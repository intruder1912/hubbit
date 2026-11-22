import importlib

from lego_boost.scan import MOVE_HUB_NAME, MOVE_HUB_SERVICE_UUID, is_move_hub


def test_matches_by_service_uuid():
    assert is_move_hub(None, [MOVE_HUB_SERVICE_UUID.upper()])


def test_matches_by_name():
    assert is_move_hub(MOVE_HUB_NAME, [])


def test_ignores_other_devices():
    assert not is_move_hub("AirPods", ["0000180f-0000-1000-8000-00805f9b34fb"])
    assert not is_move_hub(None, None)


def test_bluez_not_running_gives_a_hint_instead_of_a_traceback(monkeypatch, capsys):
    """Issue #25: Kali without the bluetooth service."""
    from bleak.exc import BleakDBusError

    scan_mod = importlib.import_module("lego_boost.scan")  # the package exports a scan()

    async def broken(timeout, first_only=False):
        raise BleakDBusError(
            "org.freedesktop.systemd1.NoSuchUnit", ["Unit dbus-org.bluez.service not found."]
        )

    monkeypatch.setattr(scan_mod, "scan_async", broken)
    assert scan_mod.main(["--timeout", "0.1"]) == 2
    out = capsys.readouterr().out
    assert "BlueZ" in out and "systemctl enable --now bluetooth" in out
    assert "Traceback" not in out


def test_bluetooth_hints():
    from lego_boost.scan import bluetooth_hint

    assert "switched off" in bluetooth_hint(RuntimeError("[org.bluez.Error.NotReady] Resource"))
    assert "troubleshooting" in bluetooth_hint(RuntimeError("something else"))
