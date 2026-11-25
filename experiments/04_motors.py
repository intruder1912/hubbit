"""04 - Exercise the built-in motors A and B (and AB together).

Run:  uv run experiments/04_motors.py
Hardware: SAFETY - lift the model or put it on a clear floor; wheels/tracks will turn.
"""

import time

from hubbit import boost

with boost() as hub:
    print("A: 90 degrees forward, then back")
    hub.motor_A.angled(90, 0.3)
    hub.motor_A.angled(-90, 0.3)

    print("B: 1 second at 30%")
    hub.motor_B.timed(1.0, 0.3)

    print("AB: both forward 1s, then turn on the spot 1s")
    hub.motor_AB.timed(1.0, 0.4, 0.4)
    hub.motor_AB.timed(1.0, 0.4, -0.4)

    angles = []
    hub.motor_A.subscribe(angles.append)
    hub.motor_A.angled(180, 0.3)
    time.sleep(0.3)
    hub.motor_A.unsubscribe(angles.append)
    print(f"Encoder A last angle: {angles[-1] if angles else '?'}")
