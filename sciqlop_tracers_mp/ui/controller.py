"""Live bar -> (debounce) -> worker thread (T96 trace) -> dock. Pins keep results."""
from __future__ import annotations

import itertools
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from PySide6.QtCore import QObject, QTimer, Signal
from SciQLop.user_api.threading import on_main_thread, unwrap

from ..core.mapping import Mapper
from ..model import MapResult, MPMapError, Pin
from . import format as fmt
from .bar import LiveBar
from .dock import MPDock
from .widget import MPWidget

log = logging.getLogger(__name__)
DEBOUNCE_MS = 250
PDYN_REDRAW = 0.01  # relative Pdyn change that triggers a redraw of the boundary circles


class _Bridge(QObject):
    done = Signal(int, object)
    failed = Signal(int, str)


class MPController:
    """Create with attach(); public methods run on the GUI thread."""

    def __init__(self, panel, satellite: str, t: float | None = None, mapper: Mapper | None = None):
        self._panel, self.satellite = panel, satellite
        self.mapper = mapper or Mapper(satellite)
        self.widget = MPWidget()
        self.dock = MPDock(self.widget, fmt.dock_title(satellite, panel.name), panel.name)
        self.dock.closed.connect(self.close)
        self.widget.pin_clicked.connect(self.pin)
        self.widget.clear_clicked.connect(self.clear_pins)
        self.widget.remove_clicked.connect(self.remove_pin)
        self.pins: list[Pin] = []
        self.current: MapResult | None = None
        self._ids = itertools.count(1)
        self._gen = 0
        self._closed = False
        self._t_submit = 0.0
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="tracers-mp")
        self._bridge = _Bridge()
        self._bridge.done.connect(self._on_done)
        self._bridge.failed.connect(self._on_failed)
        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.setInterval(DEBOUNCE_MS)
        self._timer.timeout.connect(self._submit)
        if t is None:
            tr = panel.time_range
            t = 0.5 * (tr.start() + tr.stop())
        self.bar = LiveBar(panel, t, self._on_bar_moved)
        unwrap(panel._impl).destroyed.connect(self._on_panel_destroyed)
        if not self.dock.placed_beside:
            self.widget.show_message("could not place the map beside its panel; opened on the right")
        self._schedule()

    # --- lifecycle ---------------------------------------------------------------------------------
    def _on_panel_destroyed(self, *_):
        if not self._closed:
            self._shutdown()          # never touch the dying panel's children (the bar)
            self.dock.close()

    def _shutdown(self) -> None:
        self._closed = True
        self._gen += 1
        self._timer.stop()
        self._pool.shutdown(wait=False, cancel_futures=True)

    @on_main_thread
    def close(self) -> None:
        if self._closed:
            return
        self._shutdown()
        self.bar.remove()
        self.dock.close()

    # --- public ------------------------------------------------------------------------------------
    @on_main_thread
    def set_time(self, t: float) -> None:
        self.bar.set_value(t)

    @on_main_thread
    def pin(self) -> Pin | None:
        r = self.current
        if r is None or r.mp_point is None or self._closed:
            return None
        pid = next(self._ids)
        p = Pin(pid, r, fmt.PIN_COLORS[(pid - 1) % len(fmt.PIN_COLORS)])
        self.pins.append(p)
        self.widget.add_pin(p)
        return p

    @on_main_thread
    def remove_pin(self, pin_id: int) -> None:
        self.pins = [p for p in self.pins if p.id != pin_id]
        self.widget.remove_pin(pin_id)

    @on_main_thread
    def clear_pins(self) -> None:
        self.pins = []
        self.widget.clear_pins()

    # --- live computation --------------------------------------------------------------------------
    def _on_bar_moved(self, t: float) -> None:
        if self._closed:
            return
        hit = self.mapper.cached(t)
        if hit is not None:   # instant feedback when dragging over already computed times
            self._gen += 1
            self._timer.stop()
            self._display(hit, 0.0)
            return
        self._schedule()

    def _schedule(self) -> None:
        if not self._closed:
            self._timer.start()

    def _submit(self) -> None:
        if self._closed:
            return
        self._gen += 1
        gen = self._gen
        t = self.bar.value
        self._t_submit = time.monotonic()
        self.widget.show_message(f"tracing T96 field line at {fmt.ymd_hms(t)} …")
        self._pool.submit(self._work, gen, t)

    def _work(self, gen: int, t: float) -> None:
        if gen != self._gen:
            return
        try:
            r = self.mapper.map(t, should_cancel=lambda: gen != self._gen)
        except MPMapError as e:
            self._bridge.failed.emit(gen, str(e))
            return
        except Exception as e:  # network, geopack: report, never kill the worker
            log.exception("MP mapping failed")
            self._bridge.failed.emit(gen, f"{type(e).__name__}: {e}")
            return
        if r is not None:
            self._bridge.done.emit(gen, r)

    def _display(self, r: MapResult, elapsed: float) -> None:
        self.current = r
        if self.widget.map.pdyn is None or abs(r.drivers.pdyn - self.widget.map.pdyn) > PDYN_REDRAW * self.widget.map.pdyn:
            self.widget.map.set_boundary(r.drivers.pdyn)
        self.widget.show_result(r)
        self.widget.show_message(f"T96 + IGRF, {elapsed:.1f} s" if elapsed else "T96 + IGRF (cached)")

    def _on_done(self, gen: int, r: MapResult) -> None:
        if gen != self._gen or self._closed:
            return
        try:
            self._display(r, time.monotonic() - self._t_submit)
        except Exception as e:
            log.exception("MP display failed")
            self.widget.show_message(f"display error: {type(e).__name__}: {e}", error=True)

    def _on_failed(self, gen: int, message: str) -> None:
        if gen == self._gen and not self._closed:
            self.current = None
            self.widget.clear_live()
            self.widget.show_message(message, error=True)


@on_main_thread
def attach(panel, satellite: str, t: float | None = None) -> MPController:
    """Open the magnetopause-map dock beside the panel, with the live bar at t (default: panel centre)."""
    return MPController(panel, satellite, t)
