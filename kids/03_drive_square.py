# Mission 3: Drive in a square!
#
# How to run:   uv run kids/03_drive_square.py
# Careful:      put the robot on the floor with lots of space.
# Try this:     can you drive a triangle? Or a zig-zag?
#               (turn_right() is a quarter turn. turn_right(0.2) turns less,
#               turn_right(0.7) turns about half way round.)

from hubbit.kid import Robot

with Robot() as robot:
    for side in range(4):
        print("Side", side + 1)
        robot.light("blue")
        robot.forward(1)
        robot.light("yellow")
        robot.turn_right()
