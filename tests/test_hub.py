import time
from types import SimpleNamespace

import pytest

from hubbit import hub as hub_mod
from hubbit.scan import FoundHub


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

    from hubbit import kid

    fake = FakeHub()
    fake.led = SimpleNamespace(set_color=lambda color: None)
    monkeypatch.setattr(kid, "connect", lambda *a, **k: fake)
    with kid.Robot():  # Ctrl+C is swallowed: no traceback for kids
        raise KeyboardInterrupt
    assert fake.motor_AB.stopped and fake.connection.closed


def test_robot_lets_other_errors_through(monkeypatch):
    from types import SimpleNamespace

    from hubbit import kid

    fake = FakeHub()
    fake.led = SimpleNamespace(set_color=lambda color: None)
    monkeypatch.setattr(kid, "connect", lambda *a, **k: fake)
    with pytest.raises(ValueError), kid.Robot():
        raise ValueError("boom")
    assert fake.motor_AB.stopped and fake.connection.closed


def test_safe_shutdown_does_not_hang(monkeypatch):
    fake = FakeHub(hang_on_disconnect=True)
    start = time.monotonic()
    hub_mod.safe_shutdown(fake, timeout=0.2)
    assert time.monotonic() - start < 2
    assert fake.connection.closed


def test_pinned_pylgbst_has_the_upstream_fixes():
    # undera/pylgbst#142 / #144: guards against moving the pin back to a commit without them
    import asyncio
    import inspect

    import bleak
    from pylgbst.comms.cbleak import BleakConnection
    from pylgbst.messages import MsgHubAction, MsgPortValueSingle

    params = inspect.signature(BleakConnection.find_device).parameters.values()
    assert any(p.kind is inspect.Parameter.VAR_KEYWORD for p in params)

    seen = {}

    class FakeScanner:
        def __init__(self, detection_callback, **kwargs):
            seen.update(kwargs)
            self.callback = detection_callback

        async def start(self):
            device = type("D", (), {"address": "AA", "name": "Move Hub"})()
            await self.callback(device, None)

        async def stop(self):
            pass

    original = bleak.BleakScanner
    bleak.BleakScanner = FakeScanner
    try:
        asyncio.run(BleakConnection().find_device("AA", "Move Hub", service_uuids=["x"]))
    finally:
        bleak.BleakScanner = original
    assert seen == {"service_uuids": ["x"]}  # passed on, as the macOS filter needs

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

    from hubbit.hub import quiet_pylgbst_logs

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
    hub = _hub_with()
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


def _hub_with(**devices):
    hub = SimpleNamespace(motor_A=object(), motor_B=object(), motor_AB=object(), led=object())
    for name, value in devices.items():
        setattr(hub, name, value)
    return hub


def test_connect_treats_a_hub_without_devices_as_failed(monkeypatch):
    # Kali: MoveHub() returned with all devices None -> 'NoneType' has no 'set_color'
    good = _hub_with()
    connections, scans = _fake_pylgbst(monkeypatch, _hub_with(motor_AB=None, led=None), good)
    assert hub_mod.connect() is good
    assert len(scans) == 2
    assert connections[0].disconnects == 1  # the half-set-up connection is closed


def test_connect_reports_missing_devices_twice(monkeypatch):
    _fake_pylgbst(monkeypatch, _hub_with(led=None), _hub_with(led=None))
    with pytest.raises(hub_mod.HubConnectError, match="led"):
        hub_mod.connect()


def test_connect_gives_up_early_when_the_bluetooth_thread_dies(monkeypatch):
    import threading

    connections, _ = _fake_pylgbst(monkeypatch, "hang", _hub_with())
    monkeypatch.setattr(hub_mod, "CONNECT_TIMEOUT", 10.0)
    real_connection = __import__("pylgbst").get_connection_bleak

    def dying_connection(**kw):
        conn = real_connection(**kw)
        alive = threading.Event()
        alive.set()
        conn.is_alive = alive.is_set
        threading.Timer(0.3, alive.clear).start()  # the BLE thread ends after 0.3 s
        return conn

    monkeypatch.setattr(__import__("pylgbst"), "get_connection_bleak", dying_connection)
    start = time.monotonic()
    hub_mod.connect()  # the retry succeeds
    assert time.monotonic() - start < 3  # not the full CONNECT_TIMEOUT
    assert connections[0].disconnects == 1


