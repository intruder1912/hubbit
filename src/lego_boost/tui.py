"""boost-tui: drive the robot in a full-screen window, with buttons and arrow keys.

    uv run boost-tui              # connect to the hub (press the green button)
    uv run boost-tui --simulate   # practice without a hub
    uv run boost-tui --lang de    # German labels and messages (or BOOST_LANG=de)

Same session core as `boost-console` (`lego_boost.session`): the buttons and keys just
type commands for you, and the command line at the bottom takes every console command
(also `raw` mode). Arrow keys drive while they are held: terminals don't report key
releases, so the robot keeps going while auto-repeats arrive and stops ~0.3 s after the
last one (`Session.hold`). After STOP, a held arrow must be let go before it drives again.

SAFETY: drives the motors. Space / Escape / the STOP button stop them at once.
"""

from __future__ import annotations

import argparse
import threading
import time
from collections.abc import Callable

from rich.text import Text
from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Input, RichLog, Static

from lego_boost.console import _connect_hub, status_text
from lego_boost.i18n import LANGS, color_word, default_lang, t, tilt_word
from lego_boost.kid import Robot
from lego_boost.session import CONNECTED, DISCONNECTED, NOT_OPEN, Session

# After STOP, a still-held arrow key keeps auto-repeating; it counts as let go (and may
# drive again) once no arrow press came for this long.
RELEASE_GAP = 0.35
# Buttons run the normal console defaults (1 s, quarter turn).
PAD = ("forward", "left", "stop", "right", "back")
LIGHTS = ("red", "yellow", "green", "blue", "purple", "white", "off")
LIGHT_CSS = {"purple": "magenta", "off": "black"}
# Sensor colours (kid.COLOR_NAMES) as terminal colours for the swatch.
SWATCH = {"black": "black", "pink": "pink1", "purple": "magenta", "blue": "blue",
          "lightblue": "sky_blue1", "cyan": "cyan", "green": "green", "yellow": "yellow",
          "orange": "dark_orange", "red": "red", "white": "white"}  # fmt: skip
DISTANCE_FULL = 10.0  # the sensor's distance reading tops out around 10
BATTERY_EMPTY, BATTERY_FULL = 6.0, 9.6  # 6 AAA cells


def bar(value: float, low: float, high: float, width: int = 10) -> str:
    """ASCII bar: bar(5, 0, 10) -> "[#####-----]"."""
    filled = round(width * min(1.0, max(0.0, (value - low) / (high - low))))
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def sensor_text(session: Session) -> Text:
    """The live sensor panel (refreshed by the session's idle polling)."""
    lang = session.lang
    text = Text(t(lang, "tui_sensors") + "\n", style="bold")
    label = "{:<10}".format

    text.append(label(t(lang, "tui_color")))
    color = session.last_color
    if color in SWATCH:
        text.append("      ", style=f"on {SWATCH[color]}")
        text.append(" " + color_word(color, lang))
    else:
        text.append("-")
    text.append("\n" + label(t(lang, "tui_distance")))
    distance = session.last_distance
    if distance is None:
        text.append("-")
    else:
        text.append(f"{bar(distance, 0, DISTANCE_FULL)} {distance:g}")
    text.append("\n" + label(t(lang, "tui_tilt")))
    text.append(tilt_word(session.last_tilt, lang) if session.last_tilt else "-")
    text.append("\n" + label(t(lang, "tui_battery")))
    volts = session.last_battery
    if volts is None:
        text.append("-")
    else:
        low = volts < 7.0
        style = "bold red" if low else ""
        text.append(f"{bar(volts, BATTERY_EMPTY, BATTERY_FULL)} {volts:.1f} V", style=style)
    return text


class LogLine(Message):
    """Text for the log pane (posted from any thread)."""

    def __init__(self, text: str) -> None:
        super().__init__()
        self.text = text


class CommandLine(Input):
    """The command line. While it is empty, space is "stop" instead of a typed blank."""

    def check_consume_key(self, key: str, character: str | None) -> bool:
        if key == "space" and not self.value:
            return False
        return super().check_consume_key(key, character)


