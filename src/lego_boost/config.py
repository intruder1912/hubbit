"""Per-machine settings in a `.env` file in the project folder (no extra dependency).

    BOOST_HUB_ADDRESS=00:16:53:AB:CD:EF    # written by `boost-scan --save`
    BOOST_LANG=de

`load_env()` copies the values into `os.environ` unless a variable is already set there,
so a variable set in the shell always wins. See `.env.example` for the keys.
`LEGO_BOOST_ENV_FILE` points to another file (tests use it to ignore the real `.env`).
"""

from __future__ import annotations

import os
from pathlib import Path

ENV_NAME = ".env"
ENV_OVERRIDE = "LEGO_BOOST_ENV_FILE"
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # src/lego_boost/config.py -> repo


def env_path() -> Path:
    """The `.env` to use: $LEGO_BOOST_ENV_FILE, else the current folder's, else the project's."""
    override = os.environ.get(ENV_OVERRIDE)
    if override:
        return Path(override)
    here = Path.cwd() / ENV_NAME
    if here.is_file() or not (PROJECT_ROOT / "pyproject.toml").is_file():
        return here
    return PROJECT_ROOT / ENV_NAME


def _parse_line(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None
    key, value = line.split("=", 1)
    key = key.strip().removeprefix("export ").strip()
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
        value = value[1:-1]
    elif " #" in value:
        value = value.split(" #", 1)[0].rstrip()
    return (key, value) if key else None


def read_env(path: Path | None = None) -> dict[str, str]:
    """KEY=VALUE pairs from a .env file ({} if there is none)."""
    path = path or env_path()
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    pairs = (_parse_line(line) for line in text.splitlines())
    return dict(pair for pair in pairs if pair)


def load_env(path: Path | None = None) -> dict[str, str]:
    """Put the .env values into os.environ (variables already set win). Returns what was set."""
    applied = {}
    for key, value in read_env(path).items():
        if key not in os.environ:
            os.environ[key] = value
            applied[key] = value
    return applied


def save_value(key: str, value: str, path: Path | None = None) -> Path:
    """Set KEY=value in the .env file: replace the existing line, else append. Keeps comments."""
    path = path or env_path()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        lines = []
    new = f"{key}={value}"
    for i, line in enumerate(lines):
        parsed = _parse_line(line)
        if parsed and parsed[0] == key:
            lines[i] = new
            break
    else:
        lines.append(new)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
