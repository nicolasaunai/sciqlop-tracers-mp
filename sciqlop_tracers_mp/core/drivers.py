"""T96 inputs from OMNI_HRO_1MIN (already propagated to the bow-shock nose).

Pdyn, SYM-H (as Dst), IMF By and Bz GSM, linearly interpolated at t over valid samples. A gap longer than
MAX_GAP around t is an error rather than a silent interpolation.
"""
from __future__ import annotations

import threading
from typing import Callable

import numpy as np

from ..model import Drivers, NoDriversError

PRODUCTS = {"pdyn": "Pressure", "symh": "SYM_H", "by": "BY_GSM", "bz": "BZ_GSM"}
HALF_WINDOW = 3 * 3600.0
MARGIN = 1800.0
MAX_GAP = 1800.0  # s: nearest valid sample must be within this of t

# T96 parameterisation range (Tsyganenko 1996; geopack t96 docstring)
T96_RANGE = {"pdyn": (0.5, 10.0), "symh": (-100.0, 20.0), "by": (-10.0, 10.0), "bz": (-10.0, 10.0)}
LABELS = {"pdyn": "Pdyn", "symh": "SYM-H", "by": "By", "bz": "Bz"}

# fetch(omni_parameter, t0, t1) -> (epoch seconds [n], values [n], NaN for fill) or None
Fetch = Callable[[str, float, float], "tuple[np.ndarray, np.ndarray] | None"]


def speasy_fetch(param: str, t0: float, t1: float):
    import speasy as spz
    from datetime import datetime, timezone
    v = spz.get_data(f"cda/OMNI_HRO_1MIN/{param}", datetime.fromtimestamp(t0, timezone.utc),
                     datetime.fromtimestamp(t1, timezone.utc))
    if v is None or len(v) == 0:
        return None
    v = v.astype(float).replace_fillval_by_nan()
    t = v.time.astype("datetime64[ns]").astype("int64") * 1e-9
    return t, np.asarray(v.values[:, 0], dtype=float)


def range_warnings(values: dict) -> tuple[str, ...]:
    out = []
    for k, (lo, hi) in T96_RANGE.items():
        if not lo <= values[k] <= hi:
            out.append(f"{LABELS[k]} = {values[k]:.1f} outside T96 range [{lo:g}, {hi:g}]")
    return tuple(out)


class DriverSource:
    """Thread-safe; caches one window of each OMNI parameter."""

    def __init__(self, fetch: Fetch = speasy_fetch):
        self._fetch = fetch
        self._lock = threading.Lock()
        self._window: tuple[float, float] | None = None
        self._series: dict[str, tuple[np.ndarray, np.ndarray]] = {}

    def at(self, t: float) -> Drivers:
        with self._lock:
            if self._window is None or not (self._window[0] + MARGIN <= t <= self._window[1] - MARGIN):
                self._load(t)
            values = {k: self._interp(k, t) for k in PRODUCTS}
        return Drivers(warnings=range_warnings(values), **values)

    def _load(self, t: float) -> None:
        series = {}
        for key, param in PRODUCTS.items():
            got = self._fetch(param, t - HALF_WINDOW, t + HALF_WINDOW)
            if got is None:
                raise NoDriversError(f"no OMNI {param} around this time")
            ts, y = got
            ok = np.isfinite(y)
            series[key] = (np.asarray(ts)[ok], np.asarray(y)[ok])
        self._series = series
        self._window = (t - HALF_WINDOW, t + HALF_WINDOW)

    def _interp(self, key: str, t: float) -> float:
        ts, y = self._series[key]
        if len(ts) == 0 or np.min(np.abs(ts - t)) > MAX_GAP:
            raise NoDriversError(f"OMNI {PRODUCTS[key]} has no valid data within {MAX_GAP / 60:.0f} min")
        return float(np.interp(t, ts, y))
