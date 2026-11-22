"""Typed robot commands: turn a line like "forward 2" into a `Command`.

Pure logic, no hub access - the console's `Session` runs the commands. Used by
`boost-console` (and later the TUI).

    >>> parse("Forward 1,5")
    Command(name='forward', args=(1.5,))
    >>> parse("turn left 45")
    Command(name='left', args=(45.0,))

Simple commands work in both modes; raw commands only after typing `raw`.
Words come from an alias table (`Spec.aliases`), so other languages can be added there.
"""

from __future__ import annotations

import difflib
import math
from dataclasses import dataclass

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
         ("f", "fwd", "go")),
    Spec("back", SIMPLE, "Drive backward (seconds)", "back 1", (_seconds(),),
         ("b", "backward", "backwards", "reverse")),
    Spec("left", SIMPLE, "Turn left on the spot (degrees, about)", "left 90", (_degrees(),),
         ("l",)),
    Spec("right", SIMPLE, "Turn right on the spot (degrees, about)", "right 45", (_degrees(),),
         ("r",)),
    Spec("led", SIMPLE, "Change the hub's light", "led red", (Param("color", "color"),),
         ("light", "lamp")),
    Spec("color", SIMPLE, "Which color does the sensor see?", "color", (), ("colour", "see")),
    Spec("distance", SIMPLE, "How far away is something? (bigger = farther)", "distance", (),
         ("dist",)),
    Spec("stop", SIMPLE, "Stop the motors right now", "stop", (), ("s", "halt"), queued=False),
    Spec("help", SIMPLE, "Show the commands", "help forward",
         (Param("command", "word", ""),), ("?", "h"), queued=False),
    Spec("raw", SIMPLE, "Switch to raw mode (for grown-ups)", "raw", queued=False),
    Spec("simple", SIMPLE, "Switch back to simple mode", "simple", queued=False),
    Spec("reconnect", SIMPLE, "Connect again after the hub was lost", "reconnect",
         queued=False),
    Spec("exit", SIMPLE, "Stop everything and say goodbye", "exit", (), ("quit", "q", "bye"),
         queued=False),
    # --- raw ------------------------------------------------------------------
    Spec("motor", RAW, "Run a motor: port, speed % (-100..100), seconds", "motor A 30 1.5",
         (Param("port", "port"), Param("speed", "number", low=-100, high=100, nonzero=True),
          _seconds(_REQUIRED))),
    Spec("angle", RAW, "Turn a motor by degrees: port, degrees, speed %", "angle AB 360 40",
         (Param("port", "port"), Param("degrees", "number", low=-3600, high=3600, nonzero=True),
          Param("speed", "number", float(DEFAULT_SPEED), 1, 100))),
    Spec("sensors", RAW, "Read color, distance and battery once", "sensors"),
    Spec("battery", RAW, "Battery voltage", "battery", (), ("volt", "voltage")),
    Spec("hub", RAW, "List what is plugged into the hub", "hub", (), ("ports", "info")),
)  # fmt: skip

BY_NAME = {spec.name: spec for spec in SPECS}
_ALIASES = {word: spec.name for spec in SPECS for word in (spec.name, *spec.aliases)}


def words(mode: str = SIMPLE) -> list[str]:
    """All command words usable in `mode` (for Tab completion)."""
    return sorted(word for word, name in _ALIASES.items() if _usable(BY_NAME[name], mode))


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


def _convert(spec: Spec, param: Param, text: str):
    where = f"{spec.name}: {param.name}"
    if param.kind == "number":
        value = _number(text)
        if value is None:
            raise ParseError(f"{where} must be a number, e.g. '{spec.example}'")
        if param.nonzero and value == 0:
            raise ParseError(f"{where} must not be 0")
        low, high = param.low, param.high
        if (low is not None and value < low) or (high is not None and value > high):
            raise ParseError(f"{where} must be between {low:g} and {high:g}")
        return value
    if param.kind == "color":
        if text in COLORS:
            return text
        guess = _closest(text, COLORS)
        hint = f" Did you mean '{guess}'?" if guess else ""
        raise ParseError(
            f"I don't know the color '{text}'.{hint} Colors: {', '.join(COLORS)}", guess
        )
    if param.kind == "port":
        port = text.upper()
        if port not in PORTS:
            raise ParseError(f"{where} must be one of {', '.join(PORTS)}")
        return port
    return text  # "word"


def parse(line: str, mode: str = SIMPLE) -> Command | None:
    """Parse one typed line. Returns None for an empty line, raises ParseError otherwise."""
    tokens = line.strip().lower().split()
    if not tokens:
        return None
    if tokens[0] == "turn":
        if len(tokens) < 2 or tokens[1] not in ("left", "right"):
            raise ParseError("Say which way: 'turn left 90' or 'turn right 90'")
        tokens = tokens[1:]

    word, values = tokens[0], tokens[1:]
    if word in COLORS and not values:  # "red" is short for "led red"
        return Command("led", (word,))

    name = _ALIASES.get(word)
    if name is None:
        guess = _closest(word, words(mode))
        guess = _ALIASES[guess] if guess else None
        hint = f" Did you mean '{guess}'?" if guess else ""
        raise ParseError(f"I don't know '{word}'.{hint} Type 'help' to see all commands.", guess)

    spec = BY_NAME[name]
    if not _usable(spec, mode):
        raise ParseError(f"'{name}' only works in raw mode. Type 'raw' to switch.")
    if len(values) > len(spec.params):
        most = len(spec.params)
        what = "no values" if most == 0 else f"at most {most} value" + ("s" if most > 1 else "")
        raise ParseError(f"'{name}' takes {what}, e.g. '{spec.example}'")

    args = []
    for i, param in enumerate(spec.params):
        if i < len(values):
            args.append(_convert(spec, param, values[i]))
        elif param.required:
            raise ParseError(f"'{name}' needs a {param.name}, e.g. '{spec.example}'")
        else:
            args.append(param.default)
    return Command(name, tuple(args))


def help_text(mode: str = SIMPLE, name: str = "") -> str:
    """Help for all commands of `mode`, or for one command (by name or alias)."""
    if name:
        canonical = _ALIASES.get(name.lower())
        if canonical is None:
            raise ParseError(f"No help for '{name}'. Type 'help' to see all commands.")
        spec = BY_NAME[canonical]
        lines = [f"{spec.name}: {spec.help}", f"  example: {spec.example}"]
        if spec.aliases:
            lines.append(f"  also: {', '.join(spec.aliases)}")
        if spec.mode == RAW:
            lines.append("  (raw mode only)")
        return "\n".join(lines)

    def block(title, specs):
        width = max(len(spec.example) for spec in specs)
        rows = [f"  {spec.example.ljust(width)}  {spec.help}" for spec in specs]
        return "\n".join([title, *rows])

    simple = [spec for spec in SPECS if spec.mode == SIMPLE]
    text = block("Commands:", simple)
    if mode == RAW:
        text += "\n\n" + block("Raw commands:", [spec for spec in SPECS if spec.mode == RAW])
    return text + "\n\nTip: a color name alone works too, e.g. 'blue'."
