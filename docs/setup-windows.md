# Setup on Windows 10/11

Status: **not yet verified on hardware** — see the Windows validation issue.

bleak uses the built-in Windows Bluetooth stack (WinRT). Any Bluetooth 4.0+ adapter
recognised by Windows works; no extra dongle needed.

1. Bluetooth on (Settings → Bluetooth & devices). **Do not pair** the hub in Windows —
   bleak connects directly.
2. Install uv in PowerShell, then reopen PowerShell:
   ```powershell
   powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```
3. Install Git (`winget install Git.Git`), then:
   ```powershell
   git clone https://github.com/intruder1912/lego-boost.git
   cd lego-boost
   uv sync
   uv run boost-scan
   uv run kids/01_hello_light.py
   ```

Optional hub address: `$env:BOOST_HUB_ADDRESS = "00:16:53:XX:XX:XX"`

## Kid-friendly editor

[Thonny](https://thonny.org/) or VS Code. In VS Code select the interpreter
`.venv\Scripts\python.exe` so the ▶ button runs scripts with the right packages.
