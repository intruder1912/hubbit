"""Connect to a Move Hub and always clean up (motors stopped, BLE closed).

Usage:
    from lego_boost import boost

    with boost() as hub:
        hub.led.set_color(COLOR_GREEN)
        hub.motor_AB.timed(1.0, 0.5)
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from types import SimpleNamespace

from lego_boost.config import load_env
from lego_boost.scan import MOVE_HUB_NAME, find_hub

log = logging.getLogger(__name__)

ENV_ADDRESS = "BOOST_HUB_ADDRESS"


# MoveHub() waits up to 10 s for the built-in devices, then asks the hub four questions
# with no timeout at all. On BlueZ a half-open link right after a disconnect never answers.
CONNECT_TIMEOUT = 25.0

# MoveHub() can return without them (BlueZ link dropped during setup); Robot needs them.
REQUIRED_DEVICES = ("motor_A", "motor_B", "motor_AB", "led")

LINUX_HINT = " If it keeps failing on Linux, reset Bluetooth: see docs/setup-linux.md."


class HubNotFoundError(RuntimeError):
    pass


class HubConnectError(RuntimeError):
    """The hub was found, but setting up the connection failed or never finished."""


def resolve_address(address: str | None = None, timeout: float = 15.0) -> str:
    """Explicit address > $BOOST_HUB_ADDRESS (shell or .env) > first hub found by a BLE scan.

    A known address is still waited for with a timed scan: the hub only accepts a
    connection while it advertises, and pylgbst's own search for it never times out.
    """
    load_env()
    address = address or os.environ.get(ENV_ADDRESS)
    print("Looking for the Move Hub ... press its green button.")
    if address:
        found = find_hub(timeout, address=address)
        if found is None:
            raise HubNotFoundError(
                f"Move Hub {address} not seen within {timeout:.0f}s. Is it switched on "
                "(blinking LED)? A different hub? Run 'boost-scan --save' to update .env, "
                f"or unset {ENV_ADDRESS}."
            )
        return found.address
    found = find_hub(timeout)
    if found is None:
        raise HubNotFoundError(
            f"No Move Hub found within {timeout:.0f}s. Is it switched on (blinking LED)? "
            "See docs/troubleshooting.md."
        )
    return found.address


def patch_pylgbst() -> None:
    """Work around two pylgbst bugs at the pinned commit (71dfc63). Idempotent.

    1. On macOS 12+ pylgbst calls `BleakConnection.find_device(..., service_uuids=[...])`,
       but `find_device` accepts no extra kwargs -> TypeError kills the comms thread and
       every connect fails with "communication threads not functioning". Our own scan
       finds the hub without the service filter, so the extra kwargs are dropped.
       Harmless on Linux/Windows (they never pass the kwarg).
    2. `MsgHubAction.is_reply` raises TypeError for any other upstream message instead of
       returning False. A sensor value arriving while `hub.disconnect()` waits for its
       reply kills pylgbst's processing thread.
    (1 and 2 are fixed upstream in undera/pylgbst#142 / #144, not released yet.)
    3. A failed BLE connect (BlueZ: "failed to discover services" right after the hub was
       switched back on) ends pylgbst's connection thread with a full traceback on stderr,
       which garbles boost-tui. Log one line instead; connect() then reports and retries.
    4. A vision sensor reading sent just before a mode switch is decoded with the new
       mode's layout (1 byte where 4 are expected) -> AssertionError traceback (seen on
       Kali in boost-tui). Drop such stale readings.
    """
    from pylgbst.comms.cbleak import BleakConnection, BleakDriver
    from pylgbst.messages import MsgHubAction
    from pylgbst.peripherals import VisionSensor

    original_find = BleakConnection.find_device
    if not getattr(original_find, "_lego_boost_patched", False):

        async def find_device(self, hub_mac=None, hub_name=None, **_ignored):
            return await original_find(self, hub_mac, hub_name)

        find_device._lego_boost_patched = True
        BleakConnection.find_device = find_device

    original_is_reply = MsgHubAction.is_reply
    if not getattr(original_is_reply, "_lego_boost_patched", False):

        def is_reply(self, msg):
            if not isinstance(msg, MsgHubAction):
                return False
            return original_is_reply(self, msg)

        is_reply._lego_boost_patched = True
        MsgHubAction.is_reply = is_reply

    original_thread = BleakDriver._bleak_thread
    if not getattr(original_thread, "_lego_boost_patched", False):

        async def _bleak_thread(self):
            try:
                await original_thread(self)
            except Exception as exc:  # noqa: BLE001 - the thread ends either way
                log.warning("Bluetooth connection failed: %s", exc)

        _bleak_thread._lego_boost_patched = True
        BleakDriver._bleak_thread = _bleak_thread

    original_handle = VisionSensor._handle_port_data
    if not getattr(original_handle, "_lego_boost_patched", False):

        def _handle_port_data(self, msg):
            mode = getattr(self._port_mode, "mode", None)
            if mode == VisionSensor.COLOR_DISTANCE_FLOAT and len(msg.payload) < 4:
                log.debug("Dropped a stale vision reading: %r", msg)
                return
            original_handle(self, msg)

        _handle_port_data._lego_boost_patched = True
        VisionSensor._handle_port_data = _handle_port_data


class _QuietUnknownPeripheral(logging.Filter):
    """Drop pylgbst's warning about the Move Hub's internal device on port 0x46 (type 0x42).

    It shows up on every connect, means nothing for users and confuses kids.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        return "Have no dedicated class for peripheral" not in record.getMessage()


