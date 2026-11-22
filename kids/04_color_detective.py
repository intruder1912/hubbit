# Mission 4: Color detective! Hold colored LEGO bricks in front of the sensor.
#            The robot tells you the color and copies it with its light.
#
# How to run:   uv run kids/04_color_detective.py
# Needs:        the color & distance sensor plugged in.
# Try this:     make the robot drive forward when it sees green!

from lego_boost.kid import Robot

with Robot() as robot:
    print("Show me a color! (press Ctrl+C to stop)")
    last = None
    for _ in range(200):
        color = robot.see_color()
        # "black" mostly means "too dark or too far", so we skip it like "nothing"
        if color != last and color not in ("nothing", "black"):
            print("I see", color.upper(), "!")
            robot.light(color)
            last = color
        robot.wait(0.1)
