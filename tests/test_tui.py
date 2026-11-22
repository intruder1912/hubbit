"""boost-tui with textual's Pilot against the simulated hub (no hardware, no real terminal)."""

import asyncio

import pytest
from textual.widgets import Button, Input, RichLog

from lego_boost import tui
from lego_boost.session import CLOSED, CONNECTED, DISCONNECTED
from lego_boost.sim import sim_robot


def run(test, lang="en", connect=None):
    """Run `test(pilot, app, sim_lines)` inside a headless app."""
    sim_lines: list[str] = []

    def default_connect():
        return sim_robot(sim_lines.append, app.session.lang)

    app = tui.BoostTui(connect or default_connect, lang)

    async def main():
        async with app.run_test(size=(110, 32)) as pilot:
            for _ in range(100):
                if app.session.state not in ("not open",):
                    break
                await pilot.pause(0.02)
            await test(pilot, app, sim_lines)

    asyncio.run(main())
    return app


async def idle(pilot, app):
    for _ in range(200):
        if not app.session.busy():
            break
        await pilot.pause(0.02)
    await pilot.pause(0.05)


def log_text(app) -> str:
    return "\n".join(strip.text for strip in app.query_one("#log", RichLog).lines)


def motor_moves(lines):
    return [line for line in lines if "motor AB:" in line and "stop" not in line]


def test_buttons_drive_and_light():
    async def test(pilot, app, sim):
        assert app.session.state == CONNECTED
        await pilot.click("#forward")
        await idle(pilot, app)
        assert "[sim] motor AB: 1 s at +35% / +35%" in sim
        await pilot.click("#light-blue")
        await idle(pilot, app)
        assert "[sim] light: blue" in sim
        await pilot.click("#ask-color")
        await idle(pilot, app)
        assert "I see: nothing" in log_text(app)

    app = run(test)
    assert app.session.state == CLOSED  # closing the window stops and disconnects


def test_arrow_keys_step_and_drop_presses_while_busy():
    async def test(pilot, app, sim):
        await pilot.press("up", "up", "up", "up")  # a held key repeats fast
        await idle(pilot, app)
        assert motor_moves(sim) == ["[sim] motor AB: 0.3 s at +35% / +35%"]
        await pilot.press("left")
        await idle(pilot, app)
        assert motor_moves(sim)[-1].endswith("-50% / +50%")

    run(test)


def test_space_and_escape_stop_but_typing_keeps_its_keys():
    async def test(pilot, app, sim):
        await pilot.press("up")
        await pilot.press("space")
        await idle(pilot, app)
        assert "Stopped." in log_text(app)
        command = app.query_one("#command", Input)
        await pilot.press("l", "e", "d", "space", "r", "e", "d", "left", "left", "up")
        assert command.value == "led red"  # space typed, arrows moved the cursor
        assert len(motor_moves(sim)) == 1  # no extra drive while typing
        await pilot.press("enter")
        await idle(pilot, app)
        assert "[sim] light: red" in sim
        assert command.value == ""
        await pilot.press("f", "o", "escape")  # escape always stops
        await idle(pilot, app)
        assert log_text(app).count("Stopped.") == 2

    run(test)


def test_command_line_runs_console_commands_and_raw_mode():
    async def test(pilot, app, sim):
        for line in ("raw", "motor A 30 0.2", "battery", "dance"):
            app.query_one("#command", Input).value = line
            await pilot.press("enter")
            await idle(pilot, app)
        text = log_text(app)
        assert "Raw mode." in text
        assert "[sim] motor A: 0.2 s at +30% / +30%" in sim
        assert "Battery: 9.00 V" in text
        assert "I don't know 'dance'" in text
        assert "mode: raw" in str(app.query_one("#status").render())

    run(test)


def test_exit_closes_the_app():
    async def test(pilot, app, sim):
        app.query_one("#command", Input).value = "exit"
        await pilot.press("enter")
        await pilot.pause(0.1)

    app = run(test)
    assert app.session.state == CLOSED
    assert app.return_code in (0, None)


def test_german_labels_and_switching():
    async def test(pilot, app, sim):
        assert str(app.query_one("#forward", Button).label) == "^ Vor"
        assert str(app.query_one("#light-green", Button).label) == "gruen"
        assert "Los geht's!" in log_text(app)
        app.query_one("#command", Input).value = "language english"
        await pilot.press("enter")
        assert str(app.query_one("#forward", Button).label) == "^ Forward"
        assert str(app.query_one("#light-green", Button).label) == "green"

    run(test, lang="de")


def test_no_hub_stays_open_and_offers_reconnect():
    tries = []

    def connect():
        tries.append(1)
        if len(tries) == 1:
            raise RuntimeError("No Move Hub found within 15s.")
        return sim_robot(lambda text: None)

    async def test(pilot, app, sim):
        assert app.session.state == DISCONNECTED
        assert "Could not connect: No Move Hub found" in log_text(app)
        await pilot.press("up")  # nothing to drive: ignored
        app.query_one("#command", Input).value = "reconnect"
        await pilot.press("enter")
        for _ in range(100):
            if app.session.state == CONNECTED:
                break
            await pilot.pause(0.02)
        assert app.session.state == CONNECTED
        assert "lost" not in app.query_one("#status").classes

    run(test, connect=connect)
    assert len(tries) == 2


@pytest.mark.parametrize("argv", [["--help"]])
def test_cli_help(argv, capsys):
    with pytest.raises(SystemExit):
        tui.main(argv)
    assert "--simulate" in capsys.readouterr().out
