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
    q = kid.QUARTER_TURN_SECONDS
    assert [call[0] for call in robot.hub.motor_AB.calls] == [q / 2, q * 2]
    assert robot.battery() == 7.46
    assert robot.is_connected()
    robot.hub.connection.is_alive = lambda: False
    assert not robot.is_connected()
    assert Robot().is_connected() is False  # never connected
