import time
from types import SimpleNamespace

import pytest

from lego_boost import hub as hub_mod
from lego_boost.scan import FoundHub


class FakeMotor:
    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True


class FakeHub:
    def __init__(self, hang_on_disconnect=False):
        self.motor_A, self.motor_B, self.motor_AB = FakeMotor(), FakeMotor(), FakeMotor()
        self.motor_external = None
        self.hang = hang_on_disconnect
        self.connection = SimpleNamespace(closed=False)
        self.connection.disconnect = lambda: setattr(self.connection, "closed", True)

    def disconnect(self):
        if self.hang:
            time.sleep(10)


def test_resolve_address_prefers_explicit(monkeypatch):
    monkeypatch.setenv(hub_mod.ENV_ADDRESS, "FROM-ENV")
    seen = []

    def find_hub(timeout, address=None):
        seen.append(address)
        return FoundHub("LEGO Move Hub", address, -40)

    monkeypatch.setattr(hub_mod, "find_hub", find_hub)
    assert hub_mod.resolve_address("EXPLICIT") == "EXPLICIT"
    assert hub_mod.resolve_address() == "FROM-ENV"
    assert seen == ["EXPLICIT", "FROM-ENV"]  # both waited for with a timeout


def test_resolve_address_raises_when_nothing_found(monkeypatch):
    monkeypatch.delenv(hub_mod.ENV_ADDRESS, raising=False)
    monkeypatch.setattr(hub_mod, "find_hub", lambda timeout, address=None: None)
    with pytest.raises(hub_mod.HubNotFoundError):
        hub_mod.resolve_address(timeout=0.1)


def test_boost_stops_motors_even_on_error(monkeypatch):
    fake = FakeHub()
    monkeypatch.setattr(hub_mod, "connect", lambda *a, **k: fake)
    with pytest.raises(ValueError), hub_mod.boost():
        raise ValueError("boom")
    assert fake.motor_AB.stopped and fake.motor_A.stopped and fake.motor_B.stopped
    assert fake.connection.closed


def test_boost_stops_motors_on_ctrl_c(monkeypatch):
    fake = FakeHub()
    monkeypatch.setattr(hub_mod, "connect", lambda *a, **k: fake)
    with pytest.raises(KeyboardInterrupt), hub_mod.boost():
        raise KeyboardInterrupt
    assert fake.motor_AB.stopped and fake.connection.closed


def test_robot_stops_motors_on_ctrl_c(monkeypatch):
    from types import SimpleNamespace

    from lego_boost import kid

    fake = FakeHub()
    fake.led = SimpleNamespace(set_color=lambda color: None)
    monkeypatch.setattr(kid, "connect", lambda *a, **k: fake)
    with pytest.raises(KeyboardInterrupt), kid.Robot():
        raise KeyboardInterrupt
    assert fake.motor_AB.stopped and fake.connection.closed


def test_safe_shutdown_does_not_hang(monkeypatch):
    fake = FakeHub(hang_on_disconnect=True)
    start = time.monotonic()
    hub_mod.safe_shutdown(fake, timeout=0.2)
    assert time.monotonic() - start < 2
    assert fake.connection.closed


def test_patch_pylgbst_find_device_accepts_service_uuids(monkeypatch):
    import asyncio

    from pylgbst.comms.cbleak import BleakConnection

    calls = []

    async def fake_find_device(self, hub_mac=None, hub_name=None):
        calls.append((hub_mac, hub_name))
        return "DEVICE"

    monkeypatch.setattr(BleakConnection, "find_device", fake_find_device)
    hub_mod.patch_pylgbst()
    hub_mod.patch_pylgbst()  # idempotent: must not wrap twice

    result = asyncio.run(BleakConnection.find_device(None, "AA", "Move Hub", service_uuids=["x"]))
    assert result == "DEVICE"
    assert calls == [("AA", "Move Hub")]


def test_patch_pylgbst_hub_action_ignores_other_messages():
    from pylgbst.messages import MsgHubAction, MsgPortValueSingle

    hub_mod.patch_pylgbst()
    request = MsgHubAction(MsgHubAction.DISCONNECT)
    assert not request.is_reply(MsgPortValueSingle.__new__(MsgPortValueSingle))
    assert request.is_reply(MsgHubAction(MsgHubAction.UPSTREAM_DISCONNECT))


def test_safe_shutdown_skips_the_hub_when_the_link_is_gone():
    fake = FakeHub(hang_on_disconnect=True)
    fake.connection.is_alive = lambda: False
    start = time.monotonic()
    hub_mod.safe_shutdown(fake, timeout=2)
    assert time.monotonic() - start < 0.5  # no waiting for a dead hub
    assert not fake.motor_AB.stopped and fake.connection.closed


