"""Typed robot commands: turn a line like "forward 2" into a `Command`.

Pure logic, no hub access - the console's `Session` runs the commands. Used by
`boost-console` (and later the TUI).

    >>> parse("Forward 1,5")
    Command(name='forward', args=(1.5,))
    >>> parse("turn left 45")
    Command(name='left', args=(45.0,))
    >>> parse("dreh links 45")
    Command(name='left', args=(45.0,))
    >>> parse("licht rot")
    Command(name='led', args=('red',))

Simple commands work in both modes; raw commands only after typing `raw`.
English and German words always both work (`Spec.aliases`, `Spec.de`); `lang` only picks
the language of messages and help (see `lego_boost.i18n`). Colours come back as English
names (`kid.COLORS`).
"""

from __future__ import annotations

import difflib
import math
from dataclasses import dataclass

from lego_boost.i18n import (
    COLORS_DE,
    DE,
    EN,
    PARAM_NAMES_DE,
    color_to_english,
    color_words,
    normalize,
    t,
)
from lego_boost.kid import COLORS, DEFAULT_SPEED

SIMPLE = "simple"
RAW = "raw"

MAX_SECONDS = 10.0  # longest single move (hardware safety)
PORTS = ("A", "B", "AB", "C", "D")
_REQUIRED = object()


@dataclass(frozen=True)
class Param:
    name: str
    kind: str  # "number" | "color" | "port" | "word"
    default: object = _REQUIRED
    low: float | None = None
    high: float | None = None
    nonzero: bool = False

    @property
    def required(self) -> bool:
        return self.default is _REQUIRED


@dataclass(frozen=True)
class Spec:
    name: str
    mode: str  # SIMPLE = available everywhere, RAW = only in raw mode
    help: str
    example: str
    params: tuple[Param, ...] = ()
    aliases: tuple[str, ...] = ()
    queued: bool = True  # False: handled at once by the session (stop, exit, help, ...)
    de: tuple[str, ...] = ()  # German words; the first one is shown in German help
    help_de: str = ""
    example_de: str = ""

    def shown(self, lang: str) -> str:
        """The command word to show in `lang`."""
        return self.de[0] if lang == DE and self.de else self.name


@dataclass(frozen=True)
class Command:
    name: str
    args: tuple = ()


class ParseError(ValueError):
    """A line that is not a valid command. `str(err)` is a friendly message."""

    def __init__(self, message: str, suggestion: str | None = None):
        super().__init__(message)
        self.suggestion = suggestion


def _seconds(default=1.0):
    return Param("seconds", "number", default, 0.1, MAX_SECONDS)


def _degrees(default=90.0):
    return Param("degrees", "number", default, 1, 720)


