# Setup on macOS

Tested: macOS 27 (Apple Silicon). Should work on macOS 12+.

1. `brew install uv` (or the curl installer from the README).
2. `uv sync` in the repo — downloads Python 3.12 and creates `.venv/`.
3. **Bluetooth permission:** the first BLE scan triggers a macOS prompt for the app running
   Python (Terminal, iTerm, VS Code, …). Allow it. If you missed it:
   System Settings → Privacy & Security → Bluetooth → enable your terminal/IDE.
   Without it, scans silently find nothing or the process aborts.
4. Switch on the hub, run `uv run hubbit-scan`.

## Addresses on macOS

CoreBluetooth hides MAC addresses. `hubbit-scan` prints a **UUID** that is stable on
*this* Mac only. Use it as `BOOST_HUB_ADDRESS` here, but not on other machines.
`.env` is not committed, so saving it there is safe:

```bash
uv run hubbit-scan --save                     # writes BOOST_HUB_ADDRESS into .env
export BOOST_HUB_ADDRESS=<uuid-from-hubbit-scan>   # or: this shell only (wins over .env)
```
