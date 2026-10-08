from sciqlop_tracers_mp.model import CLOSED, OPEN, Drivers, MapResult
from sciqlop_tracers_mp.ui import format as fmt

D = Drivers(4.09, -122.0, 10.7, 11.5, ("SYM-H",))


def _r(status, **kw):
    return MapResult(t=1759220100.0, satellite="tracers2", status=status, sc_gsm=(0.1, 0.2, 1.06), mlat=69.2,
                     mlt=13.65, drivers=D, **kw)


def test_label_and_rows():
    r = _r(OPEN, crossing=(-21.1, -19.8, -8.8))
    assert fmt.label(r) == "08:15:00 · X -21.1"
    assert fmt.pin_row(r) == ("08:15:00", "open", "-21.10", "-19.80", "-8.80")
    assert "crosses MP" in fmt.live_line(r)


def test_closed_uses_nearest_point():
    r = _r(CLOSED, nearest=(9.9, 0.6, 1.5), min_dist=0.28)
    assert r.mp_point == (9.9, 0.6, 1.5)
    assert fmt.pin_row(r)[1] == "closed (0.28 in)"
    assert "nearest MP point" in fmt.live_line(r)


def test_drivers_line_warns():
    assert "⚠" in fmt.drivers_line(D)
    assert "⚠" not in fmt.drivers_line(Drivers(2.0, -10.0, 1.0, -2.0))


def test_dock_title():
    assert fmt.dock_title("tracers2", "Panel1") == "MP map · TRACERS-2 ↔ Panel1"


def test_ranked_satellites(qapp):
    from sciqlop_tracers_mp.ui.attach import ranked_satellites
    assert ranked_satellites(["speasy//cda//TRACERS//TRACERS2//ACI//TS2_L2_ACI_IPD//x"])[0] == "tracers2"
    assert ranked_satellites(["speasy//cda//TRACERS//TRACERS1//ACI//TS1_L2_ACI_IPD//x"])[0] == "tracers1"
    assert ranked_satellites([]) == ["tracers1", "tracers2"]