SPECS: tuple[Spec, ...] = (
    # --- simple ---------------------------------------------------------------
    Spec("forward", SIMPLE, "Drive forward (seconds)", "forward 2", (_seconds(),),
         ("f", "fwd", "go"),
         de=("vor", "vorwaerts"), help_de="Vorwaerts fahren (Sekunden)", example_de="vor 2"),
    Spec("back", SIMPLE, "Drive backward (seconds)", "back 1", (_seconds(),),
         ("b", "backward", "backwards", "reverse"),
         de=("zurueck", "rueckwaerts"), help_de="Rueckwaerts fahren (Sekunden)",
         example_de="zurueck 1"),
    Spec("left", SIMPLE, "Turn left on the spot (degrees, about)", "left 90", (_degrees(),),
         ("l",), de=("links",), help_de="Auf der Stelle links drehen (Grad, ungefaehr)",
         example_de="links 90"),
    Spec("right", SIMPLE, "Turn right on the spot (degrees, about)", "right 45", (_degrees(),),
         ("r",), de=("rechts",), help_de="Auf der Stelle rechts drehen (Grad, ungefaehr)",
         example_de="rechts 45"),
    Spec("led", SIMPLE, "Change the hub's light", "led red", (Param("color", "color"),),
         ("light", "lamp"), de=("licht", "lampe"), help_de="Licht am Hub aendern",
         example_de="licht rot"),
    Spec("color", SIMPLE, "Which color does the sensor see?", "color", (), ("colour", "see"),
         de=("farbe",), help_de="Welche Farbe sieht der Sensor?", example_de="farbe"),
    Spec("distance", SIMPLE, "How far away is something? (bigger = farther)", "distance", (),
         ("dist",), de=("abstand",), help_de="Wie weit weg ist etwas? (groesser = weiter)",
         example_de="abstand"),
    Spec("stop", SIMPLE, "Stop the motors right now", "stop", (), ("s", "halt"), queued=False,
         de=("stopp",), help_de="Motoren sofort anhalten", example_de="stopp"),
    Spec("help", SIMPLE, "Show the commands", "help forward",
         (Param("command", "word", ""),), ("?", "h"), queued=False,
         de=("hilfe",), help_de="Befehle zeigen", example_de="hilfe vor"),
    Spec("raw", SIMPLE, "Switch to raw mode (for grown-ups)", "raw", queued=False,
         de=("roh",), help_de="In den Roh-Modus schalten (fuer Erwachsene)", example_de="roh"),
    Spec("simple", SIMPLE, "Switch back to simple mode", "simple", queued=False,
         de=("einfach",), help_de="Zurueck in den einfachen Modus", example_de="einfach"),
    Spec("language", SIMPLE, "Language of messages: english or deutsch", "language deutsch",
         (Param("language", "word", ""),), ("lang",), queued=False,
         de=("sprache",), help_de="Sprache der Meldungen: deutsch oder english",
         example_de="sprache english"),
    Spec("reconnect", SIMPLE, "Connect again after the hub was lost", "reconnect",
         queued=False, de=("verbinden",), help_de="Neu verbinden, wenn der Hub weg war",
         example_de="verbinden"),
    Spec("exit", SIMPLE, "Stop everything and say goodbye", "exit", (), ("quit", "q", "bye"),
         queued=False, de=("ende", "tschuess", "tschuss"),
         help_de="Alles anhalten und tschuess sagen", example_de="ende"),
    # --- raw ------------------------------------------------------------------
    Spec("motor", RAW, "Run a motor: port, speed % (-100..100), seconds", "motor A 30 1.5",
         (Param("port", "port"), Param("speed", "number", low=-100, high=100, nonzero=True),
          _seconds(_REQUIRED)),
         de=("motor",), help_de="Einen Motor laufen lassen: Anschluss, Tempo % (-100..100), "
         "Sekunden", example_de="motor A 30 1.5"),
    Spec("angle", RAW, "Turn a motor by degrees: port, degrees, speed %", "angle AB 360 40",
         (Param("port", "port"), Param("degrees", "number", low=-3600, high=3600, nonzero=True),
          Param("speed", "number", float(DEFAULT_SPEED), 1, 100)),
         de=("winkel",), help_de="Motor um Grad drehen: Anschluss, Grad, Tempo %",
         example_de="winkel AB 360 40"),
    Spec("sensors", RAW, "Read color, distance and battery once", "sensors",
         de=("sensoren",), help_de="Farbe, Abstand und Batterie einmal lesen",
         example_de="sensoren"),
    Spec("battery", RAW, "Battery voltage", "battery", (), ("volt", "voltage"),
         de=("batterie",), help_de="Batteriespannung", example_de="batterie"),
    Spec("hub", RAW, "List what is plugged into the hub", "hub", (), ("ports", "info"),
         de=("hub",), help_de="Zeigen, was am Hub eingesteckt ist", example_de="hub"),
)  # fmt: skip

BY_NAME = {spec.name: spec for spec in SPECS}
_ALIASES = {word: spec.name for spec in SPECS for word in (spec.name, *spec.aliases, *spec.de)}
TURN_WORDS = ("turn", "dreh", "drehe", "drehen")
ALL_COLOR_WORDS = sorted({*COLORS, *COLORS_DE})


def canonical(word: str) -> str | None:
    """The command name for a word or alias ("fwd" -> "forward", "zurueck" -> "back"), or None."""
    return _ALIASES.get(normalize(word))


def words(mode: str = SIMPLE, lang: str | None = None) -> list[str]:
    """Command words usable in `mode` (for Tab completion): all, or only those of `lang`."""
    found = set()
    for spec in SPECS:
        if not _usable(spec, mode):
            continue
        if lang in (None, EN):
            found.update((spec.name, *spec.aliases))
        if lang in (None, DE):
            found.update(spec.de or (spec.name,))
    return sorted(found)


def _usable(spec: Spec, mode: str) -> bool:
    return spec.mode == SIMPLE or mode == RAW


def _closest(word: str, candidates) -> str | None:
    match = difflib.get_close_matches(word, list(candidates), n=1, cutoff=0.6)
    return match[0] if match else None


def _number(text: str) -> float | None:
    try:
        value = float(text.replace(",", "."))
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _example(spec: Spec, lang: str) -> str:
    return spec.example_de if lang == DE and spec.example_de else spec.example


def _param_name(param: Param, lang: str) -> str:
    return PARAM_NAMES_DE.get(param.name, param.name) if lang == DE else param.name


