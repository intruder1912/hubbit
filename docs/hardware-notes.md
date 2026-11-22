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
- **New turn formula on the hub:** `kids/de/03_quadrat_fahren.py` (German, 4 x `vorwaerts(1)`
  + `rechts()` = 0.39 s) closes the square to within 3-5 cm and ~5 deg after four turns
  (so ~89 deg per quarter turn). No 0x46 warning on connect any more. Good enough, no
  further tuning.
- **Scan with `service_uuids`** (what upstream fix undera/pylgbst#142 restores on macOS):
  `BleakScanner(service_uuids=["00001623-1212-efde-1623-785feabcd123"])` found the hub
  ("Move Hub") within 0.5 s. So the fixed pylgbst works on macOS with the filter.

## Mission 4 with LEGO bricks (2026-11-22, Mac, #2)

- `Robot.see_color()` is debounced now: a new colour counts after 0.3 s
  (`COLOR_STABLE_SECONDS`); the first reading counts at once.
- Run 1 (debounce only), bricks red → blue → yellow at 1-2 cm: `RED`, `BLACK`, `YELLOW`.
  Blue was lost to a BLACK reading. No more flicker between bricks.
- Mission 4 (EN + DE) now skips "black" like "nothing" (BLACK mostly means too dark / too
  far). Run 2: `RED`, `BLUE`, `YELLOW`, all three right. Good enough, no further tuning.
  The hub light followed each brick colour, no flicker.
- Mission 5 (remote control, EN + DE) in the user's own terminal: w/a/s/d/q and the
  unknown-letter reply all as expected; tapped turns (0.3 s, ~60 deg) feel fine for steering.

## Kali Linux (2026-11-22, bare-metal laptop, BlueZ, #3)

- Setup per `docs/setup-linux.md`: `bluez` + `systemctl enable --now bluetooth` + `bluetooth`
  group + log out/in were all needed. Then `active`, `Powered: yes`, not blocked.
- `02_hub_info` (all peripherals, 7.42 V / 96 mA), `03_led_colors`, mission 3, console
  (`forward`, `left 90`, `color`, raw `battery`, Ctrl+C mid-drive) and boost-tui driving +
  STOP: all fine. Address saved, `BOOST_TRIM=5` (same robot as on the Mac).
- **Reconnect after switching the hub off:** the first `reconnect` failed in BlueZ
  (`BleakError: failed to discover services, device disconnected`, full traceback from
  pylgbst's thread), the second worked (built-in devices took > 10 s:
  `Got only these devices: (None, ...)`). Now `connect()` retries once by itself and the
  thread error is one log line.
- **boost-tui started right after the console:** the link came up half-open and
  `MoveHub()` waited forever for a reply (no timeout in pylgbst). So `reconnect` was
  silently ignored ("one connect at a time") and Ctrl+Q hung: asyncio waited for the
  stuck textual worker thread. Now: setup limited to 25 s (`CONNECT_TIMEOUT`), connects
  run in daemon threads, `reconnect` during a connect says "Still connecting ...".
- **Stale vision reading:** at TUI start one `VisionSensor` value from before the mode
  switch (1 byte `ff`) was decoded with the 4-byte layout → `AssertionError` traceback in
  the TUI log. Harmless (one reading lost), now dropped quietly by `patch_pylgbst()`.
- **Flaky after many reconnects (retest after the fixes above).** Laptop adapter: Apple
  Broadcom BCM20702B0 (`05ac:8289`, Bluetooth 4.0, ~2012 MacBook); BlueZ 5.87, kernel
  7.2.15. After repeated hub switch-offs and reconnects, connects failed more and more, even
  from a fresh `boost-console` ("failed to discover services", "Service Discovery has not
  been performed yet"). Once `MoveHub()` returned with all devices `None` and `Robot`
  crashed on `led.set_color`. `journalctl -u bluetooth` shows why: 30+ pairs of
  `Device 00:16:53:C2:96:F3 is already connected` / `No matching connection for device`.
  BlueZ kept a stale connection to a hub that was gone. `GAS PPCP: Invalid Connection
  Parameters` lines are harmless. The reset steps in `docs/setup-linux.md` (remove device,
  restart bluetooth, hub batteries out) fixed it: `02_hub_info` and a normal connect worked
  again. Not fixed in code: clearing BlueZ state would need Linux-only D-Bus calls. Now
  `connect()` treats a hub without motors/LED as a failed connect, gives up as soon as
  pylgbst's BLE thread dies, always closes half-set-up connections, asks for a fresh green
  button press before the retry and points Linux users to the reset steps.

## Platform log

Record what was verified on real hardware.

| Date | Platform | Python / bleak | Result |
|---|---|---|---|
| 2026-11-21 | macOS 27.2.1, Apple Silicon | 3.12 / 3.1.0 | ✅ scan, 02 info, 03 LED, 04 motors, 05 vision+tilt (with `patch_pylgbst`); button untested |
| 2026-11-22 | macOS 27.2.1, Apple Silicon | 3.12 / 3.1.0 | ✅ `boost-scan --save` + saved address, session core timing, `boost-tui` (hold-to-drive, sensor panel, tilt) |
| 2026-11-22 | macOS 27.2.1, Apple Silicon | 3.12 / 3.1.0 | ✅ kids missions 1–5 (EN + DE 3, 4, 5), colour debounce with LEGO bricks |
| 2026-11-22 | macOS 27.2.1, Apple Silicon | 3.12 / 3.1.0 | ✅ hw-2: `BOOST_TRIM`, degree turns (recalibrated), raw mode, German console, stop, reconnect |
| 2026-11-22 | Kali Linux (bare metal), BlueZ | 3.12 / 3.1.0 | ✅ setup, 02, 03, mission 3, console, TUI; reconnect needed a retry (fixed), TUI hang after quick restart (fixed); repeated reconnects flaky (stale BlueZ state, old BCM20702 adapter; reset steps in setup-linux.md) |
| | Ubuntu / Raspberry Pi OS | | pending |
| | Windows | | pending |
