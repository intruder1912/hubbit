import time
from types import SimpleNamespace

import pytest

from lego_boost import hub as hub_mod


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
    assert hub_mod.resolve_address("EXPLICIT") == "EXPLICIT"
    assert hub_mod.resolve_address() == "FROM-ENV"


def test_resolve_address_raises_when_nothing_found(monkeypatch):
    monkeypatch.delenv(hub_mod.ENV_ADDRESS, raising=False)
    monkeypatch.setattr(hub_mod, "find_hub", lambda timeout: None)
    with pytest.raises(hub_mod.HubNotFoundError):
        hub_mod.resolve_address(timeout=0.1)


def test_boost_stops_motors_even_on_error(monkeypatch):
    fake = FakeHub()
    monkeypatch.setattr(hub_mod, "connect", lambda *a, **k: fake)
    with pytest.raises(ValueError), hub_mod.boost():
        raise ValueError("boom")
    assert fake.motor_AB.stopped and fake.motor_A.stopped and fake.motor_B.stopped
    assert fake.connection.closed


def test_safe_shutdown_does_not_hang(monkeypatch):
    fake = FakeHub(hang_on_disconnect=True)
    start = time.monotonic()
    hub_mod.safe_shutdown(fake, timeout=0.2)
    assert time.monotonic() - start < 2
    assert fake.connection.closed
