# Troubleshooting

| Symptom | Things to check |
|---|---|
| `boost-scan` finds nothing | Hub on? Press green button — LED must **blink** (hub switches off after a few minutes idle). Batteries ok? Only one program may connect: close the LEGO app and other scripts. |
| macOS: nothing found / abort | Bluetooth permission for terminal/IDE (see [setup-macos](setup-macos.md)). |
| Linux: `Unit dbus-org.bluez.service not found` | The Bluetooth service is not installed/enabled (Kali: disabled by default): `sudo apt install bluez && sudo systemctl enable --now bluetooth` ([setup-linux](setup-linux.md), #25). |
| Linux: `org.bluez.Error.NotReady` / no adapter | `bluetoothctl power on`, `rfkill unblock bluetooth`, service running, user in `bluetooth` group. |
| Script hangs after "Connecting" | Hub dropped the connection (idle or low battery). Ctrl+C, press green button, retry. |
| Hub paired in OS settings | Forget it there; bleak connects without pairing. |
| Motors keep running after a crash | Shouldn't happen with `boost()`/`Robot()`; press the green button to switch the hub off. |
| `module 'bleak' has no attribute 'discover'` | pylgbst came from PyPI. Run `uv sync` (uses the pinned git commit). |

Debug logging: `import logging; logging.basicConfig(level=logging.DEBUG)`
