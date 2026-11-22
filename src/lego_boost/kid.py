"""A very simple robot API for young programmers.

    from lego_boost.kid import Robot

    with Robot() as robot:
        robot.light("green")
        robot.forward(2)
        robot.turn_left()
        print(robot.see_color())

German: `Roboter` has the same robot with German method names and messages
(`roboter.licht("rot")`, `roboter.vorwaerts(2)`, `roboter.farbe()` -> "gruen").

Assumes a driving model where motors A and B are the left and right wheels/tracks
(e.g. Vernie, M.T.R.4, Frankie's base). Speeds are 0..100 percent.

Drift: if one wheel is a bit faster, set `BOOST_TRIM` in `.env` (percent, -30..30).
`BOOST_TRIM=5` runs the left wheel 5% slower (robot drifts right), `-5` the right wheel.
A wheel is only ever slowed down, never sped up.
"""

from __future__ import annotations

import math
import os
import time

from lego_boost.config import load_env
from lego_boost.hub import connect, link_alive, safe_shutdown
from lego_boost.i18n import DE, EN, color_to_english, color_word, color_words, t

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


ENV_TRIM = "BOOST_TRIM"
MAX_TRIM = 30.0


def read_trim(lang: str = EN) -> float:
    """$BOOST_TRIM (shell or .env) as a percent in -MAX_TRIM..MAX_TRIM; 0 if unset.

    A bad value prints a warning: out of range is clamped, not a number gives 0.
    """
    load_env()
    raw = os.environ.get(ENV_TRIM, "").strip()
    if not raw:
        return 0.0
    try:
        value = float(raw.replace(",", "."))
    except ValueError:
        value = math.nan
    used = 0.0 if math.isnan(value) else max(-MAX_TRIM, min(MAX_TRIM, value))
    if used != value:
        print(t(lang, "bad_trim", value=raw, max=f"{MAX_TRIM:g}", used=f"{used:g}"))
    return used


def trimmed(left: float, right: float, trim: float) -> tuple[float, float]:
    """Wheel speeds with the trim applied: trim > 0 slows the left wheel, < 0 the right."""
    if trim > 0:
        left *= 1 - trim / 100
    elif trim < 0:
        right *= 1 + trim / 100
    return left, right


def turn_seconds(degrees: float) -> float:
    """Seconds of turning on the spot for about `degrees` (linear guess from the calibration)."""
    return QUARTER_TURN_SECONDS * abs(degrees) / 90.0


class Robot:
    lang = EN  # language of the printed messages

    def __init__(self, address: str | None = None, lang: str | None = None):
        self._address = address
        if lang is not None:
            self.lang = lang
        self.hub = None
        self._last_color = 0xFF
        self._last_distance: float | None = None
        self._last_tilt: str | None = None
        self._tilt_subscribed = False
        self.trim = read_trim(self.lang)  # percent, see BOOST_TRIM in the module docstring

    # --- connection -------------------------------------------------------
    def __enter__(self) -> Robot:
        self.hub = connect(self._address)
        print(self._t("robot_connected"))
        self.light("green")
        return self

    def __exit__(self, *exc) -> None:
        if self.hub is not None:
            safe_shutdown(self.hub)
            print(self._t("robot_bye"))

    # --- light ------------------------------------------------------------
    def light(self, color: str) -> None:
        """Change the hub's light: red, green, blue, yellow, purple, white, off, ...

        German colour names work too ("rot", "gruen", ...).
        """
        name = color_to_english(color, COLORS)
        if name is None:
            colors = ", ".join(color_words(self.lang, COLORS))
            print(self._t("robot_unknown_color", color=color, colors=colors))
            return
        self.hub.led.set_color(COLORS[name])

    # --- driving ----------------------------------------------------------
    def wheels(self, left: float, right: float) -> tuple[float, float]:
        """Left/right wheel speeds (-1..1) with this robot's trim applied."""
        return trimmed(left, right, self.trim)

    def forward(self, seconds: float = 1, speed: float = DEFAULT_SPEED) -> None:
        self.hub.motor_AB.timed(seconds, *self.wheels(_speed(speed), _speed(speed)))

    def backward(self, seconds: float = 1, speed: float = DEFAULT_SPEED) -> None:
        self.hub.motor_AB.timed(seconds, *self.wheels(-_speed(speed), -_speed(speed)))

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
        self.hub.motor_AB.timed(seconds, *self.wheels(-_speed(speed), _speed(speed)))

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
        self.hub.motor_AB.timed(seconds, *self.wheels(_speed(speed), -_speed(speed)))

    def spin_motor(self, degrees: float = 360, speed: float = DEFAULT_SPEED) -> None:
        """Turn the extra motor (port C or D), e.g. Vernie's head or a shooter."""
        motor = self.hub.motor_external
        if motor is None:
            print(self._t("no_extra_motor"))
            return
        motor.angled(degrees, _speed(speed))

    def stop(self) -> None:
        self.hub.motor_AB.stop()

    # --- sensor -----------------------------------------------------------
    def _ensure_sensor(self) -> bool:
        sensor = self.hub.vision_sensor
        if sensor is None:
            print(self._t("no_sensor"))
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

    def tilt(self) -> str | None:
        """Which way the hub is tipped: "up", "down", "left", "right", "front", "back".

        None if the hub has no tilt sensor or no reading came in yet.
        """
        sensor = getattr(self.hub, "tilt_sensor", None)
        if sensor is None:
            return None
        if not self._tilt_subscribed:
            states = getattr(sensor, "TRI_STATES", {})

            def on_tilt(state, *_):
                self._last_tilt = str(states.get(state, state)).lower()

            sensor.subscribe(on_tilt, mode=sensor.MODE_3AXIS_SIMPLE)
            self._tilt_subscribed = True
            time.sleep(0.3)
        return self._last_tilt

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

    def _t(self, key: str, **values) -> str:
        return t(self.lang, key, **values)


class Roboter(Robot):
    """The same robot in German: German messages, German method names.

        with Roboter() as roboter:
            roboter.licht("gruen")
            roboter.vorwaerts(2)
            roboter.rechts()
            print(roboter.farbe())

    Each German method just calls the English one.
    """

    lang = DE

    def vorwaerts(self, sekunden: float = 1, tempo: float = DEFAULT_SPEED) -> None:
        self.forward(sekunden, tempo)

    def rueckwaerts(self, sekunden: float = 1, tempo: float = DEFAULT_SPEED) -> None:
        self.backward(sekunden, tempo)

    def links(self, sekunden: float = QUARTER_TURN_SECONDS, grad: float | None = None) -> None:
        """Auf der Stelle links drehen. Ohne Zahl: eine Vierteldrehung (90 Grad)."""
        self.turn_left(sekunden, degrees=grad)

    def rechts(self, sekunden: float = QUARTER_TURN_SECONDS, grad: float | None = None) -> None:
        """Auf der Stelle rechts drehen. Ohne Zahl: eine Vierteldrehung (90 Grad)."""
        self.turn_right(sekunden, degrees=grad)

    def licht(self, farbe: str) -> None:
        """Licht am Hub: rot, gruen, blau, gelb, lila, weiss, aus, ..."""
        self.light(farbe)

    def farbe(self) -> str:
        """Die Farbe vor dem Sensor auf Deutsch ("gruen"), oder "nichts"."""
        return color_word(self.see_color(), DE)

    def abstand(self) -> float | None:
        return self.distance()

    def anhalten(self) -> None:
        self.stop()

    def batterie(self) -> float | None:
        return self.battery()

    @staticmethod
    def warte(sekunden: float) -> None:
        time.sleep(sekunden)
