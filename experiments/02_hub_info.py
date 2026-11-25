"""02 - Connect and print hub info: peripherals, battery voltage, current.

Run:  uv run experiments/02_hub_info.py
Hardware: hub on. Nothing moves.
"""

import logging
import time

from hubbit import boost

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

with boost() as hub:
    print("\nPeripherals:")
    for port, device in sorted(hub.peripherals.items()):
        print(f"  port 0x{port:02x}: {device}")

    readings = {}
    hub.voltage.subscribe(lambda v: readings.__setitem__("voltage", v))
    hub.current.subscribe(lambda c: readings.__setitem__("current", c))
    time.sleep(1)
    volts, amps = readings.get("voltage", "?"), readings.get("current", "?")
    print(f"\nVoltage: {volts} V   Current: {amps} mA")
