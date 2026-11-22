"""German as second language: parser words, messages, console, Robot aliases (#7)."""

import io
from pathlib import Path

import pytest

from lego_boost import console, i18n
from lego_boost.commands import RAW, SIMPLE, Command, ParseError, help_text, parse, words
from lego_boost.kid import COLORS, Roboter
from lego_boost.session import Session
from lego_boost.sim import SimHub, sim_robot

UE, SZ = chr(0xFC), chr(0xDF)  # u-umlaut, sharp s (source literals stay ASCII)


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("vor 2", Command("forward", (2.0,))),
        ("Vorwaerts 1,5", Command("forward", (1.5,))),
        ("zurueck", Command("back", (1.0,))),
        (f"zur{UE}ck 2", Command("back", (2.0,))),
        ("links 90", Command("left", (90.0,))),
        ("rechts", Command("right", (90.0,))),
        ("dreh links 45", Command("left", (45.0,))),
        ("drehe rechts", Command("right", (90.0,))),
        ("turn links 30", Command("left", (30.0,))),
        ("licht rot", Command("led", ("red",))),
        ("licht red", Command("led", ("red",))),
        ("led gruen", Command("led", ("green",))),
        (f"Gr{UE}n", Command("led", ("green",))),
        (f"wei{SZ}", Command("led", ("white",))),
        ("weiss", Command("led", ("white",))),
        ("lila", Command("led", ("purple",))),
        ("tuerkis", Command("led", ("cyan",))),
        ("aus", Command("led", ("off",))),
        ("farbe", Command("color", ())),
        ("abstand", Command("distance", ())),
        ("stopp", Command("stop", ())),
        ("hilfe vor", Command("help", ("vor",))),
        ("ende", Command("exit", ())),
        (f"tsch{UE}ss", Command("exit", ())),
        ("tschuess", Command("exit", ())),
        ("sprache deutsch", Command("language", ("deutsch",))),
        ("roh", Command("raw", ())),
        ("verbinden", Command("reconnect", ())),
    ],
)
def test_german_words_always_work(line, expected):
    assert parse(line) == expected  # no language switch needed


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("winkel AB 360 40", Command("angle", ("AB", 360.0, 40.0))),
        ("sensoren", Command("sensors", ())),
        ("batterie", Command("battery", ())),
        ("motor a 30 1", Command("motor", ("A", 30.0, 1.0))),
    ],
)
def test_german_raw_words(line, expected):
    assert parse(line, RAW) == expected


def test_german_error_messages():
    with pytest.raises(ParseError) as err:
        parse("vorwarts 2", lang="de")
    assert "Meinst du 'vor'?" in str(err.value)
    with pytest.raises(ParseError) as err:
        parse("licht gruhn", lang="de")
    assert err.value.suggestion == "gruen"
    assert "Farben: aus, schwarz, rosa" in str(err.value)
    with pytest.raises(ParseError) as err:
        parse("vor 99", lang="de")
    assert "vor: Sekunden muss zwischen 0.1 und 10 liegen" in str(err.value)
    with pytest.raises(ParseError) as err:
        parse("winkel AB 90", lang="de")
    assert "Roh-Modus" in str(err.value)
    with pytest.raises(ParseError) as err:
        parse("dreh", lang="de")
    assert "dreh links 90" in str(err.value)


def test_german_help():
    text = help_text(SIMPLE, lang="de")
    assert text.startswith("Befehle:")
    assert "vor 2" in text and "Vorwaerts fahren" in text
    assert "Roh-Befehle:" in help_text(RAW, lang="de")
    one = help_text(SIMPLE, "zurueck", lang="de")
    assert one.startswith("zurueck: Rueckwaerts fahren")
    assert "auch: back" in one
    assert "nur im Roh-Modus" in help_text(SIMPLE, "winkel", lang="de")
    assert "example: forward 2" in help_text(SIMPLE, "vor")  # English help by word


def test_words_per_language():
    assert "vor" in words(SIMPLE, "de") and "forward" not in words(SIMPLE, "de")
    assert "forward" in words(SIMPLE, "en") and "vor" not in words(SIMPLE, "en")
    assert {"vor", "forward"} <= set(words(SIMPLE))
    assert "winkel" in words(RAW, "de") and "winkel" not in words(SIMPLE, "de")


def test_every_message_exists_in_both_languages():
    assert set(i18n.MESSAGES["de"]) == set(i18n.MESSAGES["en"])
    for text in i18n.MESSAGES["de"].values():
        assert text.isascii()


