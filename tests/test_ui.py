import pytest

from sciqlop_tracers_mp.model import CLOSED, OPEN, Drivers, MapResult, Pin

D = Drivers(4.09, -122.0, 10.7, 11.5, ())


def _r(status, t=1759220100.0, **kw):
    return MapResult(t=t, satellite="tracers2", status=status, sc_gsm=(0.1, 0.2, 1.06), mlat=69.2, mlt=13.65,
                     drivers=D, **kw)


@pytest.fixture
def manager(qapp):
    import PySide6QtAds as QtAds
    from PySide6.QtWidgets import QMainWindow
    win = QMainWindow()
    mgr = QtAds.CDockManager(win)
    yield mgr
    win.deleteLater()


def test_dock_close_and_external_destroy(manager, qapp):
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QWidget
    from sciqlop_tracers_mp.ui.dock import MPDock
    a = MPDock(QWidget(), "MP map · TRACERS-2 ↔ Panel0", None, manager=manager)
    b = MPDock(QWidget(), "MP map · TRACERS-2 ↔ Panel0", None, manager=manager)
    fired = []
    b.closed.connect(lambda: fired.append(1))
    a.close()
    b._doc.takeWidget().deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete)
    assert fired == [1]


def test_widget_pins_roundtrip(qapp):
    from sciqlop_tracers_mp.ui.widget import MPWidget
    w = MPWidget()
    w.map.set_boundary(4.09)
    w.show_result(_r(OPEN, crossing=(-9.2, -16.9, -6.1)))
    assert w.pin_button.isEnabled()
    w.add_pin(Pin(1, _r(OPEN, crossing=(-9.2, -16.9, -6.1)), "#d62728"))
    w.add_pin(Pin(2, _r(CLOSED, t=1759220160.0, nearest=(9.9, 0.4, 1.4), min_dist=0.3), "#1f77b4"))
    assert w.table.rowCount() == 2 and len(w.map._pins) == 2
    w.remove_pin(1)
    assert w.table.rowCount() == 1 and list(w.map._pins) == [2]
    assert w.table.item(0, 1).text() == "08:16:00"
    w.clear_pins()
    assert w.table.rowCount() == 0 and not w.map._pins
    w.clear_live()
    assert not w.pin_button.isEnabled()
