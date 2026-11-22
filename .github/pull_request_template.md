## What and why

<!-- Short description. Reference the issue: Closes #NN -->

## How it was tested

- [ ] `uv run ruff check . && uv run ruff format --check . && uv run pytest`
- [ ] On real hardware (hub model, OS):
- [ ] Not hardware-related / not tested on hardware

## Checklist

- [ ] Scripts that touch the hub use `with boost()` / `with Robot()`; speeds ≤ 50 % by default
- [ ] Docs updated (README, `docs/`), if behaviour or setup changed
