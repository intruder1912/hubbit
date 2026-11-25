"""03 - Cycle the hub LED through all colors.

Run:  uv run experiments/03_led_colors.py
Hardware: hub on. Nothing moves.
"""

import time

from pylgbst.peripherals import COLORS

from hubbit import boost

with boost() as hub:
    for code, name in COLORS.items():
        if name == "NONE":
            continue
        print(name)
        hub.led.set_color(code)
        time.sleep(0.7)
