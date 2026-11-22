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
- **One pending request at a time:** `hub.send()` asserts there is no outstanding sync
  request. Two threads sending commands (e.g. `motor.stop()` from the UI thread while another
  thread waits in `timed()`) raise `AssertionError`. `lego_boost.session` therefore sends
  everything from one worker thread and starts moves with `wait_complete=False`.
- **Lost link detection:** `BleakConnection.is_alive()` is a no-op; use
  `hub.connection.is_alive()` (the `BleakDriver`, checks pylgbst's two threads). It only turns
  False after a write fails, so the session also uses a per-command watchdog.
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

- `Robot` drive speed 35% (50% felt too fast for young drivers); ~35 cm per `forward(1)`.
- Turn on the spot at 50%: 0.35 s ≈ 79°, 0.5 s ≈ 130° (not linear, motors ramp up).
  `QUARTER_TURN_SECONDS = 0.38` → mission 3 drives a closed square. Re-check on carpet
  or with weak batteries. (Replaced 2026-11-22 by a start-up + rate model, see below.)
- Each motor call adds ~0.28 s of BLE round trip (`forward(1)` takes ~1.29 s).
- Colour sensor with non-LEGO items (green, red, neon orange): red ✓, green seen as
  BLUE/CYAN, orange likely as RED; BLACK appears between items. Retest with LEGO bricks.

## Console / TUI session (2026-11-22, Mac, Vernie, hard floor)

- `boost-scan --save` found the hub as **"Move Hub"** (not "LEGO Move Hub"; matched by the
  service UUID) and wrote the address to `.env`; `02_hub_info` then connected through it.
  Battery 7.8 V ("100%"), 95 mA idle. `disconnect did not finish within 3.0s` at the end
  (our timeout caught it; shutdown fine).
- Session core (#13): `led` round trip 0.17 s; `stop` mid-move until "Stopped." 0.23 /
  0.55 / 0.25 s; `left 90` / `right 90` incl. round trip 0.62 / 0.67 s; 30 s with sensor
  polling every 0.5 s, stayed connected.
- Tilt (3-axis simple): **`up` = resting upright**; tipping changes it as expected.
- Colours: unreliable apart from red; other bricks often read BLACK (3-5 cm, unsteady hand,
  dim yellowish light). Distance looks plausible (10 = nothing, smaller = closer).
  Deliberately **not** calibrated further for now: good enough to experiment.
- `boost-tui` arrow keys: the first version (0.3 s steps) drove jerkily and a held arrow
  restarted driving right after STOP. Now hold-to-drive (`Session.hold`): smooth while held,
  stops ~0.3 s after release, STOP waits until the key is let go; a tapped turn is one
  0.12 s pulse (small angle), holding turns continuously. Confirmed on the hub.
- Drift: the **left motor is slightly faster** than the right, forwards and backwards, so
  straight driving curves a little. Fixed by `BOOST_TRIM` (#31), see hw-2 below.

## Console session hw-2 (2026-11-22, Mac, Vernie, hard floor, #13)

- **Trim:** `BOOST_TRIM=5` (left wheel 5% slower) → `forward 3` (~1 m) drifts about 2 cm or
  less. Kept in the Mac's `.env`.
- **Degree turns** (with trim 5, by eye): `left 90` ≈ 85°, `right 45` ≈ 30°, `left 180` ≈ 205°
  with the old linear formula (0.38 s per 90°). Together with the 2026-11-21 points the
  motors need ~0.1 s to get going, then turn ~310°/s: `turn_seconds = 0.1 + deg / 310`
  (all five points within ~6°). Now `left 90` = 0.39 s, `right 45` = 0.25 s, `left 180` = 0.68 s.
  Not yet re-measured with the new formula.
- **Raw mode:** `battery` 7.38 V, `sensors` → `color=nothing distance=10.0 battery=7.37 V`;
  `hub` lists motors on 0x00/0x01/0x02 (A, B, external), AB on 0x10, vision sensor 0x03,
  LED 0x32, tilt 0x3a, current 0x3b, voltage 0x3c and an internal device on 0x46 (type 0x42,
  pylgbst has no class; its connect-time warning is now filtered). `angle A 360 30` ran.
  Two commands on one line (`motor A 30 1, motor B 30 1`) are rejected with a hint.
- **German console:** `sprache deutsch`, `vor`, `zurueck`, `links 90`, `farbe` (nichts / rot),
  `hilfe` all fine; the typo `zuruech` got "Meinst du 'zurueck'?".
- **`stop`** stops at once.
- **Reconnect:** hub switched off → "Lost the hub. Press the green button, then type
  'reconnect'"; `reconnect` after a green-button press → "Connected again!". It printed a
  stray "Robot stopped. Bye!" (now gone) and the 0x46 warning (now filtered).

## Platform log

Record what was verified on real hardware.

| Date | Platform | Python / bleak | Result |
|---|---|---|---|
| 2026-11-21 | macOS 27.2.1, Apple Silicon | 3.12 / 3.1.0 | ✅ scan, 02 info, 03 LED, 04 motors, 05 vision+tilt (with `patch_pylgbst`); button untested |
| 2026-11-22 | macOS 27.2.1, Apple Silicon | 3.12 / 3.1.0 | ✅ `boost-scan --save` + saved address, session core timing, `boost-tui` (hold-to-drive, sensor panel, tilt) |
| 2026-11-22 | macOS 27.2.1, Apple Silicon | 3.12 / 3.1.0 | ✅ hw-2: `BOOST_TRIM`, degree turns (recalibrated), raw mode, German console, stop, reconnect |
| | Ubuntu / Kali / Raspberry Pi OS | | pending |
| | Windows | | pending |
