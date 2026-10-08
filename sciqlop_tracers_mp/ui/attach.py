"""'MP ▾' button in each panel's chrome row: open the magnetopause map for TRACERS-1 or -2.

Private SciQLop pieces (same as sciqlop_vdf.ui.attach): PanelContainer.chrome_row, the `sqp_product_path`
Qt property on plottables.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMenu, QToolButton
from SciQLop.user_api.plot import PlotPanel
from SciQLop.user_api.threading import unwrap

from ..model import SATELLITES
from .controller import attach

log = logging.getLogger(__name__)
BUTTON_NAME = "sciqlop_tracers_mp_attach"
HINTS = {"tracers1": ("tracers1", "ts1_", "ts1/"), "tracers2": ("tracers2", "ts2_", "ts2/", "//ts2//")}


def product_paths(panel: PlotPanel) -> list[str]:
    paths = []
    for p in panel.plots:
        try:
            plottables = unwrap(p._impl).plottables()
        except Exception:  # noqa: BLE001 — non time-series plots
            continue
        for g in plottables:
            path = g.property("sqp_product_path")
            if path:
                paths.append(str(path))
    return paths


def ranked_satellites(paths: list[str]) -> list[str]:
    """Satellites whose products are on the panel first (then the other)."""
    low = " ".join(paths).lower()
    score = {s: sum(low.count(h) for h in hints) for s, hints in HINTS.items()}
    return sorted(SATELLITES, key=lambda s: (-score[s], s))


class AttachButton(QToolButton):
    def __init__(self, tsp, parent=None):
        super().__init__(parent)
        self.setObjectName(BUTTON_NAME)
        self.setText("MP ▾")
        self.setToolTip("Map the TRACERS magnetic footprint onto the T96 magnetopause")
        self.setPopupMode(QToolButton.InstantPopup)
        self._tsp = tsp
        self.controllers = []
        self._menu = QMenu(self)
        self._menu.aboutToShow.connect(self._fill)
        self.setMenu(self._menu)

    def _fill(self) -> None:
        self._menu.clear()
        for sat in ranked_satellites(product_paths(PlotPanel(self._tsp))):
            self._menu.addAction(SATELLITES[sat]).triggered.connect(lambda _=False, s=sat: self.attach(s))

    def attach(self, satellite: str):
        ctl = attach(PlotPanel(self._tsp), satellite)
        self.controllers.append(ctl)
        return ctl


def _container(tsp):
    node = tsp
    while node is not None:
        if type(node).__name__ == "PanelContainer":
            return node
        node = node.parent()
    return None


def install(tsp) -> bool:
    container = _container(tsp)
    row = getattr(container, "chrome_row", None)
    if row is None or row.layout() is None:
        return False
    if row.findChild(QToolButton, BUTTON_NAME) is not None:
        return True
    layout = row.layout()
    layout.insertWidget(max(layout.count() - 1, 0), AttachButton(tsp, row))
    return True


def install_attach_buttons(main_window) -> None:
    for name in main_window.plot_panels():
        tsp = main_window.plot_panel(name)
        if tsp is not None:
            install(tsp)
    main_window.panel_added.connect(lambda tsp: QTimer.singleShot(0, lambda: install(tsp)))
