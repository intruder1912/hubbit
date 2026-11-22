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


async def log_shows(pilot, app, text: str) -> bool:
    """True once `text` is in the log (lines arrive a moment after the session connects)."""
    for _ in range(100):
        if text in log_text(app):
            return True
        await pilot.pause(0.02)
    return False


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


async def hold_key(pilot, key, seconds, every=0.08):
    """Like holding a key down: the terminal sends it again every `every` seconds."""
    loop = asyncio.get_running_loop()
    end = loop.time() + seconds
    while loop.time() < end:
        await pilot.press(key)
        await pilot.pause(every)


def test_held_arrow_drives_smoothly_and_stops_after_release():
    async def test(pilot, app, sim):
        await hold_key(pilot, "up", 1.2)
        assert motor_moves(sim) == ["[sim] motor AB: running at +35% / +35%"]  # one start
        assert app.session.busy()  # still driving while the key is held
        await pilot.pause(0.6)  # let go
        assert not app.session.busy()
        assert sim[-1] == "[sim] motor AB: stop"

    run(test)


def test_tap_drives_briefly_and_turning_changes_direction_while_held():
    async def test(pilot, app, sim):
        await pilot.press("up")  # one tap: a short drive
        await idle(pilot, app)
        assert sim[-1] == "[sim] motor AB: stop"
        await hold_key(pilot, "up", 0.3)
        await hold_key(pilot, "left", 0.3)
        await idle(pilot, app)
        moves = motor_moves(sim)
        assert moves[-2:] == [
            "[sim] motor AB: running at +35% / +35%",
            "[sim] motor AB: running at -50% / +50%",
        ]

    run(test)


def test_stop_while_holding_waits_for_the_key_to_be_let_go():
    async def test(pilot, app, sim):
        await hold_key(pilot, "up", 0.4)
        await pilot.press("space")
        await hold_key(pilot, "up", 0.6)  # still held after STOP
        await idle(pilot, app)
        assert len(motor_moves(sim)) == 1  # no restart while held
        assert "Stopped." in log_text(app)
        await pilot.pause(0.5)  # let go ...
        await hold_key(pilot, "up", 0.2)  # ... and press again: drives
        assert len(motor_moves(sim)) == 2

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
        assert await log_shows(pilot, app, "Los geht's!")
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


def test_bar():
    assert tui.bar(5, 0, 10) == "[#####-----]"
    assert tui.bar(-3, 0, 10) == "[----------]"
    assert tui.bar(99, 0, 10, width=4) == "[####]"


def test_sensor_panel_shows_live_readings_in_both_languages():
    async def test(pilot, app, sim):
        session = app.session
        session.last_color, session.last_distance = "green", 5.0
        session.last_tilt, session.last_battery = "up", 6.5
        text = tui.sensor_text(session).plain
        assert "green" in text and "[#####-----] 5" in text
        assert "Tilt      up" in text and "6.5 V" in text
        session.lang = "de"
        text = tui.sensor_text(session).plain
        assert "Farbe" in text and "gruen" in text and "Neigung   oben" in text
        await pilot.pause(0.6)  # the panel itself is refreshed by the timer
        assert "gruen" in str(app.query_one("#sensors").render())

    run(test)


def test_sim_polls_the_battery_into_the_panel():
    async def test(pilot, app, sim):
        for _ in range(100):
            if app.session.last_battery is not None:
                break
            await pilot.pause(0.02)
        assert app.session.last_battery == 9.0
        assert "Pfeile: fahren" in str(app.query_one("#keys").render())

    run(test, lang="de")
