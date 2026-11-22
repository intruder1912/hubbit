"""A very simple robot API for young programmers.

    from lego_boost.kid import Robot

    with Robot() as robot:
        robot.light("green")
        robot.forward(2)
        robot.turn_left()
        print(robot.see_color())

Assumes a driving model where motors A and B are the left and right wheels/tracks
(e.g. Vernie, M.T.R.4, Frankie's base). Speeds are 0..100 percent.
"""

from __future__ import annotations

import time

from lego_boost.hub import connect, link_alive, safe_shutdown

COLORS = {
    "off": 0x00,
    "black": 0x00,
    "pink": 0x01,
    "purple": 0x02,
    "blue": 0x03,
    "lightblue": 0x04,
    "cyan": 0x05,
    "green": 0x06,
    "yellow": 0x07,
    "orange": 0x08,
    "red": 0x09,
    "white": 0x0A,
}
COLOR_NAMES = {0x00: "black", 0xFF: "nothing"} | {v: k for k, v in COLORS.items() if v != 0x00}

DEFAULT_SPEED = 35  # driving: ~35 cm per second on the test model (50% felt too fast)
TURN_SPEED = 50  # turning on the spot
# Calibrated 2026-11-21 on a hard floor at 50%: 0.35 s ~ 79 deg, 0.5 s ~ 130 deg
# (not linear: the motors ramp up first). Interpolated: 0.38 s ~ 90 deg.
QUARTER_TURN_SECONDS = 0.38


def _speed(percent: float) -> float:
    return max(-100.0, min(100.0, percent)) / 100.0


def turn_seconds(degrees: float) -> float:
    """Seconds of turning on the spot for about `degrees` (linear guess from the calibration)."""
    return QUARTER_TURN_SECONDS * abs(degrees) / 90.0


class Robot:
    def __init__(self, address: str | None = None):
        self._address = address
        self.hub = None
        self._last_color = 0xFF
        self._last_distance: float | None = None

    # --- connection -------------------------------------------------------
    def __enter__(self) -> Robot:
        self.hub = connect(self._address)
        print("Robot connected!")
        self.light("green")
        return self

    def __exit__(self, *exc) -> None:
        if self.hub is not None:
            safe_shutdown(self.hub)
            print("Robot stopped. Bye!")

    # --- light ------------------------------------------------------------
    def light(self, color: str) -> None:
        """Change the hub's light: red, green, blue, yellow, purple, white, off, ..."""
        name = color.lower()
        if name not in COLORS:
            print(f"I don't know the color '{color}'. Try one of: {', '.join(COLORS)}")
            return
        self.hub.led.set_color(COLORS[name])

    # --- driving ----------------------------------------------------------
    def forward(self, seconds: float = 1, speed: float = DEFAULT_SPEED) -> None:
        self.hub.motor_AB.timed(seconds, _speed(speed), _speed(speed))

    def backward(self, seconds: float = 1, speed: float = DEFAULT_SPEED) -> None:
        self.hub.motor_AB.timed(seconds, -_speed(speed), -_speed(speed))

    def turn_left(
        self,
        seconds: float = QUARTER_TURN_SECONDS,
        speed: float = TURN_SPEED,
        degrees: float | None = None,
    ) -> None:
        """Turn on the spot. With no number it is about a quarter turn (90 degrees).

        `robot.turn_left(degrees=45)` turns by an angle instead (approximate).
        """
        if degrees is not None:
            seconds = turn_seconds(degrees)
        self.hub.motor_AB.timed(seconds, -_speed(speed), _speed(speed))

    def turn_right(
        self,
        seconds: float = QUARTER_TURN_SECONDS,
        speed: float = TURN_SPEED,
        degrees: float | None = None,
    ) -> None:
        """Turn on the spot. With no number it is about a quarter turn (90 degrees).

        `robot.turn_right(degrees=45)` turns by an angle instead (approximate).
        """
        if degrees is not None:
            seconds = turn_seconds(degrees)
        self.hub.motor_AB.timed(seconds, _speed(speed), -_speed(speed))

    def spin_motor(self, degrees: float = 360, speed: float = DEFAULT_SPEED) -> None:
        """Turn the extra motor (port C or D), e.g. Vernie's head or a shooter."""
        motor = self.hub.motor_external
        if motor is None:
            print("No extra motor plugged into port C or D.")
            return
        motor.angled(degrees, _speed(speed))

    def stop(self) -> None:
        self.hub.motor_AB.stop()

    # --- sensor -----------------------------------------------------------
    def _ensure_sensor(self) -> bool:
        sensor = self.hub.vision_sensor
        if sensor is None:
            print("No color/distance sensor plugged in.")
            return False
        if not getattr(self, "_subscribed", False):
            sensor.subscribe(self._on_sensor)
            self._subscribed = True
            time.sleep(0.3)
        return True

    def _on_sensor(self, color, distance=None) -> None:
        self._last_color = color
        self._last_distance = distance

    def see_color(self) -> str:
        """Name of the color in front of the sensor (or 'nothing')."""
        if not self._ensure_sensor():
            return "nothing"
        return COLOR_NAMES.get(self._last_color, "nothing")

    def distance(self) -> float | None:
        """Rough distance to an object in front of the sensor (bigger = farther), or None."""
        if not self._ensure_sensor():
            return None
        return self._last_distance

    # --- hub --------------------------------------------------------------
    def battery(self) -> float | None:
        """Battery voltage in volts (6 fresh AAA cells: about 9 V), or None if unknown."""
        voltage = getattr(self.hub, "voltage", None)
        if voltage is None:
            return None
        try:
            return round(float(voltage.voltage), 2)
        except Exception:  # noqa: BLE001 - a missing reading must not stop the robot
            return None

    def is_connected(self) -> bool:
        """True while the Bluetooth link to the hub is working."""
        return self.hub is not None and link_alive(self.hub)

    # --- misc -------------------------------------------------------------
    @staticmethod
    def wait(seconds: float) -> None:
        time.sleep(seconds)
