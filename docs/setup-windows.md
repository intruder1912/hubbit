# Setup on Windows 10/11

Status: **not yet verified on hardware**. See the Windows validation issue (#4).

bleak uses the built-in Windows Bluetooth stack (WinRT). Any Bluetooth 4.0+ adapter
recognised by Windows works; no extra dongle needed.

## Install

1. Bluetooth on (Settings → Bluetooth & devices). **Do not pair** the hub in Windows —
   bleak connects directly. If it was paired before, remove it there.
2. Install uv in PowerShell:
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
   Close and reopen PowerShell. For the double-click launchers below, **sign out of Windows
   and back in once** so Explorer sees the new `PATH`.
3. Install Git (`winget install Git.Git`), then:
   ```powershell
   git clone https://github.com/intruder1912/lego-boost.git
   cd lego-boost
   uv sync
   uv run boost-scan
   uv run kids/01_hello_light.py
   ```

## Hub address (optional, saves the scan)

`boost-scan` prints the hub's address (a MAC like `00:16:53:AB:CD:EF` on Windows).

```powershell
$env:BOOST_HUB_ADDRESS = "00:16:53:AB:CD:EF"     # this PowerShell window only
setx BOOST_HUB_ADDRESS "00:16:53:AB:CD:EF"       # permanently (new windows only)
```

## Double-click launchers (no terminal needed)

The `windows\` folder has one launcher per kids mission plus `scan.cmd`. Double-click one
in Explorer: a window opens, runs the script with the project's Python, and stays open
at the end ("Press any key ...") so the output can be read. Press the hub's green button
**right before** double-clicking (it only advertises for ~10 s).

Tip: drag `windows\mission-1-hello-light.cmd` to the desktop with **Alt** held to create
a shortcut.

## Kid-friendly editor

Both editors must use the project's Python in `.venv` (created by `uv sync`), otherwise
`import lego_boost` fails.

**Thonny** ([thonny.org](https://thonny.org/))
1. Tools → Options → Interpreter → "Alternative Python 3 interpreter or virtual environment".
2. Python executable: `<lego-boost folder>\.venv\Scripts\python.exe` → OK.
3. Open e.g. `kids\01_hello_light.py`, press the green button on the hub, then **Run (F5)**.
4. To stop a running mission use the red **Stop** button (or Ctrl+C in the shell pane).
   Whether Stop always halts the motors cleanly is still to be checked in #4. Every motor
   command ends by itself after its time anyway.

**VS Code**
1. Install the Python extension, open the `lego-boost` folder.
2. Ctrl+Shift+P → "Python: Select Interpreter" → `.venv\Scripts\python.exe`.
3. Open a mission and click ▶ (Run Python File). Stop with Ctrl+C in the terminal.

## Notes

- Text the scripts print is kept ASCII-only (checked by `tests/test_portability.py`), so
  old console code pages can't crash them.
- Ctrl+C in a running script stops the motors and disconnects (tested with a fake hub in
  CI on Windows; real-hardware check in #4).
