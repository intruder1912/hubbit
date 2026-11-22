import os

import pytest

_KEYS = ("BOOST_HUB_ADDRESS", "BOOST_LANG")


@pytest.fixture(autouse=True)
def _no_real_env_file(monkeypatch, tmp_path):
    """Tests must not read the developer's .env (hub address, BOOST_LANG=de, ...), and values
    a test loads from a .env file (`load_env` writes os.environ) must not leak into others."""
    monkeypatch.setenv("LEGO_BOOST_ENV_FILE", str(tmp_path / "no-such-file"))
    before = {key: os.environ.get(key) for key in _KEYS}
    yield
    for key, value in before.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value
