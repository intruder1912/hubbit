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
