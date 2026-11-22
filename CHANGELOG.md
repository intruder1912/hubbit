# Changelog

All notable changes to this project. Versions follow [Semantic Versioning](https://semver.org/)
(0.x: anything may still change). From 0.1.0 on, entries are generated from
[Conventional Commits](https://www.conventionalcommits.org/) with git-cliff
(see `docs/releasing.md`).

## [0.1.0] - 2026-11-22

First release. Verified on real hardware on macOS (Apple Silicon) and Kali Linux; Windows
(the kids notebook) is prepared and CI-tested, but not yet checked on hardware (#4).

### Features
- `lego_boost` helper package around pylgbst: `boost()` / `connect()` with timeouts, one
  retry and clean shutdown; own BLE scan with timeout; `boost-scan --save` remembers the hub
  address in `.env`.
- Kids track: `Robot` (English) and `Roboter` (German) with colours by name, speeds in %,
  degree turns, debounced colour sensor, per-robot motor trim `BOOST_TRIM`; missions 1-5 in
  both languages with Windows double-click launchers.
- `boost-console`: interactive text commands (simple and raw mode, English and German, help,
  `stop`, watchdog, reconnect).
- `boost-tui`: full-screen button window with hold-to-drive arrow keys, tapped small turns,
  live sensor panel and command line.
- `--simulate` for console and TUI: no hub needed.
- Experiments 01-05 (scan, hub info, LED, motors, sensors).

### Fixes and workarounds
- Runtime patches for pylgbst bugs (failed-connect traceback, stale vision readings); the
  macOS and disconnect bugs were fixed upstream (undera/pylgbst#142, #144) and are pinned.
- BlueZ: connect timeout, retry, missing-devices check; reset steps in `docs/setup-linux.md`.

### Docs and infrastructure
- Setup guides for macOS, Linux and Windows, hardware notes, troubleshooting, triage.
- CI on macOS, Ubuntu and Windows; SHA-pinned actions; Dependabot; CodeQL.
