# Mission 2: A rainbow party! The light runs through all colors 3 times.
#
# How to run:   uv run kids/02_rainbow.py
# Try this:     make it faster by changing 0.3 to 0.1, or change 3 to 10.

from lego_boost.kid import Robot

rainbow = ["red", "orange", "yellow", "green", "blue", "purple"]

with Robot() as robot:
    for round_number in range(3):
        print("Round", round_number + 1)
        for color in rainbow:
            robot.light(color)
            robot.wait(0.3)
