"""Per-machine settings file (#28). Files are named *.cfg here: the sandbox hides .env*."""

import importlib
import os

import pytest

from hubbit import config
from hubbit import hub as hub_mod
from hubbit.scan import FoundHub

scan_mod = importlib.import_module("hubbit.scan")  # the package exports a scan()


@pytest.fixture
def env_file(tmp_path, monkeypatch):
    path = tmp_path / "settings.cfg"
    monkeypatch.setenv(config.ENV_OVERRIDE, str(path))
    monkeypatch.delenv("BOOST_HUB_ADDRESS", raising=False)
    monkeypatch.delenv("BOOST_LANG", raising=False)
    return path


def test_read_env_parses_comments_quotes_and_export(env_file):
    env_file.write_text(
        "# comment\n\nBOOST_HUB_ADDRESS = 'AA:BB'\nexport BOOST_LANG=de  # German\nbroken line\n",
        encoding="utf-8",
    )
    assert config.read_env() == {"BOOST_HUB_ADDRESS": "AA:BB", "BOOST_LANG": "de"}


def test_shell_variables_win_over_the_file(env_file, monkeypatch):
    env_file.write_text("BOOST_HUB_ADDRESS=FROM-FILE\nBOOST_LANG=de\n", encoding="utf-8")
    monkeypatch.setenv("BOOST_HUB_ADDRESS", "FROM-SHELL")
    assert config.load_env() == {"BOOST_LANG": "de"}
    assert os.environ["BOOST_HUB_ADDRESS"] == "FROM-SHELL"
    assert os.environ["BOOST_LANG"] == "de"


def test_missing_file_is_fine(env_file):
    assert config.read_env() == {}
    assert config.load_env() == {}


def test_save_value_replaces_or_appends_and_keeps_comments(env_file):
    env_file.write_text("# my hub\nBOOST_HUB_ADDRESS=OLD\nBOOST_LANG=de\n", encoding="utf-8")
    config.save_value("BOOST_HUB_ADDRESS", "NEW")
    assert (
        env_file.read_text(encoding="utf-8") == "# my hub\nBOOST_HUB_ADDRESS=NEW\nBOOST_LANG=de\n"
    )
    config.save_value("OTHER", "1")
    assert env_file.read_text(encoding="utf-8").endswith("OTHER=1\n")


def test_default_lang_comes_from_the_file(env_file):
    from hubbit.i18n import default_lang

    env_file.write_text("BOOST_LANG=de\n", encoding="utf-8")
    assert default_lang() == "de"


def test_boost_scan_save_writes_the_address(env_file, monkeypatch, capsys):
    hub = FoundHub("LEGO Move Hub", "00:16:53:AB:CD:EF", -50)
    monkeypatch.setattr(scan_mod, "scan", lambda timeout: [hub])
    assert scan_mod.main(["--save"]) == 0
    assert config.read_env() == {"BOOST_HUB_ADDRESS": "00:16:53:AB:CD:EF"}
    assert "Saved BOOST_HUB_ADDRESS" in capsys.readouterr().out


def test_boost_scan_save_refuses_several_hubs(env_file, monkeypatch, capsys):
    hubs = [FoundHub("LEGO Move Hub", f"00:00:00:00:00:0{i}", -50) for i in (1, 2)]
    monkeypatch.setattr(scan_mod, "scan", lambda timeout: hubs)
    assert scan_mod.main(["--save"]) == 1
    assert not env_file.exists()
    assert "Several hubs" in capsys.readouterr().out


def test_without_save_it_only_gives_a_tip(env_file, monkeypatch, capsys):
    hub = FoundHub("LEGO Move Hub", "00:16:53:AB:CD:EF", -50)
    monkeypatch.setattr(scan_mod, "scan", lambda timeout: [hub])
    assert scan_mod.main([]) == 0
    assert not env_file.exists()
    assert "hubbit-scan --save" in capsys.readouterr().out


def test_saved_address_is_waited_for_with_a_timeout(env_file, monkeypatch):
    """A switched-off hub with a known address must not hang forever (pylgbst would)."""
    env_file.write_text("BOOST_HUB_ADDRESS=aa:bb:cc:dd:ee:ff\n", encoding="utf-8")
    calls = []

    def find_hub(timeout, address=None):
        calls.append((timeout, address))
        return None

    monkeypatch.setattr(hub_mod, "find_hub", find_hub)
    with pytest.raises(hub_mod.HubNotFoundError) as err:
        hub_mod.resolve_address(timeout=0.1)
    assert calls == [(0.1, "aa:bb:cc:dd:ee:ff")]
    assert "hubbit-scan --save" in str(err.value)

    found = FoundHub("LEGO Move Hub", "AA:BB:CC:DD:EE:FF", -40)
    monkeypatch.setattr(hub_mod, "find_hub", lambda timeout, address=None: found)
    assert hub_mod.resolve_address(timeout=0.1) == "AA:BB:CC:DD:EE:FF"
