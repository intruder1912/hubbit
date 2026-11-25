"""hubbit-console: drive the robot by typing commands, in one long session.

    uv run hubbit-console              # connect to the hub (press the green button)
    uv run hubbit-console --simulate   # practice without a hub
    uv run hubbit-console --lang de    # German messages (or BOOST_LANG=de); words work in both

Type `help` for the commands, `raw` for grown-up commands, `exit` to stop.
German: `hilfe`, `roh`, `ende`; `sprache deutsch` / `language english` switches messages.
The hub stays connected until `exit`, Ctrl+C or Ctrl+D.

SAFETY: drives the motors. `stop` (or Ctrl+C) stops them at once; moves last <= 10 s.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Iterable
from pathlib import Path

from hubbit.commands import PORTS, RAW, TURN_WORDS, canonical, words
from hubbit.i18n import DE, LANGS, color_word, color_words, default_lang, normalize, t
from hubbit.kid import COLORS, Robot
from hubbit.session import CONNECTED, Session

HISTORY_FILE = Path.home() / ".hubbit_history"


def status_text(session: Session) -> str:
    """One-line status for the bottom bar."""
    lang = session.lang
    state = t(lang, session.check())
    battery = "?" if session.last_battery is None else f"{session.last_battery:.1f} V"
    color = color_word(session.last_color, lang) if session.last_color else "-"
    mode = t(lang, session.mode)
    return t(lang, "status", state=state, mode=mode, battery=battery, color=color)


def completions(session: Session, text_before_cursor: str) -> list[str]:
    """Words that fit at the cursor: commands first, then colors or ports."""
    lang = session.lang
    parts = normalize(text_before_cursor).split()
    if text_before_cursor.endswith(" ") or not parts:
        parts.append("")
    current = parts[-1]
    if len(parts) == 1:
        candidates: Iterable[str] = [*words(session.mode, lang), *color_words(lang, COLORS)]
    else:
        command = canonical(parts[0]) or parts[0]
        if command == "led" and len(parts) == 2:
            candidates = color_words(lang, COLORS)
        elif command in ("motor", "angle") and len(parts) == 2:
            candidates = [port.lower() for port in PORTS]
        elif command in TURN_WORDS and len(parts) == 2:
            candidates = ["links", "rechts"] if lang == DE else ["left", "right"]
        elif command == "language" and len(parts) == 2:
            candidates = ["deutsch", "english"]
        else:
            candidates = []
    return sorted({word for word in candidates if word.startswith(current)})


def _connect_hub(address: str | None, session_lang: Callable[[], str]) -> Callable[[], Robot]:
    def connect() -> Robot:
        return Robot(address, session_lang()).__enter__()

    return connect


def _run_plain(session: Session, lines: Iterable[str], say: Callable[[str], None]) -> None:
    """No terminal (piped input, CI): read commands line by line."""
    for line in lines:
        line = line.rstrip("\n")
        say(f"{t(session.lang, session.mode)}> {line}")
        if not session.handle(line):
            return
        session.wait_idle(15)


def _run_prompt(session: Session, history: Path | None) -> None:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import Completer, Completion
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.history import FileHistory, InMemoryHistory
    from prompt_toolkit.patch_stdout import patch_stdout

    class RobotCompleter(Completer):
        def get_completions(self, document, complete_event):
            word = document.get_word_before_cursor()
            for match in completions(session, document.text_before_cursor):
                yield Completion(match, start_position=-len(word))

    def message():
        if session.mode == RAW:
            return HTML(f"<ansired><b>{t(session.lang, 'raw')}&gt;</b></ansired> ")
        return HTML(f"<ansigreen><b>{t(session.lang, 'prompt')}&gt;</b></ansigreen> ")

    def toolbar():
        text = status_text(session)
        return text if session.state == CONNECTED else HTML(f"<ansired>{text}</ansired>")

    try:
        hist = FileHistory(str(history)) if history else InMemoryHistory()
    except OSError:
        hist = InMemoryHistory()
    prompt = PromptSession(
        history=hist,
        completer=RobotCompleter(),
        complete_while_typing=False,  # Tab shows the choices
        bottom_toolbar=toolbar,
        refresh_interval=0.5,  # keeps the status bar (and the watchdog) up to date
    )
    with patch_stdout():
        while True:
            try:
                line = prompt.prompt(message)
            except EOFError:  # Ctrl+D
                return
            if not session.handle(line):
                return


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hubbit-console",
        description="Drive the LEGO BOOST robot by typing commands. Type 'help' inside.",
    )
    parser.add_argument("--address", help="hub address (default: $BOOST_HUB_ADDRESS, .env or scan)")
    parser.add_argument("--simulate", action="store_true", help="practice without a hub")
    parser.add_argument("--no-history", action="store_true", help="don't save typed commands")
    parser.add_argument(
        "--lang",
        choices=LANGS,
        default=default_lang(),
        help="language of messages: en or de (default: $BOOST_LANG, else en)",
    )
    args = parser.parse_args(argv)

    say = print
    session: Session | None = None

    def lang() -> str:
        return session.lang if session is not None else args.lang

    if args.simulate:
        from hubbit.sim import sim_robot

        def connect() -> Robot:
            return sim_robot(say, lang())
    else:
        connect = _connect_hub(args.address, lang)

    session = Session(connect, say, lang=args.lang)
    try:
        session.open()
    except Exception as err:  # noqa: BLE001 - no traceback for a hub that isn't there
        say(t(args.lang, "could_not_connect", error=err))
        return 1
    say(t(session.lang, "banner"))
    interactive = sys.stdin.isatty() and sys.stdout.isatty()
    try:
        if interactive:
            _run_prompt(session, None if args.no_history else HISTORY_FILE)
        else:
            _run_plain(session, sys.stdin, say)
    except KeyboardInterrupt:  # Ctrl+C: stop and leave
        say(t(session.lang, "ctrl_c"))
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
