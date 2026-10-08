"""TRACERS position from SSCWeb (GEO, 60 s), cubic-spline interpolated.

Checked against TS2_L2_MAG_BDC-16SPS/ts2_l2_mag_1sps_geo_pos on 2025-09-30 08:10-08:19:
cubic spline through the 60 s SSCWeb samples is within 0.4 km of the 1 s MAG position (linear: 4 km).
"""
from __future__ import annotations

import threading
from typing import Callable

import numpy as np
from scipy.interpolate import CubicSpline

from ..model import NoPositionError

HALF_WINDOW = 600.0   # s fetched on each side of the requested time
MARGIN = 120.0        # s: refetch when t is closer than this to the cached window edge

# fetch(satellite, t0, t1) -> (epoch seconds [n], GEO km [n, 3]) or None
Fetch = Callable[[str, float, float], "tuple[np.ndarray, np.ndarray] | None"]


def speasy_fetch(satellite: str, t0: float, t1: float):
    import speasy as spz
    from datetime import datetime, timezone
    v = spz.get_data(f"ssc/{satellite}", datetime.fromtimestamp(t0, timezone.utc),
                     datetime.fromtimestamp(t1, timezone.utc), coordinate_system="geo")
    if v is None or len(v) == 0:
        return None
    t = v.time.astype("datetime64[ns]").astype("int64") * 1e-9
    return t, np.asarray(v.values, dtype=float)


class PositionSource:
    """Thread-safe; one cached window per instance."""

    def __init__(self, satellite: str, fetch: Fetch = speasy_fetch):
        self.satellite = satellite
        self._fetch = fetch
        self._lock = threading.Lock()
        self._window: tuple[float, float] | None = None
        self._spline: CubicSpline | None = None

    def geo_km(self, t: float) -> np.ndarray:
        with self._lock:
            if self._window is None or not (self._window[0] + MARGIN <= t <= self._window[1] - MARGIN):
                self._load(t)
            lo, hi = self._spline.x[0], self._spline.x[-1]
            if not lo <= t <= hi:
                raise NoPositionError(f"no {self.satellite} position at this time (SSCWeb coverage ends)")
            return np.asarray(self._spline(t), dtype=float)

    def _load(self, t: float) -> None:
        got = self._fetch(self.satellite, t - HALF_WINDOW, t + HALF_WINDOW)
        if got is None or len(got[0]) < 4:
            raise NoPositionError(f"no {self.satellite} position from SSCWeb around this time")
        ts, xyz = got
        keep = np.isfinite(xyz).all(axis=1)
        ts, xyz = ts[keep], xyz[keep]
        order = np.argsort(ts)
        ts, xyz = ts[order], xyz[order]
        ts, uniq = np.unique(ts, return_index=True)
        if len(ts) < 4:
            raise NoPositionError(f"no {self.satellite} position from SSCWeb around this time")
        self._spline = CubicSpline(ts, xyz[uniq])
        self._window = (float(ts[0]), float(ts[-1]))
