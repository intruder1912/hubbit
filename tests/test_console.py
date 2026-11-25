import io

import pytest

from hubbit import console
from hubbit.session import CLOSED, Session
from hubbit.sim import sim_robot


@pytest.fixture
def session():
    out = []
    s = Session(lambda: sim_robot(out.append), out.append)
    s.open()
    s.out = out
    yield s
    s.close(timeout=0.5)


def test_completion_commands_colors_and_ports(session):
    assert "forward" in console.completions(session, "fo")
    assert "red" in console.completions(session, "re")  # bare color = led
    assert console.completions(session, "led gr") == ["green"]
    assert "motor" not in console.completions(session, "mo")
    session.mode = "raw"
    assert "motor" in console.completions(session, "mo")
    assert console.completions(session, "motor ") == ["a", "ab", "b", "c", "d"]
    assert console.completions(session, "turn ") == ["left", "right"]
    assert console.completions(session, "forward ") == []


def test_status_text(session):
    assert "connected" in console.status_text(session)
    assert "mode: simple" in console.status_text(session)
    session.handle("raw")
    session.handle("battery")
    session.wait_idle(2)
    assert "battery: 9.0 V" in console.status_text(session)


def test_simulated_session_from_piped_input(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("forward 0.1\nblue\nraw\nbattery\nexit\nleft\n"))
    assert console.main(["--simulate"]) == 0
    out = capsys.readouterr().out
    assert "[sim] motor AB: 0.1 s at +35% / +35%" in out
    assert "[sim] light: blue" in out
    assert "Battery: 9.00 V" in out
    assert "raw> left" not in out  # nothing runs after exit
    assert "Robot stopped. Bye!" in out


def test_no_hub_found_is_a_friendly_error(monkeypatch, capsys):
    def no_hub():
        raise RuntimeError("No Move Hub found within 15s.")

    monkeypatch.setattr(console, "_connect_hub", lambda address, lang: no_hub)
    assert console.main([]) == 1
    assert "Could not connect: No Move Hub found" in capsys.readouterr().out


def test_interactive_prompt_runs_commands_until_exit(session):
    from prompt_toolkit.application import create_app_session
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    with create_pipe_input() as pipe, create_app_session(input=pipe, output=DummyOutput()):
        pipe.send_text("led red\r")
        pipe.send_text("raw\r")
        pipe.send_text("exit\r")
        console._run_prompt(session, history=None)
    session.wait_idle(2)
    assert "[sim] light: red" in session.out
    assert session.mode == "raw"
    session.close()
    assert session.state == CLOSED