def test_unknown_peripheral_warning_is_filtered(caplog):
    import logging

    from lego_boost.hub import quiet_pylgbst_logs

    quiet_pylgbst_logs()
    quiet_pylgbst_logs()  # idempotent
    logger = logging.getLogger("hub")
    assert len(logger.filters) == 1
    with caplog.at_level(logging.WARNING, logger="hub"):
        logger.warning("Have no dedicated class for peripheral type 0x42 (UNKNOWN) on port 0x46")
        logger.warning("something else")
    assert [r.getMessage() for r in caplog.records] == ["something else"]


class FakeConnection:
    def __init__(self):
        self.disconnects = 0

    def disconnect(self):
        self.disconnects += 1


def _fake_pylgbst(monkeypatch, *outcomes):
    """connect() with a fake scan + pylgbst. Each outcome: "hang", an exception, or a hub."""
    import threading

    import pylgbst
    import pylgbst.hub

    connections, scans = [], []
    outcomes = list(outcomes)

    def fake_connection(**_):
        connections.append(FakeConnection())
        return connections[-1]

    def fake_move_hub(conn):
        outcome = outcomes.pop(0)
        if outcome == "hang":  # pylgbst waits for a reply that never comes
            threading.Event().wait()
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    monkeypatch.setattr(hub_mod, "resolve_address", lambda *a: scans.append(a) or "addr")
    monkeypatch.setattr(pylgbst, "get_connection_bleak", fake_connection)
    monkeypatch.setattr(pylgbst.hub, "MoveHub", fake_move_hub)
    return connections, scans


def test_connect_gives_up_when_the_hub_never_answers(monkeypatch):
    connections, _ = _fake_pylgbst(monkeypatch, "hang")
    monkeypatch.setattr(hub_mod, "CONNECT_TIMEOUT", 0.3)
    start = time.monotonic()
    with pytest.raises(hub_mod.HubConnectError, match="green button"):
        hub_mod.connect()
    assert time.monotonic() - start < 3  # no retry after a timeout: waiting stays short
    assert connections[0].disconnects == 1  # pylgbst's threads are told to stop


def test_connect_tries_once_more_after_a_failed_setup(monkeypatch, capsys):
    hub = object()
    connections, scans = _fake_pylgbst(monkeypatch, RuntimeError("threads not functioning"), hub)
    assert hub_mod.connect() is hub
    assert len(scans) == 2 and connections[0].disconnects == 1
    assert "once more" in capsys.readouterr().out


def test_connect_reports_a_second_failure(monkeypatch):
    _fake_pylgbst(monkeypatch, RuntimeError("first"), RuntimeError("second"))
    with pytest.raises(hub_mod.HubConnectError, match="second"):
        hub_mod.connect()


def test_patch_pylgbst_bleak_thread_error_is_one_log_line(caplog):
    import asyncio
    import logging

    from pylgbst.comms.cbleak import BleakDriver

    hub_mod.patch_pylgbst()
    driver = BleakDriver.__new__(BleakDriver)
    driver.hub_mac, driver.hub_name = "addr", "Move Hub"

    async def failing_connect(*_a, **_k):
        raise RuntimeError("failed to discover services, device disconnected")

    import pylgbst.comms.cbleak as cbleak

    original = cbleak.BleakConnection.connect
    cbleak.BleakConnection.connect = failing_connect
    try:
        with caplog.at_level(logging.WARNING):
            asyncio.run(driver._bleak_thread())  # must not raise
    finally:
        cbleak.BleakConnection.connect = original
    assert "failed to discover services" in caplog.text


def test_patch_pylgbst_drops_a_stale_vision_reading():
    from pylgbst.messages import MsgPortInputFmtSingle, MsgPortValueSingle
    from pylgbst.peripherals import VisionSensor

    hub_mod.patch_pylgbst()
    sensor = VisionSensor(SimpleNamespace(), 3)
    sensor._port_mode = MsgPortInputFmtSingle(3, VisionSensor.COLOR_DISTANCE_FLOAT, True, 1)
    seen = []
    sensor._subscribers.add(lambda *values: seen.append(values))

    stale = MsgPortValueSingle.__new__(MsgPortValueSingle)
    stale.port, stale.payload = 3, b"\xff"  # 1 byte from the old mode (seen on Kali)
    sensor._handle_port_data(stale)  # no AssertionError traceback
    assert seen == []

    good = MsgPortValueSingle.__new__(MsgPortValueSingle)
    good.port, good.payload = 3, bytes([9, 4, 0, 0])
    sensor._handle_port_data(good)
    assert seen == [(9, 4.0)]
