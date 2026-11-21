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
import threading
from collections.abc import Iterator
from contextlib import contextmanager

from lego_boost.scan import MOVE_HUB_NAME, find_hub

log = logging.getLogger(__name__)

ENV_ADDRESS = "BOOST_HUB_ADDRESS"


class HubNotFoundError(RuntimeError):
    pass


def resolve_address(address: str | None = None, timeout: float = 15.0) -> str:
    """Explicit address > $BOOST_HUB_ADDRESS > BLE scan."""
    address = address or os.environ.get(ENV_ADDRESS)
    if address:
        return address
    print("Looking for the Move Hub ... press its green button.")
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
    """
    from pylgbst.comms.cbleak import BleakConnection
    from pylgbst.messages import MsgHubAction

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


def connect(address: str | None = None, timeout: float = 15.0):
    """Return a connected pylgbst MoveHub. Prefer the `boost()` context manager."""
    from pylgbst import get_connection_bleak
    from pylgbst.hub import MoveHub

    patch_pylgbst()
    addr = resolve_address(address, timeout)
    log.info("Connecting to %s", addr)
    conn = get_connection_bleak(hub_mac=addr, hub_name=MOVE_HUB_NAME)
    return MoveHub(conn)


def _run_with_timeout(fn, timeout: float) -> None:
    """Run fn in a daemon thread; give up after `timeout` (pylgbst calls can block forever)."""
    t = threading.Thread(target=fn, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        log.warning("%s did not finish within %.1fs", getattr(fn, "__name__", fn), timeout)


def safe_shutdown(hub, timeout: float = 3.0) -> None:
    """Stop all motors and disconnect. Never raises."""

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
