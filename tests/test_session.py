import threading
import time
from types import SimpleNamespace

import pytest

from lego_boost import kid
from lego_boost.kid import Robot
from lego_boost.session import CLOSED, CONNECTED, DISCONNECTED, Session


class FakeMotor:
    def __init__(self, hang=False):
        self.calls = []
        self.stops = 0
        self.cmd_in_progress = False
        self.hang = hang

    def timed(self, seconds, a=1.0, b=None, wait_complete=True):
        self.calls.append(("timed", seconds, a, b, wait_complete))
        if self.hang:
            threading.Event().wait()  # pylgbst waiting for a reply that never comes

    def angled(self, degrees, speed, wait_complete=True):
        self.calls.append(("angled", degrees, speed, wait_complete))

    def stop(self):
        self.stops += 1


class FakeHub:
    def __init__(self, hang=False):
        self.motor_A, self.motor_B = FakeMotor(), FakeMotor()
        self.motor_AB = FakeMotor(hang)
        self.motor_external = self.port_C = self.port_D = None
        self.vision_sensor = None
        self.led = SimpleNamespace(colors=[])
        self.led.set_color = self.led.colors.append
        self.voltage = SimpleNamespace(voltage=8.123)
        self.peripherals = {0x37: "EncodedMotor on AB"}
        self.alive = True
        self.closed = False
        self.connection = SimpleNamespace(
            is_alive=lambda: self.alive, disconnect=lambda: setattr(self, "closed", True)
        )

    def disconnect(self):
        pass


@pytest.fixture
def make():
    sessions = []

    def factory(hang=False, grace=5.0):
        hubs = []

        def connect():
            robot = Robot()
            robot.hub = FakeHub(hang)
            hubs.append(robot.hub)
            return robot

        out = []
        session = Session(connect, out.append, grace=grace)
        session.open()
        sessions.append(session)
        return session, hubs, out

    yield factory
    for session in sessions:
        session.close(timeout=0.5)


def test_forward_starts_motors_without_blocking_and_waits(make):
    session, hubs, _ = make()
    start = time.monotonic()
    assert session.handle("forward 0.2")
    assert session.wait_idle(2)
    assert time.monotonic() - start >= 0.2
    speed = kid.DEFAULT_SPEED / 100
    assert hubs[0].motor_AB.calls == [("timed", 0.2, speed, speed, False)]


def test_turn_by_degrees_uses_calibration(make):
    session, hubs, _ = make()
    session.handle("left 45")
    assert session.wait_idle(2)
    seconds = hubs[0].motor_AB.calls[0][1]
    assert seconds == pytest.approx(kid.QUARTER_TURN_SECONDS / 2)


def test_stop_interrupts_a_long_move_and_drops_the_queue(make):
    session, hubs, out = make()
    session.handle("forward 10")
    session.handle("back 10")
    time.sleep(0.1)
    start = time.monotonic()
    session.handle("stop")
    assert session.wait_idle(2)
    assert time.monotonic() - start < 1.0
    motor = hubs[0].motor_AB
    assert len(motor.calls) == 1  # "back 10" never ran
    assert motor.stops >= 1
    assert "Stopped." in out
    session.handle("forward 0.1")  # still usable afterwards
    assert session.wait_idle(2)
    assert len(motor.calls) == 2


def test_sensor_and_led_commands_report_back(make):
    session, hubs, out = make()
    session.handle("blue")
    session.handle("raw")
    session.handle("battery")
    session.handle("hub")
    assert session.wait_idle(2)
    assert hubs[0].led.colors[-1] == kid.COLORS["blue"]
    assert "Battery: 8.12 V" in out
    assert any("EncodedMotor on AB" in line for line in out)
    assert session.last_battery == 8.12


def test_a_failing_command_does_not_end_the_session(make):
    session, _, out = make()
    session.handle("raw")
    session.handle("motor C 30 1")  # nothing plugged into C
    assert session.wait_idle(2)
    assert any("did not work" in line and "port C" in line for line in out)
    assert session.state == CONNECTED


def test_parse_errors_are_printed(make):
    session, _, out = make()
    assert session.handle("dance")
    assert "I don't know 'dance'" in out[-1]
    session.handle("motor A 30 1")
    assert "raw mode" in out[-1]


def test_lost_link_only_allows_reconnect_or_exit(make):
    session, hubs, out = make()
    hubs[0].alive = False
    session.handle("forward 1")
    assert session.state == DISCONNECTED
    assert any("Lost the hub" in line for line in out)
    assert hubs[0].motor_AB.calls == []
    session.handle("reconnect")
    assert session.state == CONNECTED and len(hubs) == 2
    assert hubs[0].closed  # old connection cleaned up
    session.handle("forward 0.1")
    assert session.wait_idle(2)
    assert len(hubs[1].motor_AB.calls) == 1


def test_watchdog_notices_a_hub_that_stopped_answering(make):
    session, hubs, out = make(hang=True, grace=0.2)
    session.handle("forward 0.1")
    time.sleep(0.5)
    assert session.check() == DISCONNECTED
    assert any("stopped answering" in line for line in out)
    session.handle("reconnect")  # a fresh worker; the stuck one is left behind
    assert session.state == CONNECTED


def test_failed_reconnect_stays_in_the_console(make):
    session, hubs, out = make()
    hubs[0].alive = False
    session.check()

    def no_hub():
        raise RuntimeError("No Move Hub found")

    session._connect = no_hub
    assert session.handle("reconnect")
    assert session.state == DISCONNECTED
    assert "Could not connect: No Move Hub found" in out[-1]


def test_exit_and_close_stop_motors_and_disconnect(make):
    session, hubs, _ = make()
    session.handle("forward 10")
    time.sleep(0.1)
    assert session.handle("exit") is False
    session.close()
    assert session.state == CLOSED
    assert hubs[0].motor_AB.stops >= 1 and hubs[0].closed
    session.close()  # twice is fine
