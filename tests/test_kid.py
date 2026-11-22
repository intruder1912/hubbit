import pytest

from lego_boost.kid import COLOR_NAMES, COLORS, Robot, _speed


def test_speed_is_clamped_and_scaled():
    assert _speed(50) == 0.5
    assert _speed(500) == 1.0
    assert _speed(-500) == -1.0


def test_color_names_roundtrip():
    for name in ("red", "green", "blue", "yellow"):
        assert COLOR_NAMES[COLORS[name]] == name


def test_unknown_color_does_not_crash(capsys):
    robot = Robot()
    robot.hub = object()  # never touched for unknown colors
    robot.light("sparkly")
    assert "don't know" in capsys.readouterr().out


class RecordingMotor:
    def __init__(self):
        self.calls = []

    def timed(self, *args):
        self.calls.append(args)


def test_default_turn_is_calibrated_quarter_turn():
    from types import SimpleNamespace

    from lego_boost import kid

    robot = Robot()
    robot.hub = SimpleNamespace(motor_AB=RecordingMotor())
    robot.turn_right()
    robot.turn_left()
    robot.forward()
    q, t, d = kid.QUARTER_TURN_SECONDS, kid.TURN_SPEED / 100, kid.DEFAULT_SPEED / 100
    assert robot.hub.motor_AB.calls == [(q, t, -t), (q, -t, t), (1, d, d)]
    assert kid.DEFAULT_SPEED <= 50 and kid.TURN_SPEED <= 50  # hardware safety rule


def test_turn_by_degrees_and_hub_helpers():
    from types import SimpleNamespace

    from lego_boost import kid

    robot = Robot()
    robot.hub = SimpleNamespace(
        motor_AB=RecordingMotor(),
        voltage=SimpleNamespace(voltage=7.456),
        connection=SimpleNamespace(is_alive=lambda: True),
    )
    robot.turn_left(degrees=45)
    robot.turn_right(degrees=180)
    seconds = [call[0] for call in robot.hub.motor_AB.calls]
    assert seconds == [kid.turn_seconds(45), kid.turn_seconds(180)]
    assert robot.battery() == 7.46
    assert robot.is_connected()
    robot.hub.connection.is_alive = lambda: False
    assert not robot.is_connected()
    assert Robot().is_connected() is False  # never connected


def test_trim_slows_only_one_wheel():
    from lego_boost.kid import trimmed

    assert trimmed(0.5, 0.5, 0) == (0.5, 0.5)
    assert trimmed(0.5, 0.5, 10) == (0.45, 0.5)  # left slower: robot drifted right
    assert trimmed(-0.5, 0.5, -10) == (-0.5, 0.45)  # right slower, sign kept


def test_trim_from_env(monkeypatch, capsys):
    from lego_boost.kid import read_trim

    assert read_trim() == 0
    monkeypatch.setenv("BOOST_TRIM", "4,5")
    assert read_trim() == 4.5
    monkeypatch.setenv("BOOST_TRIM", "-80")
    assert read_trim() == -30
    monkeypatch.setenv("BOOST_TRIM", "lots")
    assert read_trim("de") == 0
    out = capsys.readouterr().out
    assert "BOOST_TRIM=-80" in out and "Nehme 0" in out


def test_robot_drives_with_trim(monkeypatch):
    from types import SimpleNamespace

    from lego_boost import kid

    monkeypatch.setenv("BOOST_TRIM", "10")
    robot = Robot()
    robot.hub = SimpleNamespace(motor_AB=RecordingMotor())
    robot.forward(1, speed=40)
    robot.turn_left(0.5, speed=40)
    calls = [x for call in robot.hub.motor_AB.calls for x in call]
    assert calls == pytest.approx([1, 0.36, 0.4, 0.5, -0.36, 0.4])
    assert kid.Roboter().trim == 10  # German robot reads it too


def test_turn_seconds_has_start_up_time():
    from lego_boost import kid

    # hardware measurements 2026-11-21/22 (Vernie, hard floor): seconds -> degrees
    for seconds, degrees in [(0.19, 30), (0.35, 79), (0.38, 85), (0.5, 130), (0.76, 205)]:
        assert kid.turn_seconds(degrees) == pytest.approx(seconds, abs=0.03)
    assert kid.turn_seconds(0) == 0
    assert kid.turn_seconds(-90) == kid.turn_seconds(90)
    assert kid.QUARTER_TURN_SECONDS == pytest.approx(kid.turn_seconds(90), abs=0.01)


def test_close_can_skip_the_goodbye(monkeypatch, capsys):
    from lego_boost import kid

    closed = []
    monkeypatch.setattr(kid, "safe_shutdown", closed.append)
    robot = Robot()
    robot.hub = "hub"
    robot.close(say_bye=False)
    assert closed == ["hub"] and capsys.readouterr().out == ""
    robot.__exit__(None, None, None)
    assert "Bye" in capsys.readouterr().out
