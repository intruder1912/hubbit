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


def connect(address: str | None = None, timeout: float = 15.0):
    """Return a connected pylgbst MoveHub. Prefer the `boost()` context manager."""
    from pylgbst import get_connection_bleak
    from pylgbst.hub import MoveHub

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
