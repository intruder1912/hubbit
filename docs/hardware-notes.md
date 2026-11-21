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
- **macOS bug at `71dfc63`:** `_bleak_thread` passes `service_uuids=` to `find_device()`, which
  takes no kwargs → comms thread dies, every connect fails with "communication threads not
  functioning". Fixed by `lego_boost.hub.patch_pylgbst()` (drops the kwarg).
- **`MsgHubAction.is_reply` raises `TypeError`** on any other message instead of returning False;
  a sensor value arriving during `hub.disconnect()` kills the processing thread. Same patch.
- Tilt sensor default mode (`MODE_3AXIS_SIMPLE`) only reports when the face pointing up changes
  (values 0–5 = BACK, UP, DOWN, LEFT, RIGHT, FRONT); small tilts are silent.

## Hub behaviour

- After pressing the green button the hub advertises for only **~10 s** — start the script
  right away, one script per button press. Set `BOOST_HUB_ADDRESS` to skip our pre-scan.
- macOS: CoreBluetooth reports "Bluetooth is unsupported" inside Claude Code's Bash sandbox;
  hardware scripts must run outside it.
- Open: the hub dropped the connection once mid-run while being tilted hard onto its sides
  (2026-11-21, experiment 05). Suspected battery contact bounce, unconfirmed. The button
  subscription is still untested (no press happened while connected).

## Kids track calibration (2026-11-21, Mac session, hard floor)

- `Robot` drive speed 35% (50% felt too fast for a child); ~35 cm per `forward(1)`.
- Turn on the spot at 50%: 0.35 s ≈ 79°, 0.5 s ≈ 130° (not linear, motors ramp up).
  `QUARTER_TURN_SECONDS = 0.38` → mission 3 drives a closed square. Re-check on carpet
  or with weak batteries.
- Each motor call adds ~0.28 s of BLE round trip (`forward(1)` takes ~1.29 s).
- Colour sensor with non-LEGO items (green, red, neon orange): red ✓, green seen as
  BLUE/CYAN, orange likely as RED; BLACK appears between items. Retest with LEGO bricks.

## Platform log

Record what was verified on real hardware.

| Date | Platform | Python / bleak | Result |
|---|---|---|---|
| 2026-11-21 | macOS 27.2.1, Apple Silicon | 3.12 / 3.1.0 | ✅ scan, 02 info, 03 LED, 04 motors, 05 vision+tilt (with `patch_pylgbst`); button untested |
| | Ubuntu / Kali / Raspberry Pi OS | | pending |
| | Windows | | pending |
