"""One draggable vertical bar spanning every plot of a panel (GUI thread only).

Only module touching SciQLopPlots' MultiPlotsVerticalLine (through the panel's private `_impl`). Plots added
to the panel later get the bar too (MultiPlotsVerticalLine follows the panel's plot list).
"""
from __future__ import annotations

from typing import Callable

from SciQLop.user_api.threading import unwrap
from SciQLopPlots import MultiPlotsVerticalLine

COLOR = "#000000"
WIDTH = 2.0


class LiveBar:
    def __init__(self, panel, t: float, on_moved: Callable[[float], None], tooltip: str = "MP map: drag me"):
        self._line = MultiPlotsVerticalLine(unwrap(panel._impl), float(t), COLOR, False, True, tooltip)
        self._line.set_line_width(WIDTH)
        self._line.position_changed.connect(lambda p: on_moved(float(p)))

    @property
    def value(self) -> float:
        return float(self._line.position)

    def set_value(self, t: float) -> None:
        self._line.set_position(float(t))  # emits position_changed

    def remove(self) -> None:
        try:
            self._line.deleteLater()
        except RuntimeError:  # already deleted with its panel
            pass
