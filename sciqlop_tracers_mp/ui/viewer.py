"""Magnetopause seen from the Sun (Y-Z GSM) with the live point and the pinned points (GUI thread only).

Drawn with one standalone SciQLopMultiPlotPanel holding an XY plot, kept square by this widget (no QLayout
inside, the dock must stay shrinkable). SciQLop 0.14 / SciQLopPlots quirks handled here:
- an XY axis cannot be reversed: the horizontal coordinate is -Y_GSM and the tick labels show Y, so dusk
  (+Y) is on the left as seen from the Sun;
- Line graphs draw y(x): each circle is drawn as its upper and lower halves;
- marker shape/size are set on the graph components (private `_impl`);
- Text needs an explicit coordinate system to render.
"""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QWidget
from SciQLop.user_api.plot import GraphType, PlotPanel, PlotType, Text
from SciQLop.user_api.plot.enums import CoordinateSystem
from SciQLop.user_api.threading import unwrap
from SciQLopPlots import GraphMarkerShape, SciQLopMultiPlotPanel

from ..core import magnetopause as mp
from ..model import OPEN, MapResult
from . import format as fmt

X_LEVELS = (8.0, 5.0, 0.0, -10.0, -20.0)
CIRCLE_COLOR = "#9a9a9a"
HALF_RANGE = 26.0         # R_E shown on both axes
TICK_STEP = 5.0
MARKER_SIZE = 11.0
LABEL_DZ = 1.3            # R_E: live label above its point, pin labels below
LABEL_STAGGER = 4         # pin labels cycle over this many rows
NAN2 = (np.array([0.0, 1.0]), np.full((2, 2), np.nan))


def _style(graph, filled: bool, size: float = MARKER_SIZE) -> None:
    for c in unwrap(graph._impl).components():
        c.set_marker_shape(GraphMarkerShape.FilledCircle if filled else GraphMarkerShape.Circle)
        c.set_marker_size(size)


class MPMap(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._impl = SciQLopMultiPlotPanel(self, synchronize_x=False, synchronize_time=False)
        self._impl.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._impl.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        pnl = PlotPanel(self._impl)
        self._plot, first = pnl.plot_data(*NAN2, plot_type=PlotType.XY, graph_type=GraphType.Line,
                                          labels=["", ""], colors=[CIRCLE_COLOR, CIRCLE_COLOR])
        self._circles = [first]
        for _ in X_LEVELS[1:]:
            _, g = pnl.plot_data(*NAN2, plot_index=0, plot_type=PlotType.XY, graph_type=GraphType.Line,
                                 labels=["", ""], colors=[CIRCLE_COLOR, CIRCLE_COLOR])
            self._circles.append(g)
        self._circle_texts: list[Text] = []
        _, self._live = pnl.plot_data(np.array([np.nan]), np.array([np.nan]), plot_index=0, plot_type=PlotType.XY,
                                      graph_type=GraphType.Scatter, colors=[fmt.LIVE_COLOR])
        _style(self._live, True)
        self._live_text: Text | None = None
        self._pins: dict[int, tuple[object, Text]] = {}
        self._pnl = pnl
        unwrap(self._plot._impl).legend().set_visible(False)
        ticks = np.arange(-HALF_RANGE // TICK_STEP * TICK_STEP, HALF_RANGE + 1e-9, TICK_STEP)
        self._plot.set_axis_tick_labels("x", {float(v): f"{-v:g}" for v in ticks})
        self._plot.set_axis_label("x", "Y GSM, seen from the Sun (dusk left)", "R_E")
        self._plot.set_axis_label("y", "Z GSM", "R_E")
        self._fix_range()
        self.pdyn: float | None = None

    # --- geometry ------------------------------------------------------------------------------------
    def sizeHint(self) -> QSize:
        return QSize(420, 420)

    def minimumSizeHint(self) -> QSize:
        return QSize(220, 220)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        s = min(self.width(), self.height())
        self._impl.setGeometry((self.width() - s) // 2, (self.height() - s) // 2, s, s)

    def _fix_range(self) -> None:
        self._plot.set_x_range(-HALF_RANGE, HALF_RANGE)
        self._plot.set_y_range(-HALF_RANGE, HALF_RANGE)

    # --- content -------------------------------------------------------------------------------------
    @staticmethod
    def _xy(p) -> tuple[float, float]:
        return -float(p[1]), float(p[2])  # horizontal = -Y (view from the Sun)

    def set_boundary(self, pdyn: float) -> None:
        """Redraw the T96 cross-sections for this dynamic pressure."""
        self.pdyn = float(pdyn)
        for t in self._circle_texts:
            t.remove()
        self._circle_texts = []
        for g, xl in zip(self._circles, X_LEVELS):
            sec = mp.cross_section(pdyn, xl)
            if sec is None:
                g.set_data(*NAN2)
                continue
            y, zz = sec
            g.set_data(-y[::-1], zz[::-1])  # horizontal axis -Y must increase
            rho = float(np.max(zz))
            self._circle_texts.append(Text(self._plot, f"X={xl:g}", 0.0, rho + 0.6, color=CIRCLE_COLOR,
                                           font_size=8, coordinate_system=CoordinateSystem.Data))
        self._fix_range()

    def set_live(self, r: MapResult | None) -> None:
        if self._live_text is not None:
            self._live_text.remove()
            self._live_text = None
        p = None if r is None else r.mp_point
        if p is None:
            self._live.set_data(np.array([np.nan]), np.array([np.nan]))
        else:
            x, y = self._xy(p)
            self._live.set_data(np.array([x]), np.array([y]))
            _style(self._live, r.status == OPEN)
            self._live_text = Text(self._plot, fmt.label(r), x, y + LABEL_DZ, color=fmt.LIVE_COLOR, font_size=9,
                                   coordinate_system=CoordinateSystem.Data)
        self._fix_range()

    def add_pin(self, pin_id: int, r: MapResult, color: str) -> None:
        p = r.mp_point
        if p is None:
            return
        x, y = self._xy(p)
        _, g = self._pnl.plot_data(np.array([x]), np.array([y]), plot_index=0, plot_type=PlotType.XY,
                                   graph_type=GraphType.Scatter, colors=[color])
        _style(g, r.status == OPEN)
        dz = LABEL_DZ * (1 + 1.2 * ((pin_id - 1) % LABEL_STAGGER))  # nearby pins: labels on separate rows
        txt = Text(self._plot, fmt.label(r), x, y - dz, color=color, font_size=9,
                   coordinate_system=CoordinateSystem.Data)
        self._pins[pin_id] = (g, txt)
        unwrap(self._plot._impl).legend().set_visible(False)
        self._fix_range()

    def remove_pin(self, pin_id: int) -> None:
        g, txt = self._pins.pop(pin_id, (None, None))
        if g is not None:
            self._plot.remove_graph(g)
            txt.remove()

    def clear_pins(self) -> None:
        for pid in list(self._pins):
            self.remove_pin(pid)

    def save_png(self, path: str) -> None:
        unwrap(self._plot._impl).save_png(path)
