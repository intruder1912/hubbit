import pytest

from lego_boost.commands import RAW, SIMPLE, Command, ParseError, help_text, parse, words


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("forward", Command("forward", (1.0,))),
        ("Forward 1,5", Command("forward", (1.5,))),
        ("  f 2  ", Command("forward", (2.0,))),
        ("back", Command("back", (1.0,))),
        ("left", Command("left", (90.0,))),
        ("turn left 45", Command("left", (45.0,))),
        ("turn right", Command("right", (90.0,))),
        ("led red", Command("led", ("red",))),
        ("LIGHT Blue", Command("led", ("blue",))),
        ("green", Command("led", ("green",))),
        ("colour", Command("color", ())),
        ("q", Command("exit", ())),
        ("stop", Command("stop", ())),
        ("help", Command("help", ("",))),
        ("help motor", Command("help", ("motor",))),
    ],
)
def test_simple_commands(line, expected):
    assert parse(line) == expected


def test_empty_line_is_nothing():
    assert parse("") is None
    assert parse("   ") is None


def test_typo_suggests_the_closest_command():
    with pytest.raises(ParseError) as err:
        parse("forwrd 2")
    assert err.value.suggestion == "forward"
    assert "Did you mean 'forward'?" in str(err.value)


def test_unknown_color_suggests_a_color():
    with pytest.raises(ParseError) as err:
        parse("led gren")
    assert err.value.suggestion == "green"


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("forward 99", "between 0.1 and 10"),
        ("forward fast", "must be a number"),
        ("forward nan", "must be a number"),
        ("forward 1 2", "at most 1 value"),
        ("color now", "no values"),
        ("led", "needs a color"),
        ("turn", "Say which way"),
        ("left 0", "between 1 and 720"),
    ],
)
def test_bad_values_give_friendly_errors(line, message):
    with pytest.raises(ParseError, match=message):
        parse(line)


def test_raw_commands_need_raw_mode():
    with pytest.raises(ParseError, match="raw mode"):
        parse("motor A 30 1")
    assert parse("motor a 30 1.5", RAW) == Command("motor", ("A", 30.0, 1.5))
    assert parse("angle AB 360", RAW) == Command("angle", ("AB", 360.0, 35.0))
    assert parse("forward", RAW) == Command("forward", (1.0,))  # simple works in raw too


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("motor A 0 1", "must not be 0"),
        ("motor A 30", "needs a seconds"),
        ("motor E 30 1", "must be one of"),
        ("motor A 150 1", "between -100 and 100"),
        ("motor A 30 11", "between 0.1 and 10"),
    ],
)
def test_raw_limits(line, message):
    with pytest.raises(ParseError, match=message):
        parse(line, RAW)


def test_help_lists_raw_commands_only_in_raw_mode():
    assert "motor A 30 1.5" not in help_text(SIMPLE)
    assert "motor A 30 1.5" in help_text(RAW)
    assert "raw mode only" in help_text(SIMPLE, "motor")
    assert "example: forward 2" in help_text(SIMPLE, "fwd")
    with pytest.raises(ParseError):
        help_text(SIMPLE, "dance")


def test_completion_words_depend_on_mode():
    assert "forward" in words(SIMPLE) and "motor" not in words(SIMPLE)
    assert "motor" in words(RAW)
