"""Dock content: status lines, magnetopause map, Pin/Clear buttons, pin table (GUI thread only)."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QToolButton, QVBoxLayout, QWidget)

from ..model import MapResult, Pin
from . import format as fmt
from .viewer import MPMap

COLUMNS = ("", "time", "status", "X", "Y", "Z", "")


class MPWidget(QWidget):
    pin_clicked = Signal()
    clear_clicked = Signal()
    remove_clicked = Signal(int)   # pin id

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(4, 4, 4, 4)
        self.live = QLabel("move the black bar on the panel")
        self.sc = QLabel("")
        self.drivers = QLabel("")
        self.status = QLabel("")
        for w in (self.live, self.sc, self.drivers, self.status):
            w.setTextInteractionFlags(Qt.TextSelectableByMouse)
            w.setWordWrap(True)
            lay.addWidget(w)
        self.map = MPMap(self)
        lay.addWidget(self.map, 1)
        row = QHBoxLayout()
        self.pin_button = QPushButton("Pin")
        self.pin_button.setToolTip("Keep the current point on the map")
        self.pin_button.setEnabled(False)
        self.clear_button = QPushButton("Clear")
        self.clear_button.setToolTip("Remove all pinned points")
        row.addWidget(self.pin_button)
        row.addWidget(self.clear_button)
        row.addStretch(1)
        lay.addLayout(row)
        self.table = QTableWidget(0, len(COLUMNS), self)
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.NoSelection)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setMaximumHeight(170)
        lay.addWidget(self.table)
        self.pin_button.clicked.connect(self.pin_clicked.emit)
        self.clear_button.clicked.connect(self.clear_clicked.emit)
        self._rows: list[int] = []  # pin id per table row

    # --- live --------------------------------------------------------------------------------------
    def show_result(self, r: MapResult) -> None:
        self.live.setText(fmt.live_line(r))
        self.sc.setText(fmt.spacecraft_line(r))
        self.drivers.setText(fmt.drivers_line(r.drivers))
        self.drivers.setToolTip("\n".join(r.drivers.warnings) or "inputs inside the T96 range")
        self.drivers.setStyleSheet("color: #b35900;" if r.drivers.warnings else "")
        self.pin_button.setEnabled(r.mp_point is not None)
        self.map.set_live(r)

    def show_message(self, text: str, error: bool = False) -> None:
        self.status.setText(text)
        self.status.setStyleSheet("color: #c0392b;" if error else "color: #666;")

    def clear_live(self) -> None:
        self.pin_button.setEnabled(False)
        self.map.set_live(None)

    # --- pins --------------------------------------------------------------------------------------
    def add_pin(self, pin: Pin) -> None:
        r = pin.result
        row = self.table.rowCount()
        self.table.insertRow(row)
        swatch = QTableWidgetItem("■")
        swatch.setForeground(QColor(pin.color))
        self.table.setItem(row, 0, swatch)
        for col, text in enumerate(fmt.pin_row(r), start=1):
            item = QTableWidgetItem(text)
            item.setToolTip(fmt.tooltip(r))
            self.table.setItem(row, col, item)
        x = QToolButton()
        x.setText("×")
        x.setToolTip("Remove this pin")
        x.clicked.connect(lambda _=False, pid=pin.id: self.remove_clicked.emit(pid))
        self.table.setCellWidget(row, len(COLUMNS) - 1, x)
        self._rows.append(pin.id)
        self.map.add_pin(pin.id, r, pin.color)

    def remove_pin(self, pin_id: int) -> None:
        if pin_id in self._rows:
            self.table.removeRow(self._rows.index(pin_id))
            self._rows.remove(pin_id)
        self.map.remove_pin(pin_id)

    def clear_pins(self) -> None:
        self.table.setRowCount(0)
        self._rows = []
        self.map.clear_pins()
