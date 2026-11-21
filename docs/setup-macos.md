# Setup on macOS

Tested: macOS 27 (Apple Silicon). Should work on macOS 12+.

1. `brew install uv` (or the curl installer from the README).
2. `uv sync` in the repo — downloads Python 3.12 and creates `.venv/`.
3. **Bluetooth permission:** the first BLE scan triggers a macOS prompt for the app running
   Python (Terminal, iTerm, VS Code, …). Allow it. If you missed it:
   System Settings → Privacy & Security → Bluetooth → enable your terminal/IDE.
   Without it, scans silently find nothing or the process aborts.
4. Switch on the hub, run `uv run boost-scan`.

## Addresses on macOS

CoreBluetooth hides MAC addresses. `boost-scan` prints a **UUID** that is stable on
*this* Mac only. Use it as `BOOST_HUB_ADDRESS` here, but not on other machines.

```bash
export BOOST_HUB_ADDRESS=<uuid-from-boost-scan>
```
