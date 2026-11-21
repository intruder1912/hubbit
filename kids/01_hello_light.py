# Mission 1: Make the robot's light change color!
#
# How to run:   uv run kids/01_hello_light.py
# Try this:     change "red" to "blue" or "yellow", or add more colors.

from lego_boost.kid import Robot

with Robot() as robot:
    robot.light("red")
    robot.wait(1)
    robot.light("yellow")
    robot.wait(1)
    robot.light("green")
    robot.wait(1)
