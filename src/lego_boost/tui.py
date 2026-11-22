"""boost-tui: drive the robot in a full-screen window, with buttons and arrow keys.

    uv run boost-tui              # connect to the hub (press the green button)
    uv run boost-tui --simulate   # practice without a hub
    uv run boost-tui --lang de    # German labels and messages (or BOOST_LANG=de)

Same session core as `boost-console` (`lego_boost.session`): the buttons and keys just
type commands for you, and the command line at the bottom takes every console command
(also `raw` mode). Arrow keys drive in short steps; holding a key keeps the robot going,
letting go stops it within one step (terminals don't report key releases, so a key press
that arrives while a step is still running is dropped instead of queued).

SAFETY: drives the motors. Space / Escape / the STOP button stop them at once.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Footer, Input, RichLog, Static

from lego_boost.console import _connect_hub, status_text
from lego_boost.i18n import LANGS, color_word, default_lang, t
from lego_boost.kid import Robot
from lego_boost.session import CONNECTED, DISCONNECTED, NOT_OPEN, Session

# One arrow-key step: short, so the robot stops soon after the key is let go.
STEPS = {
    "forward": "forward 0.3",
    "back": "back 0.3",
    "left": "left 20",
    "right": "right 20",
}
# Buttons run the normal console defaults (1 s, quarter turn).
PAD = ("forward", "left", "stop", "right", "back")
LIGHTS = ("red", "yellow", "green", "blue", "purple", "white", "off")
LIGHT_CSS = {"purple": "magenta", "off": "black"}


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
    #pad { grid-size: 3 3; grid-gutter: 0 1; height: 11; }
    #pad Button { width: 100%; height: 3; }
    #pad .gap { height: 3; }
    #stop { background: $error; text-style: bold; }
    #lights { grid-size: 4 2; grid-gutter: 0 1; height: 6; }
    #lights Button { min-width: 6; width: 100%; height: 3; }
    #ask { height: 3; margin-top: 1; }
    #ask Button { width: 1fr; }
    #log { width: 1fr; border: round $primary; }
    """
    BINDINGS = [
        Binding("up", "drive('forward')", "drive", priority=True),
        Binding("down", "drive('back')", show=False, priority=True),
        Binding("left", "drive('left')", show=False, priority=True),
        Binding("right", "drive('right')", show=False, priority=True),
        Binding("space", "space", "stop", priority=True),
        Binding("escape", "stop", show=False, priority=True),
        Binding("f1", "help", "help"),
        Binding("ctrl+q", "quit", "quit", priority=True),
        Binding("ctrl+c", "quit", show=False, priority=True),
    ]

    def __init__(self, connect: Callable[[], Robot], lang: str) -> None:
        super().__init__()
        self.session = Session(connect, self._say, lang=lang)
        self._shown_lang = ""
        self._connecting = False

    # --- layout -------------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Static(id="status")
        with Horizontal(id="main"):
            with Vertical(id="controls"):
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
            yield RichLog(id="log", wrap=True, markup=False, min_width=20)
        yield CommandLine(id="command")
        yield Footer()

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
        self.run_worker(self._open, thread=True, group="connect")

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

    def _tick(self) -> None:
        status = self.query_one("#status", Static)
        if self.session.state == NOT_OPEN:
            status.update(t(self.session.lang, "connecting"))
            return
        status.update(status_text(self.session))
        status.set_class(self.session.state != CONNECTED, "lost")

    # --- connection (threads: scanning blocks for seconds) -------------------
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
        self._say(t(self.session.lang, "tui_banner"))

    def _reconnect(self) -> None:
        try:
            self.session.handle("reconnect")
        finally:
            self._connecting = False

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
            if not self._connecting:  # one scan at a time
                self._connecting = True
                self.run_worker(self._reconnect, thread=True, group="connect")
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
        if self.session.state != CONNECTED or self.session.busy():
            return  # drop presses while a step runs: no queue that keeps driving
        self.session.handle(STEPS[direction])

    def action_space(self) -> None:
        self.action_stop()

    def action_stop(self) -> None:
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
    parser.add_argument("--address", help="hub address (default: $BOOST_HUB_ADDRESS or scan)")
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
