"""Find LEGO BOOST Move Hubs over Bluetooth LE, with a timeout.

pylgbst's own discovery waits forever if no hub shows up, so we scan
ourselves first and hand pylgbst an exact address.

Run as a command:  uv run boost-scan  [--timeout SECONDS]
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass

MOVE_HUB_NAME = "LEGO Move Hub"
MOVE_HUB_SERVICE_UUID = "00001623-1212-efde-1623-785feabcd123"


class BluetoothUnavailableError(RuntimeError):
    """Bluetooth itself does not work (service not running, adapter off, ...).

    `str(err)` is a friendly hint with what to do.
    """


def bluetooth_hint(error: Exception) -> str:
    """A friendly hint for a Bluetooth error from bleak (by its message, any OS)."""
    text = str(error)
    if "dbus-org.bluez" in text or "org.bluez" in text and "ServiceUnknown" in text:
        return (
            "The Linux Bluetooth service (BlueZ) is not running. Fix: "
            "sudo apt install bluez && sudo systemctl enable --now bluetooth "
            "(see docs/setup-linux.md, step 1)."
        )
    if "NotReady" in text or "No Bluetooth adapters" in text or "powered off" in text.lower():
        return (
            "Bluetooth is switched off or blocked. Switch it on (Linux: bluetoothctl power on, "
            "sudo rfkill unblock bluetooth). See docs/troubleshooting.md."
        )
    return f"Bluetooth does not work here: {text} - see docs/troubleshooting.md."


@dataclass(frozen=True)
class FoundHub:
    name: str
    address: str  # MAC on Linux/Windows, CoreBluetooth UUID on macOS
    rssi: int | None


def is_move_hub(name: str | None, service_uuids: list[str] | None) -> bool:
    """True if an advertisement looks like a BOOST Move Hub."""
    uuids = [u.lower() for u in (service_uuids or [])]
    return MOVE_HUB_SERVICE_UUID in uuids or name == MOVE_HUB_NAME


async def scan_async(timeout: float = 10.0, first_only: bool = False) -> list[FoundHub]:
    from bleak import BleakScanner

    found: dict[str, FoundHub] = {}
    done = asyncio.Event()

    def on_detect(device, adv) -> None:
        name = adv.local_name or device.name
        if is_move_hub(name, adv.service_uuids):
            found[device.address] = FoundHub(name or "?", device.address, adv.rssi)
            if first_only:
                done.set()

    async with BleakScanner(detection_callback=on_detect):
        try:
            await asyncio.wait_for(done.wait(), timeout)
        except asyncio.TimeoutError:
            pass
    return list(found.values())


def scan(timeout: float = 10.0, first_only: bool = False) -> list[FoundHub]:
    """Blocking scan. Returns all Move Hubs seen within `timeout` seconds.

    Raises BluetoothUnavailableError (with a hint) if Bluetooth itself does not work.
    """
    from bleak.exc import BleakError

    try:
        return asyncio.run(scan_async(timeout, first_only))
    except BleakError as err:
        raise BluetoothUnavailableError(bluetooth_hint(err)) from err


def find_hub(timeout: float = 15.0) -> FoundHub | None:
    """Return the first Move Hub found, or None after `timeout` seconds."""
    hubs = scan(timeout, first_only=True)
    return hubs[0] if hubs else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan for LEGO BOOST Move Hubs.")
    parser.add_argument("--timeout", type=float, default=10.0, help="seconds to scan")
    args = parser.parse_args(argv)

    print(f"Scanning {args.timeout:.0f}s ... press the green button on the hub (LED blinks).")
    try:
        hubs = scan(args.timeout)
    except BluetoothUnavailableError as err:
        print(err)
        return 2
    if not hubs:
        print("No Move Hub found. See docs/troubleshooting.md.")
        return 1
    for hub in hubs:
        print(f"  {hub.name}  address={hub.address}  rssi={hub.rssi}")
    print("\nTip: export BOOST_HUB_ADDRESS=<address> to skip scanning next time.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