def test_lang_helpers(monkeypatch):
    assert i18n.lang_from_word("Deutsch") == "de"
    assert i18n.lang_from_word("english") == "en"
    assert i18n.lang_from_word("klingonisch") is None
    monkeypatch.setenv("BOOST_LANG", "de_AT.UTF-8")
    assert i18n.default_lang() == "de"
    monkeypatch.setenv("BOOST_LANG", "")
    assert i18n.default_lang() == "en"
    assert i18n.color_word("green", "de") == "gruen"
    assert i18n.color_word("nothing", "de") == "nichts"
    assert i18n.color_word("pink", "de") == "rosa"
    assert i18n.color_word("green", "en") == "green"
    for german in i18n.COLORS_DE.values():
        assert german in COLORS


@pytest.fixture
def session():
    out = []
    s = Session(lambda: sim_robot(out.append, "de"), out.append, lang="de")
    s.open()
    s.out = out
    yield s
    s.close(timeout=0.5)


def test_session_speaks_german_and_switches(session):
    out = session.out
    assert "Roboter verbunden! (nur simuliert - kein Hub noetig)" in out
    session.handle("roh")
    assert out[-1].startswith("Roh-Modus")
    session.handle("batterie")
    session.wait_idle(2)
    assert "Batterie: 9.00 V" in out
    session.handle("tanzen")
    assert "'tanzen' kenne ich nicht." in out[-1]
    session.handle("language english")
    assert session.lang == "en" and session.robot.lang == "en"
    assert out[-1].startswith("Language: English")
    session.handle("battery")
    session.wait_idle(2)
    assert out[-1] == "Battery: 9.00 V"
    session.handle("sprache")
    assert out[-1].startswith("Language: English")  # no word: tell the current language
    session.handle("sprache klingonisch")
    assert "deutsch" in out[-1]


def test_console_german_completion_and_status(session):
    assert "vor" in console.completions(session, "vo")
    assert "rot" in console.completions(session, "ro")  # bare colour (and "roh")
    assert console.completions(session, "licht gr") == ["gruen"]
    assert console.completions(session, "dreh ") == ["links", "rechts"]
    assert console.completions(session, "sprache ") == ["deutsch", "english"]
    assert "Modus: einfach" in console.status_text(session)
    assert "verbunden" in console.status_text(session)


def test_console_lang_flag(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("vor 0.1\nblau\nhilfe\nende\n"))
    assert console.main(["--simulate", "--lang", "de"]) == 0
    out = capsys.readouterr().out
    assert "LEGO BOOST Konsole" in out
    assert "[sim] light: blue" in out
    assert "Befehle:" in out
    assert "Roboter angehalten. Tschuess!" in out


class RecordingMotor:
    def __init__(self):
        self.calls = []

    def timed(self, *args):
        self.calls.append(args)


def test_roboter_german_aliases(capsys):
    roboter = Roboter()
    roboter.hub = SimHub(lambda text: None)
    roboter.hub.motor_AB = motor = RecordingMotor()
    roboter.vorwaerts(2)
    roboter.rueckwaerts(1, 20)
    roboter.links()
    roboter.rechts(grad=45)
    assert motor.calls[0] == (2, 0.35, 0.35)
    assert motor.calls[1] == (1, -0.2, -0.2)
    assert motor.calls[2][1:] == (-0.5, 0.5)
    from lego_boost.kid import turn_seconds

    assert motor.calls[3][0] == pytest.approx(turn_seconds(45))
    leds = []
    roboter.hub.led.set_color = leds.append
    roboter.licht("rot")
    roboter.licht("glitzer")
    assert leds == [COLORS["red"]]
    assert "Die Farbe 'glitzer' kenne ich nicht." in capsys.readouterr().out
    assert roboter.farbe() == "nichts"  # no sensor in the simulation
    assert "Kein Farb-/Abstandssensor" in capsys.readouterr().out
    assert roboter.abstand() is None
    assert roboter.batterie() == 9.0


GERMAN_MISSIONS = sorted((Path(__file__).resolve().parent.parent / "kids" / "de").glob("*.py"))


@pytest.mark.parametrize("path", GERMAN_MISSIONS, ids=lambda p: p.name)
def test_german_missions_follow_the_kids_rules(path):
    text = path.read_text(encoding="utf-8")
    assert len(text.splitlines()) < 30
    for header in ("# Mission", "So startest du:", "Probier mal:"):
        assert header in text
    assert "from lego_boost.kid import Roboter" in text
    assert "lambda" not in text and "class " not in text and "async " not in text
    compile(text, str(path), "exec")


def test_there_is_a_german_copy_of_every_mission():
    english = sorted((GERMAN_MISSIONS[0].parent.parent).glob("[0-9]*.py"))
    assert [p.name[:2] for p in GERMAN_MISSIONS] == [p.name[:2] for p in english]
