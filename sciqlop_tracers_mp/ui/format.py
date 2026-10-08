"""Text formatting for the dock (Qt-free, unit-tested)."""
from __future__ import annotations

from datetime import datetime, timezone

from ..model import CLOSED, OPEN, SATELLITES, TAIL, UNRESOLVED, Drivers, MapResult

PIN_COLORS = ("#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b", "#e377c2", "#17becf",
              "#bcbd22", "#7f7f7f")
LIVE_COLOR = "#000000"
STATUS_TEXT = {OPEN: "open: leaves the MP", TAIL: "tail line: stays inside the MP",
               CLOSED: "closed: stays inside the MP", UNRESOLVED: "tracing stopped before an outcome"}


def hms(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%H:%M:%S")


def ymd_hms(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def dock_title(satellite: str, panel_name: str) -> str:
    return f"MP map · {SATELLITES.get(satellite, satellite)} ↔ {panel_name}"


def point_text(r: MapResult) -> str:
    p = r.mp_point
    if p is None:
        return "no point"
    xyz = f"X {p[0]:+.1f}  Y {p[1]:+.1f}  Z {p[2]:+.1f} R_E"
    if r.status == OPEN:
        return f"crosses MP at {xyz}"
    return f"nearest MP point {xyz} ({r.min_dist:.2f} R_E inside)"


def live_line(r: MapResult) -> str:
    return f"{ymd_hms(r.t)}  {STATUS_TEXT[r.status]} · {point_text(r)}"


def spacecraft_line(r: MapResult) -> str:
    x, y, z = r.sc_gsm
    return f"s/c MLat {r.mlat:.1f}° MLT {r.mlt:.2f} h · GSM ({x:.3f}, {y:.3f}, {z:.3f}) R_E"


def drivers_line(d: Drivers) -> str:
    s = f"OMNI 1-min: Pdyn {d.pdyn:.2f} nPa · SYM-H {d.symh:.0f} nT · By {d.by:+.1f} · Bz {d.bz:+.1f} nT"
    return s + ("  ⚠ outside T96 range" if d.warnings else "")


def label(r: MapResult) -> str:
    """Short label drawn next to a point on the map."""
    p = r.mp_point
    return f"{hms(r.t)} · X {p[0]:+.1f}" if p is not None else hms(r.t)


def pin_row(r: MapResult) -> tuple[str, str, str, str, str]:
    """(time, status, X, Y, Z) cells of the pin table."""
    p = r.mp_point
    xyz = ("", "", "") if p is None else tuple(f"{v:+.2f}" for v in p)
    status = r.status if r.status == OPEN else f"{r.status} ({r.min_dist:.2f} in)"
    return (hms(r.t), status, *xyz)


def tooltip(r: MapResult) -> str:
    lines = [live_line(r), spacecraft_line(r), drivers_line(r.drivers), *r.drivers.warnings]
    return "\n".join(lines)
