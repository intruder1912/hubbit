# lego-boost

[![CI](https://github.com/intruder1912/lego-boost/actions/workflows/ci.yml/badge.svg)](https://github.com/intruder1912/lego-boost/actions/workflows/ci.yml)

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
| `kids/` | Simple "missions" for young programmers using a friendly `Robot` API (German: `kids/de/`) |
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

## Console: drive the robot by typing

```text
$ uv run boost-console            # or: uv run boost-console --simulate  (no hub needed)
robot> forward 2
robot> turn left 90
robot> led red
robot> color
I see: red
robot> raw                        # grown-up commands: motor, angle, sensors, battery, hub
raw> motor A 30 1.5
raw> exit
```

The hub stays connected until `exit` (or Ctrl+C / Ctrl+D). `stop` stops the motors at
once; `help` lists all commands; Tab completes words; Up arrow repeats earlier commands.
If the hub gets lost, the console says so: press the green button and type `reconnect`.
On Windows, double-click `windows\console.cmd` (or `console-practice.cmd` for the simulation).

## Button window: drive with the mouse and arrow keys

```bash
uv run boost-tui                  # or: --simulate (no hub), --lang de (German)
```

A full-screen window on the same session as the console: big buttons for driving and the
light colours, "What color?" / "How far?", a live sensor panel (colour swatch, distance
bar, tilt, battery), a log, and a command line at the bottom that
takes every console command (also `raw`). Arrow keys drive in short steps: hold a key to
keep going, let go and the robot stops within ~0.3 s. Space, Escape or the STOP button stop
at once; Ctrl+Q closes the window (and stops the motors). On Windows: `windows\tui.cmd`,
`tui-practice.cmd` (simulation), `tui-deutsch.cmd`. It looks best in Windows Terminal.

## Auf Deutsch

German words always work in the console, with or without umlauts (`vor 2`, `zurück`,
`dreh links 45`, `licht rot`, `grün`, `farbe`, `stopp`, `hilfe`, `ende`; raw: `winkel`,
`sensoren`, `batterie`). For German messages and help start it with `--lang de` (or set
`BOOST_LANG=de`), or type `sprache deutsch` inside (`language english` switches back).

```text
$ uv run boost-console --lang de
roboter> vor 2
roboter> farbe
Ich sehe: gruen
```

Die Missionen gibt es auch auf Deutsch in `kids/de/`, mit dem deutschen `Roboter`:

```python
from lego_boost.kid import Roboter

with Roboter() as roboter:
    roboter.licht("blau")  # rot, gruen, gelb, lila, weiss, aus, ...
    roboter.vorwaerts(2)  # auch: rueckwaerts(), links(), rechts(), warte(1)
    print(roboter.farbe())  # z.B. "gruen" (auch: abstand(), batterie())
```

Windows: `windows\mission-1-de-hallo-licht.cmd` ... `mission-5-de-fernsteuerung.cmd`,
`console-deutsch.cmd` und `console-ueben.cmd` (ohne Roboter). Printed German text uses
ae/oe/ue/ss instead of umlauts, so it works in every Windows console.

## Development

```bash
uv run pytest            # unit tests, no hardware needed
uv run ruff check .      # lint
uv run ruff format .     # format
```

Work is organised in [GitHub issues](https://github.com/intruder1912/lego-boost/issues);
questions and ideas go to [Discussions](https://github.com/intruder1912/lego-boost/discussions).
Want to help? Read [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md).
Security problems: see [SECURITY.md](SECURITY.md).
More: [docs/workflow.md](docs/workflow.md), [docs/triage.md](docs/triage.md), [CLAUDE.md](CLAUDE.md).

## Acknowledgements

This project stands on the work of others:

- [pylgbst](https://github.com/undera/pylgbst) by Andrey Pokhilko and contributors (MIT): the
  Python library that talks to the Move Hub. `lego_boost.hub.patch_pylgbst()` works around two
  bugs in the pinned commit; see [docs/hardware-notes.md](docs/hardware-notes.md).
- [bleak](https://github.com/hbldh/bleak) by Henrik Blidh and contributors (MIT): cross-platform
  Bluetooth LE.
- [prompt_toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) by Jonathan Slenders
  and contributors (BSD-3-Clause): the interactive `boost-console` prompt.
- [Textual](https://github.com/Textualize/textual) by Textualize and contributors (MIT): the
  full-screen `boost-tui` window.
- [BOOSTreveng](https://github.com/JorgePe/BOOSTreveng) by Jorge Pereira (MIT) and LEGO's
  [wireless protocol documentation](https://github.com/LEGO/lego-ble-wireless-protocol-docs):
  protocol references.
- The [Contributor Covenant](https://www.contributor-covenant.org) (CC BY 4.0): our Code of Conduct.

## License

MIT. LEGO® and BOOST are trademarks of the LEGO Group, which does not sponsor or endorse
this project.
