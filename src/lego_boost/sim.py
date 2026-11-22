"""A pretend Move Hub: prints what the motors and the light would do. No Bluetooth needed.

Used by `boost-console --simulate` (practice without the robot, and CI smoke tests).
"""

from __future__ import annotations

from collections.abc import Callable

from lego_boost.kid import COLOR_NAMES, Robot


class SimMotor:
    def __init__(self, name: str, say: Callable[[str], None]):
        self.name = name
        self._say = say
        self.cmd_in_progress = False

    def timed(self, seconds, speed_primary=1.0, speed_secondary=None, wait_complete=True):
        b = speed_primary if speed_secondary is None else speed_secondary
        if seconds == 0:
            self._say(f"[sim] motor {self.name}: stop")
            return
        a = speed_primary
        self._say(f"[sim] motor {self.name}: {seconds:g} s at {a * 100:+.0f}% / {b * 100:+.0f}%")

    def angled(self, degrees, speed_primary=1.0, speed_secondary=None, wait_complete=True):
        self._say(f"[sim] motor {self.name}: {degrees:g} deg at {speed_primary * 100:+.0f}%")

    def stop(self):
        self.timed(0)


class SimLed:
    def __init__(self, say: Callable[[str], None]):
        self._say = say

    def set_color(self, color: int) -> None:
        self._say(f"[sim] light: {COLOR_NAMES.get(color, color)}")


class SimConnection:
    def __init__(self):
        self.open = True

    def is_alive(self) -> bool:
        return self.open

    def disconnect(self) -> None:
        self.open = False


class SimHub:
    def __init__(self, say: Callable[[str], None] = print):
        self.motor_A = SimMotor("A", say)
        self.motor_B = SimMotor("B", say)
        self.motor_AB = SimMotor("AB", say)
        self.motor_external = self.port_C = self.port_D = None
        self.vision_sensor = None  # no color sensor in the simulation
        self.led = SimLed(say)
        self.voltage = type("SimVoltage", (), {"voltage": 9.0})()
        self.peripherals = {0x00: "motor A", 0x01: "motor B", 0x10: "motors AB (simulated)"}
        self.connection = SimConnection()

    def disconnect(self) -> None:
        self.connection.disconnect()


def sim_robot(say: Callable[[str], None] = print) -> Robot:
    """A connected-looking Robot on a SimHub (what `with Robot()` would give you)."""
    robot = Robot()
    robot.hub = SimHub(say)
    say("Robot connected! (simulated - no hub needed)")
    robot.light("green")
    return robot
