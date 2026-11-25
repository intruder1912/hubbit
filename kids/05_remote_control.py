# Mission 5: Remote control! Type a letter and press Enter.
#
#   w = forward   s = backward   a = left   d = right   q = quit
#
# How to run:   uv run kids/05_remote_control.py
# Try this:     add a new letter, e.g. "l" for a light show!

from hubbit.kid import Robot

with Robot() as robot:
    while True:
        key = input("Command (w/a/s/d, q to quit): ").strip().lower()
        if key == "w":
            robot.forward(0.5)
        elif key == "s":
            robot.backward(0.5)
        elif key == "a":
            robot.turn_left(0.3)
        elif key == "d":
            robot.turn_right(0.3)
        elif key == "q":
            break
        else:
            print("I don't know that one!")