def _convert(spec: Spec, param: Param, text: str, lang: str):
    where = f"{spec.shown(lang)}: {_param_name(param, lang)}"
    if param.kind == "number":
        value = _number(text)
        if value is None:
            raise ParseError(t(lang, "not_number", where=where, example=_example(spec, lang)))
        if param.nonzero and value == 0:
            raise ParseError(t(lang, "not_zero", where=where))
        low, high = param.low, param.high
        if (low is not None and value < low) or (high is not None and value > high):
            raise ParseError(t(lang, "between", where=where, low=low, high=high))
        return value
    if param.kind == "color":
        english = color_to_english(text, COLORS)
        if english is not None:
            return english
        guess = _closest(normalize(text), color_words(lang, COLORS)) or _closest(
            normalize(text), ALL_COLOR_WORDS
        )
        hint = t(lang, "hint", guess=guess) if guess else ""
        colors = ", ".join(color_words(lang, COLORS))
        raise ParseError(t(lang, "unknown_color", color=text, hint=hint, colors=colors), guess)
    if param.kind == "port":
        port = text.upper()
        if port not in PORTS:
            raise ParseError(t(lang, "bad_port", where=where, ports=", ".join(PORTS)))
        return port
    return text  # "word"


def parse(line: str, mode: str = SIMPLE, lang: str = EN) -> Command | None:
    """Parse one typed line. Returns None for an empty line, raises ParseError otherwise.

    English and German words both work; `lang` is the language of the error messages.
    """
    tokens = normalize(line.strip()).split()
    if not tokens:
        return None
    if tokens[0] in TURN_WORDS:
        if len(tokens) < 2 or _ALIASES.get(tokens[1]) not in ("left", "right"):
            raise ParseError(t(lang, "which_way"))
        tokens = tokens[1:]

    word, values = tokens[0], tokens[1:]
    color = color_to_english(word, COLORS)
    if color is not None and not values:  # "red" / "rot" is short for "led red"
        return Command("led", (color,))

    name = _ALIASES.get(word)
    if name is None:
        guess = _closest(word, words(mode))
        shown = BY_NAME[_ALIASES[guess]].shown(lang) if guess else None
        hint = t(lang, "hint", guess=shown) if shown else ""
        raise ParseError(t(lang, "unknown_word", word=word, hint=hint), shown)

    spec = BY_NAME[name]
    shown, example = spec.shown(lang), _example(spec, lang)
    if not _usable(spec, mode):
        raise ParseError(t(lang, "raw_only", name=shown))
    if len(values) > len(spec.params):
        most = len(spec.params)
        key = "no_values" if most == 0 else "at_most"
        raise ParseError(t(lang, key, name=shown, most=most, example=example))

    args = []
    for i, param in enumerate(spec.params):
        if i < len(values):
            args.append(_convert(spec, param, values[i], lang))
        elif param.required:
            raise ParseError(
                t(lang, "needs", name=shown, param=_param_name(param, lang), example=example)
            )
        else:
            args.append(param.default)
    return Command(name, tuple(args))


def help_text(mode: str = SIMPLE, name: str = "", lang: str = EN) -> str:
    """Help for all commands of `mode`, or for one command (by name or alias), in `lang`."""
    if name:
        found = canonical(name)
        if found is None:
            raise ParseError(t(lang, "no_help", name=name))
        spec = BY_NAME[found]
        text = spec.help_de if lang == DE and spec.help_de else spec.help
        lines = [
            f"{spec.shown(lang)}: {text}",
            t(lang, "help_example", example=_example(spec, lang)),
        ]
        others = [w for w in (spec.name, *spec.aliases, *spec.de) if w != spec.shown(lang)]
        if others:
            lines.append(t(lang, "help_also", words=", ".join(dict.fromkeys(others))))
        if spec.mode == RAW:
            lines.append(t(lang, "help_raw_only"))
        return "\n".join(lines)

    def block(title, specs):
        rows = [(_example(s, lang), s.help_de if lang == DE and s.help_de else s.help)
                for s in specs]  # fmt: skip
        width = max(len(example) for example, _ in rows)
        return "\n".join([title, *(f"  {ex.ljust(width)}  {text}" for ex, text in rows)])

    simple = [spec for spec in SPECS if spec.mode == SIMPLE]
    text = block(t(lang, "help_title"), simple)
    if mode == RAW:
        raw = [spec for spec in SPECS if spec.mode == RAW]
        text += "\n\n" + block(t(lang, "help_raw_title"), raw)
    return text + "\n\n" + t(lang, "help_tip")
