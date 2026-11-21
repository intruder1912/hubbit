from lego_boost.scan import MOVE_HUB_NAME, MOVE_HUB_SERVICE_UUID, is_move_hub


def test_matches_by_service_uuid():
    assert is_move_hub(None, [MOVE_HUB_SERVICE_UUID.upper()])


def test_matches_by_name():
    assert is_move_hub(MOVE_HUB_NAME, [])


def test_ignores_other_devices():
    assert not is_move_hub("AirPods", ["0000180f-0000-1000-8000-00805f9b34fb"])
    assert not is_move_hub(None, None)
