"""05 - Stream color/distance and tilt sensor readings for 15 seconds.

Run:  uv run experiments/05_sensors.py
Hardware: color & distance sensor in port C or D (optional). Nothing moves.
          Wave objects in front of the sensor and tilt the hub.
"""

import time

from pylgbst.peripherals import COLORS, TiltSensor

from hubbit import boost

DURATION = 15

with boost() as hub:

    def on_vision(color, distance=None):
        print(f"vision: color={COLORS.get(color, color)} distance={distance}")

    def on_tilt(state):
        print(f"tilt:   {TiltSensor.TRI_STATES.get(state, state)}")

    def on_button(pressed):
        print(f"button: {'pressed' if pressed else 'released'}")

    if hub.vision_sensor:
        hub.vision_sensor.subscribe(on_vision)
    else:
        print("(no vision sensor attached)")
    hub.tilt_sensor.subscribe(on_tilt)
    hub.button.subscribe(on_button)

    print(f"Listening for {DURATION}s ... (Ctrl+C to stop)")
    time.sleep(DURATION)