def quiet_pylgbst_logs() -> None:
    """Install the filter once on pylgbst's `hub` logger."""
    logger = logging.getLogger("hub")
    if not any(isinstance(f, _QuietUnknownPeripheral) for f in logger.filters):
        logger.addFilter(_QuietUnknownPeripheral())


def _close_quietly(conn) -> None:
    def close():
        try:
            conn.disconnect()
        except Exception as exc:  # noqa: BLE001
            log.debug("connection.disconnect failed: %s", exc)

    _run_with_timeout(close, 3.0)


def _hint() -> str:
    return LINUX_HINT if sys.platform.startswith("linux") else ""


def _set_up_hub(addr: str):
    """MoveHub(conn) with a time limit; raises HubConnectError. Stuck threads are daemons.

    A cause (`raise ... from`) marks a fast failure that connect() may retry; a timeout
    has none. Gives up early once pylgbst's BLE thread has died, and closes every
    half-set-up connection, so BlueZ isn't left with a stale link.
    """
    from pylgbst import get_connection_bleak
    from pylgbst.hub import MoveHub

    conn = get_connection_bleak(hub_mac=addr, hub_name=MOVE_HUB_NAME)
    result: dict = {}

    def build():
        try:
            result["hub"] = MoveHub(conn)
        except Exception as exc:  # noqa: BLE001 - reported below
            result["error"] = exc

    thread = threading.Thread(target=build, daemon=True, name="lego-boost connect")
    thread.start()
    deadline = time.monotonic() + CONNECT_TIMEOUT
    was_alive = False
    while thread.is_alive() and time.monotonic() < deadline:
        thread.join(0.1)
        alive = link_alive(SimpleNamespace(connection=conn))
        if was_alive and not alive and thread.is_alive():
            result["error"] = ConnectionError("the Bluetooth link was lost during setup")
            break
        was_alive = was_alive or alive

    if "hub" in result:
        missing = [name for name in REQUIRED_DEVICES if getattr(result["hub"], name, None) is None]
        if not missing:
            return result["hub"]
        result["error"] = ConnectionError(f"the hub did not report {', '.join(missing)}")
    _close_quietly(conn)
    if "error" not in result:
        raise HubConnectError(
            f"the hub did not answer within {CONNECT_TIMEOUT:.0f}s. Switch it off and on "
            f"(green button), then try again.{_hint()}"
        )
    error = result["error"]
    raise HubConnectError(f"{error}. Press the green button and try again.{_hint()}") from error


def connect(address: str | None = None, timeout: float = 15.0):
    """Return a connected pylgbst MoveHub. Prefer the `boost()` context manager.

    A setup that fails fast (BlueZ right after the hub restarted) is tried once more;
    one that hangs is given up after CONNECT_TIMEOUT (no retry, so waiting stays short).
    """
    patch_pylgbst()
    quiet_pylgbst_logs()
    for attempt in (1, 2):
        addr = resolve_address(address, timeout)
        log.info("Connecting to %s", addr)
        try:
            return _set_up_hub(addr)
        except HubConnectError as err:
            if attempt == 2 or err.__cause__ is None:  # second failure, or a timeout
                raise
            log.info("Connection failed (%s), retrying", err.__cause__)
            print("Connection failed. Press the green button again - trying once more ...")
    raise AssertionError("unreachable")


def _run_with_timeout(fn, timeout: float) -> None:
    """Run fn in a daemon thread; give up after `timeout` (pylgbst calls can block forever)."""
    t = threading.Thread(target=fn, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        log.warning("%s did not finish within %.1fs", getattr(fn, "__name__", fn), timeout)


def link_alive(hub) -> bool:
    """False once pylgbst's BLE threads have died (the hub was lost).

    pylgbst only notices a lost link when a write fails, so a fresh drop can still read True.
    Connections without `is_alive()` (fakes, other backends) count as alive.
    """
    is_alive = getattr(hub.connection, "is_alive", None)
    if is_alive is None:
        return True
    try:
        return bool(is_alive())
    except Exception:  # noqa: BLE001
        return False


def safe_shutdown(hub, timeout: float = 3.0) -> None:
    """Stop all motors and disconnect. Never raises.

    If the link is already gone, skip talking to the hub (it would only time out).
    """
    if not link_alive(hub):
        log.info("Hub link already lost; closing the connection only")
        try:
            hub.connection.disconnect()
        except Exception as exc:  # noqa: BLE001
            log.debug("connection.disconnect failed: %s", exc)
        return

    def stop_motors() -> None:
        for name in ("motor_AB", "motor_A", "motor_B", "motor_external"):
            motor = getattr(hub, name, None)
            if motor is not None:
                try:
                    motor.stop()
                except Exception as exc:  # noqa: BLE001 - shutdown must not fail
                    log.debug("stop %s failed: %s", name, exc)

    def disconnect() -> None:
        try:
            hub.disconnect()
        except Exception as exc:  # noqa: BLE001
            log.debug("hub.disconnect failed: %s", exc)

    _run_with_timeout(stop_motors, timeout)
    _run_with_timeout(disconnect, timeout)
    try:
        hub.connection.disconnect()  # stops pylgbst's BLE threads
    except Exception as exc:  # noqa: BLE001
        log.debug("connection.disconnect failed: %s", exc)


@contextmanager
def boost(address: str | None = None, timeout: float = 15.0) -> Iterator:
    """Context manager yielding a connected MoveHub; motors stop even on Ctrl+C or errors."""
    hub = connect(address, timeout)
    try:
        yield hub
    finally:
        safe_shutdown(hub)
