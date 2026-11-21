# Hardware notes

## Move Hub (88006) ports

| Port | pylgbst attribute | Device |
|---|---|---|
| A, B | `hub.motor_A`, `hub.motor_B` | built-in encoded motors |
| A+B | `hub.motor_AB` | both, synchronised (driving) |
| C, D | `hub.port_C`, `hub.port_D`, `hub.motor_external`, `hub.vision_sensor` | external motor / color & distance sensor |
| — | `hub.led` | RGB LED |
| — | `hub.tilt_sensor`, `hub.button`, `hub.voltage`, `hub.current` | built-in |

Speeds are floats −1.0 … 1.0: `timed(seconds, speed_a, speed_b)`, `angled(degrees, speed)`,
`goto_position(degrees)`. LED colors: `pylgbst.peripherals.COLOR_*`.

## Library quirks

- pylgbst pinned to git commit `71dfc63` (2025-01-04, "use BleakScanner instead of
  discover()"). PyPI 1.3.0 (2023) is broken with bleak ≥ 1.0.
- pylgbst's scanning has no timeout → `lego_boost.scan` scans first, with a timeout.
- `hub.disconnect()` waits for a reply that may never come → `safe_shutdown()` uses timeouts.

## Platform log

Record what was verified on real hardware.

| Date | Platform | Python / bleak | Result |
|---|---|---|---|
| | macOS 27, Apple Silicon | 3.12 / 3.1.0 | pending first hardware session |
| | Ubuntu / Kali / Raspberry Pi OS | | pending |
| | Windows | | pending |
