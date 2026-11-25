"""The old name `lego_boost` still works for the 0.2 releases (#47), with a warning."""

import importlib
import sys
from pathlib import Path

import pytest

tomllib = pytest.importorskip("tomllib")  # Python 3.11+
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def fresh_shim():
    for name in [n for n in sys.modules if n == "lego_boost" or n.startswith("lego_boost.")]:
        del sys.modules[name]
    yield
    for name in [n for n in sys.modules if n == "lego_boost" or n.startswith("lego_boost.")]:
        del sys.modules[name]


def test_old_import_warns_and_reexports(fresh_shim):
    import hubbit

    with pytest.warns(DeprecationWarning, match="hubbit"):
        old = importlib.import_module("lego_boost")
    assert old.boost is hubbit.boost
    assert old.__all__ == hubbit.__all__


def test_old_submodule_is_the_same_module(fresh_shim):
    import hubbit.kid

    with pytest.warns(DeprecationWarning):
        from lego_boost.kid import Robot
    assert Robot is hubbit.kid.Robot
    assert sys.modules["lego_boost.kid"] is hubbit.kid


def test_old_commands_still_point_at_hubbit():
    scripts = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["scripts"]
    for tool in ("scan", "console", "tui"):
        assert scripts[f"hubbit-{tool}"] == f"hubbit.{tool}:main"
        assert scripts[f"boost-{tool}"] == scripts[f"hubbit-{tool}"]
