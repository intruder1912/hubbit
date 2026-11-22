"""Cross-platform checks that need no hardware (run on macOS, Ubuntu and Windows in CI)."""

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
PY_DIRS = ("src", "kids", "experiments")


def _python_files():
    for folder in PY_DIRS:
        yield from sorted((ROOT / folder).rglob("*.py"))


def _non_ascii_strings(path: Path):
    """String literals with non-ASCII characters (comments may use any UTF-8)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if not node.value.isascii():
                yield node.lineno, node.value


@pytest.mark.parametrize("path", list(_python_files()), ids=lambda p: str(p.relative_to(ROOT)))
def test_printed_text_is_ascii(path):
    """Windows consoles and redirected output may use a legacy code page (cp1252/cp850);
    non-ASCII text in prints can raise UnicodeEncodeError there."""
    bad = list(_non_ascii_strings(path))
    assert not bad, f"non-ASCII string literals at lines {[line for line, _ in bad]}"


def test_launcher_scripts_use_crlf():
    """cmd.exe misparses labels/goto in batch files with LF line endings."""
    gitattributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "*.cmd text eol=crlf" in gitattributes
    assert sorted((ROOT / "windows").glob("*.cmd")), "no launchers in windows/"