def test_retry_asks_for_a_fresh_button_press(monkeypatch, capsys):
    _fake_pylgbst(monkeypatch, RuntimeError("first"), _hub_with())
    hub_mod.connect()
    assert "green button again" in capsys.readouterr().out


def test_linux_errors_point_to_the_reset_steps(monkeypatch):
    monkeypatch.setattr(hub_mod.sys, "platform", "linux")
    _fake_pylgbst(monkeypatch, RuntimeError("first"), RuntimeError("second"))
    with pytest.raises(hub_mod.HubConnectError, match="setup-linux.md"):
        hub_mod.connect()
    monkeypatch.setattr(hub_mod.sys, "platform", "darwin")
    _fake_pylgbst(monkeypatch, RuntimeError("first"), RuntimeError("second"))
    with pytest.raises(hub_mod.HubConnectError) as err:
        hub_mod.connect()
    assert "setup-linux" not in str(err.value)


@pytest.mark.parametrize(
    ("error", "lang", "expected"),
    [
        (hub_mod.HubNotFoundError("Move Hub 00:16:53:XX:XX:XX not seen"), "en", "not found"),
        (hub_mod.HubConnectError("setup failed"), "en", "could not connect"),
        (hub_mod.HubNotFoundError("nothing"), "de", "nicht gefunden"),
    ],
)
def test_robot_hub_missing_is_one_friendly_line(monkeypatch, capsys, error, lang, expected):
    from hubbit import kid

    def connect(*a, **k):
        raise error

    monkeypatch.setattr(kid, "connect", connect)
    robot_cls = kid.Roboter if lang == "de" else kid.Robot
    with pytest.raises(SystemExit) as exit_info, robot_cls():
        raise AssertionError("the mission body must not run without a hub")
    assert exit_info.value.code == 1
    out = capsys.readouterr().out
    assert expected in out.lower()
    assert "Traceback" not in out and str(error) not in out  # no adult details for kids


def test_robot_bluetooth_off_shows_the_hint(monkeypatch, capsys):
    from hubbit import kid
    from hubbit.scan import BluetoothUnavailableError

    def connect(*a, **k):
        raise BluetoothUnavailableError("Bluetooth is switched off or blocked.")

    monkeypatch.setattr(kid, "connect", connect)
    with pytest.raises(SystemExit), kid.Robot():
        pass
    assert "Bluetooth is switched off or blocked." in capsys.readouterr().out


def test_robot_ctrl_c_while_connecting(monkeypatch, capsys):
    from hubbit import kid

    def connect(*a, **k):
        raise KeyboardInterrupt

    monkeypatch.setattr(kid, "connect", connect)
    with pytest.raises(SystemExit), kid.Robot():
        pass
    assert "Ctrl+C" in capsys.readouterr().out


def test_robot_open_still_raises_for_the_console(monkeypatch):
    from hubbit import kid

    def connect(*a, **k):
        raise hub_mod.HubNotFoundError("nothing")

    monkeypatch.setattr(kid, "connect", connect)
    with pytest.raises(hub_mod.HubNotFoundError):
        kid.Robot().open()


def test_resolve_address_speaks_the_robots_language(monkeypatch, capsys):
    monkeypatch.delenv(hub_mod.ENV_ADDRESS, raising=False)
    monkeypatch.setattr(hub_mod, "find_hub", lambda timeout, address=None: None)
    with pytest.raises(hub_mod.HubNotFoundError):
        hub_mod.resolve_address(timeout=0.1, lang="de")
    out = capsys.readouterr().out
    assert "Suche den Move Hub" in out and "Looking" not in out


def test_roboter_connects_in_german(monkeypatch):
    from types import SimpleNamespace

    from hubbit import kid

    seen = {}
    fake = FakeHub()
    fake.led = SimpleNamespace(set_color=lambda color: None)

    def connect(address=None, timeout=15.0, lang="en"):
        seen["lang"] = lang
        return fake

    monkeypatch.setattr(kid, "connect", connect)
    with kid.Roboter():
        pass
    assert seen["lang"] == "de"