class BoostTui(App):
    TITLE = "LEGO BOOST"
    ENABLE_COMMAND_PALETTE = False  # keep the screen simple for kids
    CSS = """
    #status { height: 1; padding: 0 1; background: $success-darken-2; color: $text; }
    #status.lost { background: $error; }
    #main { height: 1fr; }
    #controls { width: 46; padding: 0 1; }
    #pad { grid-size: 3 3; grid-gutter: 0 1; height: 9; }
    #pad Button { width: 100%; height: 3; }
    #pad .gap { height: 3; }
    #stop { background: $error; text-style: bold; }
    #lights { grid-size: 4 2; grid-gutter: 0 1; height: 6; }
    #lights Button { min-width: 6; width: 100%; height: 3; }
    #ask { height: 3; }
    #ask Button { width: 1fr; }
    #sensors { height: 5; margin-top: 1; padding: 0 1; border-left: tall $primary; }
    #log { width: 1fr; border: round $primary; }
    #keys { height: 1; padding: 0 1; background: $panel; color: $text-muted; }
    """
    BINDINGS = [
        Binding("up", "drive('forward')", show=False, priority=True),
        Binding("down", "drive('back')", show=False, priority=True),
        Binding("left", "drive('left')", show=False, priority=True),
        Binding("right", "drive('right')", show=False, priority=True),
        Binding("space", "space", show=False, priority=True),
        Binding("escape", "stop", show=False, priority=True),
        Binding("f1", "help", show=False),
        Binding("ctrl+q", "quit", show=False, priority=True),
        Binding("ctrl+c", "quit", show=False, priority=True),
    ]

    def __init__(self, connect: Callable[[], Robot], lang: str) -> None:
        super().__init__()
        self.session = Session(connect, self._say, lang=lang, poll=0.5)
        self._shown_lang = ""
        self._connecting = False
        self._last_arrow = 0.0
        self._stop_latched = False

    # --- layout -------------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Static(id="status")
        with Horizontal(id="main"):
            with VerticalScroll(id="controls"):  # scrolls on very small terminals
                with Grid(id="pad"):
                    for name in ("gap", "forward", "gap", "left", "stop", "right"):
                        yield self._pad_cell(name)
                    for name in ("gap", "back", "gap"):
                        yield self._pad_cell(name)
                with Grid(id="lights"):
                    for color in LIGHTS:
                        button = Button("", id=f"light-{color}")
                        button.styles.background = LIGHT_CSS.get(color, color)
                        button.styles.color = "black" if color in ("yellow", "white") else "white"
                        yield button
                with Horizontal(id="ask"):
                    yield Button("", id="ask-color")
                    yield Button("", id="ask-distance")
                yield Static(id="sensors")
            yield RichLog(id="log", wrap=True, markup=False, min_width=20)
        yield CommandLine(id="command")
        yield Static(id="keys")  # own key hints: textual's Footer can't switch language

    @staticmethod
    def _pad_cell(name: str):
        return Static(classes="gap") if name == "gap" else Button("", id=name)

    def on_mount(self) -> None:
        self.begin_capture_print(self)  # Robot / pylgbst prints go to the log
        self._relabel()
        self._tick()
        self.set_interval(0.5, self._tick)  # status bar + watchdog
        self.query_one("#command", Input).focus()
        self._connecting = True
        self._in_background(self._open)

    def _relabel(self) -> None:
        lang = self.session.lang
        if lang == self._shown_lang:
            return
        self._shown_lang = lang
        for name in PAD:
            self.query_one(f"#{name}", Button).label = t(lang, f"tui_{name}")
        for color in LIGHTS:
            self.query_one(f"#light-{color}", Button).label = color_word(color, lang)
        self.query_one("#ask-color", Button).label = t(lang, "tui_ask_color")
        self.query_one("#ask-distance", Button).label = t(lang, "tui_ask_distance")
        self.query_one("#command", Input).placeholder = t(lang, "tui_placeholder")
        self.query_one("#keys", Static).update(t(lang, "tui_keys"))

    def _tick(self) -> None:
        self.query_one("#sensors", Static).update(sensor_text(self.session))
        status = self.query_one("#status", Static)
        if self.session.state == NOT_OPEN:
            status.update(t(self.session.lang, "connecting"))
            return
        status.update(status_text(self.session))
        status.set_class(self.session.state != CONNECTED, "lost")

    # --- connection (threads: scanning blocks for seconds) -------------------
    @staticmethod
    def _in_background(fn: Callable[[], None]) -> None:
        """Run a connect in a daemon thread. Not a textual worker: those run in asyncio's
        executor, and quitting would wait for a connect that hangs (seen on Kali)."""
        threading.Thread(target=fn, daemon=True, name="boost-tui connect").start()

    def _open(self) -> None:
        try:
            self.session.open()
        except Exception as err:  # noqa: BLE001 - stay in the window, offer 'reconnect'
            self.session.state = DISCONNECTED
            self._say(t(self.session.lang, "could_not_connect", error=err))
            self._say(t(self.session.lang, "press_reconnect", why=""))
            return
        finally:
            self._connecting = False
        self._last_arrow = 0.0
        self._stop_latched = False
        self._say(t(self.session.lang, "tui_banner"))

    def _reconnect(self) -> None:
        try:
            self.session.handle("reconnect")
        finally:
            self._connecting = False
        self._last_arrow = 0.0
        self._stop_latched = False

    # --- output -------------------------------------------------------------
    def _say(self, text: str) -> None:
        self.post_message(LogLine(text))  # thread-safe; the worker thread talks too

    def on_log_line(self, message: LogLine) -> None:
        self.query_one("#log", RichLog).write(message.text)

    def on_print(self, event: events.Print) -> None:
        if event.text.strip():
            self.query_one("#log", RichLog).write(event.text.rstrip("\n"))

    # --- input --------------------------------------------------------------
    def run_command(self, line: str) -> None:
        """Run one console command line (buttons, keys and the command line all end here)."""
        from lego_boost.commands import ParseError, parse

        try:
            cmd = parse(line, self.session.mode, self.session.lang)
        except ParseError:
            cmd = None  # the session prints the friendly error
        if cmd is not None and cmd.name == "exit":
            self.exit()
            return
        if cmd is not None and cmd.name == "reconnect":
            if self._connecting:  # one scan at a time
                self._say(t(self.session.lang, "still_connecting"))
                return
            self._connecting = True
            self._in_background(self._reconnect)
            return
        self.session.handle(line)
        self._relabel()  # 'sprache deutsch' / 'language english'
        self._tick()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        line = event.value
        event.input.value = ""
        if line.strip():
            self._say(f"> {line}")
            self.run_command(line)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        name = event.button.id or ""
        if name.startswith("light-"):
            self.run_command(f"led {name.removeprefix('light-')}")
        elif name.startswith("ask-"):
            self.run_command(name.removeprefix("ask-"))
        elif name in PAD:
            self.run_command(name)
        self.query_one("#command", Input).focus()

    def check_action(self, action: str, parameters: tuple) -> bool | None:
        """Arrow keys and space belong to the command line while something is typed in it."""
        if action in ("drive", "space") and isinstance(self.focused, Input):
            return not self.focused.value
        return True

    def action_drive(self, direction: str) -> None:
        """Arrow key (pressed or auto-repeated): drive while it is held, see Session.hold."""
        now = time.monotonic()
        gap, self._last_arrow = now - self._last_arrow, now
        if self._stop_latched:
            if gap < RELEASE_GAP:
                return  # the arrow is still held from before STOP: ignore it
            self._stop_latched = False
        if self.session.state == CONNECTED:
            self.session.hold(direction)

    def action_space(self) -> None:
        self.action_stop()

    def action_stop(self) -> None:
        self._stop_latched = True  # a held arrow must be let go before it drives again
        if self.session.state == CONNECTED:
            self.session.handle("stop")

    def action_help(self) -> None:
        self.run_command("help")

    def on_unmount(self) -> None:
        self.session.close()  # stop motors and disconnect when the window closes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="boost-tui",
        description="Drive the LEGO BOOST robot with buttons and arrow keys.",
    )
    parser.add_argument("--address", help="hub address (default: $BOOST_HUB_ADDRESS, .env or scan)")
    parser.add_argument("--simulate", action="store_true", help="practice without a hub")
    parser.add_argument(
        "--lang",
        choices=LANGS,
        default=default_lang(),
        help="language of labels and messages: en or de (default: $BOOST_LANG, else en)",
    )
    args = parser.parse_args(argv)
    app: BoostTui | None = None

    def lang() -> str:
        return app.session.lang if app is not None else args.lang

    if args.simulate:
        from lego_boost.sim import sim_robot

        def connect() -> Robot:
            return sim_robot(app._say, lang())
    else:
        connect = _connect_hub(args.address, lang)

    app = BoostTui(connect, args.lang)
    try:
        app.run()
    finally:
        app.session.close()  # also on crashes (safe to call twice)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
