"""A long-running robot session for the interactive console (and later the TUI).

    session = Session(connect_robot)      # connect_robot() -> a connected kid.Robot
    session.open()
    while session.handle(input("robot> ")):
        pass
    session.close()

Rules (see docs/superpowers/specs/2026-11-22-console-and-windows-design.md):

- One connection for the whole session; it is closed only by `close()` (`exit`, Ctrl+C).
- Commands run one at a time on a worker thread. **Only the worker talks to the hub**:
  pylgbst allows just one pending request, so `stop()` never sends anything itself. It
  drops queued commands, wakes the worker and lets the worker stop the motors.
- Moves are started without waiting (`wait_complete=False`) and then waited for in small
  steps, so `stop` interrupts them within ~0.1 s plus one BLE round trip.
- If the hub stops answering (a command takes much longer than it should) or pylgbst's
  link dies, the session becomes "disconnected": only `reconnect` and `exit` still work.
  A worker stuck inside pylgbst is abandoned (daemon thread) and a new one is started.

SAFETY: drives motors; speeds are clamped by `lego_boost.commands` (moves <= 10 s).
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from collections.abc import Callable

from lego_boost import kid
from lego_boost.commands import BY_NAME, RAW, SIMPLE, Command, ParseError, help_text, parse
from lego_boost.i18n import EN, color_word, lang_from_word, t

log = logging.getLogger(__name__)

CONNECTED = "connected"
DISCONNECTED = "disconnected"
CLOSED = "closed"
NOT_OPEN = "not open"

GRACE_SECONDS = 5.0  # extra time a command may take before the hub counts as lost
_POLL = 0.05


class _Worker:
    """One worker thread with its own queue (abandoned as a whole if it gets stuck)."""

    def __init__(self, session: Session):
        self.queue: queue.Queue = queue.Queue()
        self.wake = threading.Event()
        self.deadline: float | None = None
        self.pending = 0  # queued + running commands (guarded by Session._lock)
        self.thread = threading.Thread(
            target=session._work, args=(self,), name="robot-worker", daemon=True
        )
        self.thread.start()


class Session:
    def __init__(
        self,
        connect: Callable[[], kid.Robot],
        output: Callable[[str], None] = print,
        grace: float = GRACE_SECONDS,
        lang: str = EN,
    ):
        self._connect = connect
        self._output = output
        self._grace = grace
        self._lock = threading.Lock()
        self._gen = 0  # bumped by stop(); queued/running commands of older generations end
        self._worker: _Worker | None = None
        self.robot: kid.Robot | None = None
        self.mode = SIMPLE
        self.state = NOT_OPEN
        self.last_color: str | None = None
        self.last_battery: float | None = None
        self.lang = lang  # language of messages ("en" / "de"); input accepts both

    # --- lifecycle ----------------------------------------------------------
    def open(self) -> None:
        """Connect (scans if needed; raises HubNotFoundError if no hub shows up)."""
        self.robot = self._connect()
        self._worker = _Worker(self)
        self.state = CONNECTED

    def close(self, timeout: float = 3.0) -> None:
        """Stop the motors, end the worker and disconnect. Safe to call twice."""
        if self.state == CLOSED:
            return
        worker = self._worker
        if worker is not None and self.state == CONNECTED:
            self.stop()
            worker.queue.put(None)  # sentinel: worker exits after the stop
            worker.thread.join(timeout)
        self._worker = None
        if self.robot is not None:
            self.robot.__exit__(None, None, None)  # safe_shutdown, never raises
        self.state = CLOSED

    def reconnect(self) -> None:
        """Drop the old connection (if any) and connect again."""
        old, self._worker = self._worker, None
        if old is not None:
            with self._lock:
                self._gen += 1
            old.wake.set()
            old.queue.put(None)
        if self.robot is not None:
            self.robot.__exit__(None, None, None)
            self.robot = None
        self.state = DISCONNECTED
        self.open()

    # --- input --------------------------------------------------------------
    def handle(self, line: str) -> bool:
        """Handle one typed line. Returns False when the session should end."""
        self.check()
        try:
            cmd = parse(line, self.mode, self.lang)
        except ParseError as err:
            self._say(str(err))
            return True
        if cmd is None:
            return True

        if cmd.name == "exit":
            return False
        if cmd.name == "help":
            try:
                self._say(help_text(self.mode, cmd.args[0], self.lang))
            except ParseError as err:
                self._say(str(err))
        elif cmd.name in (RAW, SIMPLE):
            self.mode = cmd.name
            self._say(self._t(f"mode_{cmd.name}"))
        elif cmd.name == "language":
            self._set_language(cmd.args[0])
        elif cmd.name == "reconnect":
            self._do_reconnect()
        elif self.state != CONNECTED:
            self._say(self._t("not_connected"))
        elif cmd.name == "stop":
            self.stop()
        else:
            self.submit(cmd)
        return True

    def submit(self, cmd: Command) -> None:
        """Queue a command for the worker."""
        if self._worker is None:
            return
        with self._lock:
            self._worker.queue.put((self._gen, cmd))
            self._worker.pending += 1

    def stop(self) -> None:
        """Cancel queued commands and stop the motors (sent by the worker, not this thread)."""
        worker = self._worker
        if worker is None:
            return
        with self._lock:
            self._gen += 1
            while True:
                try:
                    if worker.queue.get_nowait() is not None:
                        worker.pending -= 1
                except queue.Empty:
                    break
            worker.queue.put((self._gen, Command("stop")))
            worker.pending += 1
        worker.wake.set()

    # --- state --------------------------------------------------------------
    def check(self) -> str:
        """Notice a lost hub (watchdog + pylgbst link). Returns the state."""
        worker = self._worker
        if self.state == CONNECTED and worker is not None:
            stuck = worker.deadline is not None and time.monotonic() > worker.deadline
            if stuck or not self.robot.is_connected():
                self._lost(self._t("hub_stuck" if stuck else "hub_lost"))
        return self.state

    def busy(self) -> bool:
        worker = self._worker
        return worker is not None and worker.pending > 0

    def wait_idle(self, timeout: float = 5.0) -> bool:
        """Wait until all queued commands are done (for tests and scripted use)."""
        end = time.monotonic() + timeout
        while self.busy():
            if time.monotonic() > end or self.check() != CONNECTED:
                return False
            time.sleep(0.01)
        return True

    def _lost(self, why: str) -> None:
        with self._lock:
            self._gen += 1
        if self._worker is not None:
            self._worker.wake.set()
        self._worker = None  # a stuck worker is left behind (daemon thread)
        self.state = DISCONNECTED
        self._say(self._t("press_reconnect", why=why))

    def _do_reconnect(self) -> None:
        self._say(self._t("connecting"))
        try:
            self.reconnect()
        except Exception as exc:  # noqa: BLE001 - stay in the console
            self.state = DISCONNECTED
            self._say(self._t("could_not_connect", error=exc))
            return
        self._say(self._t("connected_again"))

    def _set_language(self, word: str) -> None:
        if word:
            lang = lang_from_word(word)
            if lang is None:
                self._say(self._t("language_unknown"))
                return
            self.lang = lang
            if self.robot is not None:
                self.robot.lang = lang
        self._say(self._t("language_now"))

    def _t(self, key: str, **values) -> str:
        return t(self.lang, key, **values)

    def _say(self, text: str) -> None:
        self._output(text)

    # --- worker -------------------------------------------------------------
    def _work(self, worker: _Worker) -> None:
        while True:
            item = worker.queue.get()
            if item is None:
                return
            gen, cmd = item
            try:
                if gen != self._gen and cmd.name != "stop":
                    continue  # cancelled by stop()
                worker.wake.clear()
                worker.deadline = time.monotonic() + self._budget(cmd)
                text = self._run(cmd, gen, worker)
                if text:
                    self._say(text)
            except Exception as exc:  # noqa: BLE001 - one bad command must not end the session
                log.debug("command %s failed", cmd, exc_info=True)
                if self._worker is worker and self.robot.is_connected():
                    name = BY_NAME[cmd.name].shown(self.lang)
                    self._say(self._t("oops", name=name, error=exc))
            finally:
                worker.deadline = None
                with self._lock:
                    worker.pending -= 1
            if self._worker is not worker:
                return  # abandoned (lost hub or reconnect)

    def _budget(self, cmd: Command) -> float:
        name, args = cmd.name, cmd.args
        if name in ("forward", "back"):
            return args[0] + self._grace
        if name in ("left", "right"):
            return kid.turn_seconds(args[0]) + self._grace
        if name == "motor":
            return args[2] + self._grace
        if name == "angle":
            return 30.0 + self._grace
        return self._grace

    def _cancelled(self, gen: int) -> bool:
        return gen != self._gen

    def _sleep(self, seconds: float, gen: int, worker: _Worker) -> bool:
        """Wait `seconds`; False as soon as stop() cancels this generation."""
        end = time.monotonic() + seconds
        while (left := end - time.monotonic()) > 0:
            if self._cancelled(gen):
                return False
            worker.wake.wait(min(_POLL, left))
        return not self._cancelled(gen)

    def _timed(self, motor, seconds: float, a: float, b: float, gen: int, w: _Worker) -> None:
        motor.timed(seconds, a, b, wait_complete=False)
        if self._sleep(seconds, gen, w):
            self._wait_done(motor, gen, w)
        if self._cancelled(gen):
            motor.stop()

    def _wait_done(self, motor, gen: int, worker: _Worker) -> None:
        """Wait until the hub reports the motor command finished (or stop / deadline)."""
        while getattr(motor, "cmd_in_progress", False) and not self._cancelled(gen):
            if worker.deadline is not None and time.monotonic() > worker.deadline:
                return
            worker.wake.wait(_POLL)

    def _motor(self, port: str):
        hub = self.robot.hub
        motor = {
            "A": getattr(hub, "motor_A", None),
            "B": getattr(hub, "motor_B", None),
            "AB": getattr(hub, "motor_AB", None),
            "C": getattr(hub, "port_C", None),
            "D": getattr(hub, "port_D", None),
        }[port]
        if motor is None or not hasattr(motor, "timed"):
            raise ValueError(f"no motor on port {port}")
        return motor

    def _run(self, cmd: Command, gen: int, w: _Worker) -> str | None:
        robot, name, args = self.robot, cmd.name, cmd.args
        speed, turn = kid._speed(kid.DEFAULT_SPEED), kid._speed(kid.TURN_SPEED)
        if name == "stop":
            robot.stop()
            return self._t("stopped")
        if name == "forward":
            self._timed(robot.hub.motor_AB, args[0], speed, speed, gen, w)
        elif name == "back":
            self._timed(robot.hub.motor_AB, args[0], -speed, -speed, gen, w)
        elif name == "left":
            self._timed(robot.hub.motor_AB, kid.turn_seconds(args[0]), -turn, turn, gen, w)
        elif name == "right":
            self._timed(robot.hub.motor_AB, kid.turn_seconds(args[0]), turn, -turn, gen, w)
        elif name == "led":
            robot.light(args[0])
        elif name == "color":
            self.last_color = robot.see_color()
            return self._t("i_see", color=color_word(self.last_color, self.lang))
        elif name == "distance":
            distance = robot.distance()
            if distance is None:
                return self._t("nothing_in_front")
            return self._t("distance", distance=distance)
        elif name == "motor":
            port, percent, seconds = args
            s = kid._speed(percent)
            self._timed(self._motor(port), seconds, s, s, gen, w)
        elif name == "angle":
            port, degrees, percent = args
            motor = self._motor(port)
            motor.angled(degrees, kid._speed(percent), wait_complete=False)
            self._sleep(0.2, gen, w)  # let the "in progress" feedback arrive first
            self._wait_done(motor, gen, w)
            if self._cancelled(gen):
                motor.stop()
        elif name == "battery":
            self.last_battery = robot.battery()
            if self.last_battery is None:
                return self._t("battery_unknown")
            return self._t("battery", volts=self.last_battery)
        elif name == "sensors":
            self.last_color = robot.see_color()
            self.last_battery = robot.battery()
            color = color_word(self.last_color, self.lang)
            return self._t(
                "sensors", color=color, distance=robot.distance(), volts=self.last_battery
            )
        elif name == "hub":
            devices = getattr(robot.hub, "peripherals", {}) or {}
            rows = [f"  port 0x{port:02x}: {dev}" for port, dev in sorted(devices.items())]
            if not rows:
                return self._t("no_devices")
            return "\n".join([self._t("hub_devices"), *rows])
        return None
