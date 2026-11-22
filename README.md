# lego-boost

Experiments with the **LEGO BOOST Move Hub** (set 17101, hub 88006) from Python — no LEGO
app or tablet needed. Uses [pylgbst](https://github.com/undera/pylgbst) with the
[bleak](https://github.com/hbldh/bleak) Bluetooth LE backend, so the same code runs on
**macOS, Linux (incl. Raspberry Pi) and Windows**.

## Quickstart

1. Install [uv](https://docs.astral.sh/uv/getting-started/installation/)
   - macOS / Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh` (or `brew install uv`)
   - Windows (PowerShell): `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
2. Clone and set up (uv downloads Python 3.12 automatically):
   ```bash
   git clone https://github.com/intruder1912/lego-boost.git
   cd lego-boost
   uv sync
   ```
3. Switch on the hub (green button, LED blinks) and scan:
   ```bash
   uv run boost-scan
   ```
4. Run an experiment:
   ```bash
   uv run experiments/03_led_colors.py
   ```

OS-specific notes (Bluetooth permissions, BlueZ, etc.):
[macOS](docs/setup-macos.md) · [Linux](docs/setup-linux.md) · [Windows](docs/setup-windows.md) ·
[Troubleshooting](docs/troubleshooting.md)

## What's inside

| Folder | Content |
|---|---|
| `experiments/` | Numbered experiments: scan, hub info, LED, motors, sensors |
| `kids/` | Simple "missions" for young programmers using a friendly `Robot` API |
| `src/lego_boost/` | Helpers: scan with timeout, safe connect/disconnect, kid API |
| `docs/` | Setup per OS, hardware notes, troubleshooting, workflow |
| `windows/` | Double-click launchers for the kids missions on Windows |

### Writing your own script

```python
from pylgbst.peripherals import COLOR_GREEN
from lego_boost import boost

with boost() as hub:  # scans, connects, and always stops motors at the end
    hub.led.set_color(COLOR_GREEN)
    hub.motor_AB.timed(1.0, 0.4, 0.4)  # drive forward 1 s at 40 %
```

Kid version:

```python
from lego_boost.kid import Robot

with Robot() as robot:
    robot.light("blue")
    robot.forward(2)
    print(robot.see_color())
```

Set `BOOST_HUB_ADDRESS` (printed by `boost-scan`) to skip scanning.

## Development

```bash
uv run pytest            # unit tests, no hardware needed
uv run ruff check .      # lint
uv run ruff format .     # format
```

Work is organised in [GitHub issues](https://github.com/intruder1912/lego-boost/issues).
See [docs/workflow.md](docs/workflow.md) and [CLAUDE.md](CLAUDE.md).

## License

MIT. LEGO® and BOOST are trademarks of the LEGO Group, which does not sponsor or endorse
this project.
