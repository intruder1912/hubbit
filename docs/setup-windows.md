# Setup on Windows 10/11

Status: **verified on hardware** (2026-11-24, see `hardware-notes.md` and #4): setup, launchers,
Thonny, console and TUI work.

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
   git clone https://github.com/intruder1912/hubbit.git
   cd hubbit
   uv sync
   uv run hubbit-scan
   uv run kids/01_hello_light.py
   ```

## Hub address (optional, saves the scan)

`hubbit-scan` prints the hub's address (a MAC like `00:16:53:AB:CD:EF` on Windows).
`uv run hubbit-scan --save` (or double-clicking `windows\scan.cmd`) remembers it in the
project's `.env` file, so every script and launcher uses that hub from then on. Press the
green button before each connection anyway: the hub only connects while it blinks.

Or set it yourself (a variable set like this wins over `.env`):

```powershell
$env:BOOST_HUB_ADDRESS = "00:16:53:AB:CD:EF"     # this PowerShell window only
setx BOOST_HUB_ADDRESS "00:16:53:AB:CD:EF"       # permanently (new windows only)
```

## Double-click launchers (no terminal needed)

The `windows\` folder has one launcher per kids mission plus `scan.cmd`. Double-click one
in Explorer: a window opens, runs the script with the project's Python, and stays open
at the end ("Press any key ...") so the output can be read. Press the hub's green button
**right before** double-clicking (it only advertises for ~10 s).

`console.cmd` starts the typing console (`hubbit-console`): the hub stays connected until
`exit`, so there is no need to press the green button again for every command.
`console-practice.cmd` runs the same console without a hub (`--simulate`).

`tui.cmd` opens the button window (`hubbit-tui`: big buttons, arrow keys, STOP), and
`tui-practice.cmd` runs it without a hub. It looks best in **Windows Terminal** (default on
Windows 11); the old console window works but with plainer colours.

German: `mission-N-de-*.cmd`, `tui-deutsch.cmd` run the German missions in `kids\de\`; `console-deutsch.cmd`
and `console-ueben.cmd` (no hub) start the console with German messages (`--lang de`).
To make German the default everywhere, set the user environment variable `BOOST_LANG=de`.

Tip: drag `windows\mission-1-hello-light.cmd` to the desktop with **Alt** held to create
a shortcut.

## Kid-friendly editor

Both editors must use the project's Python in `.venv` (created by `uv sync`), otherwise
`import hubbit` fails.

**Thonny** ([thonny.org](https://thonny.org/))
1. Tools → Options → Interpreter → "Alternative Python 3 interpreter or virtual environment".
2. Python executable: `<hubbit folder>\.venv\Scripts\python.exe` → OK.
3. Open e.g. `kids\01_hello_light.py`, press the green button on the hub, then **Run (F5)**.
4. To stop a running mission use the red **Stop** button (or Ctrl+C in the shell pane).
   Stop halts the motors and disconnects cleanly (checked on hardware in #4), without a
   traceback.

**VS Code**
1. Install the Python extension, open the `hubbit` folder.
2. Ctrl+Shift+P → "Python: Select Interpreter" → `.venv\Scripts\python.exe`.
3. Open a mission and click ▶ (Run Python File). Stop with Ctrl+C in the terminal.

## Notes

- Text the scripts print is kept ASCII-only (checked by `tests/test_portability.py`), so
  old console code pages can't crash them.
- Ctrl+C in a running script stops the motors and disconnects (checked on hardware in #4).
  Kids missions then print one short line instead of a traceback.
- Disconnecting at the end of a script takes about 5 s on Windows (about 1 s on
  Mac/Linux). That is normal; just wait for "Bye!".
- VS Code was not tried on hardware yet; it uses the same interpreter as Thonny.
