"""Spacecraft -> T96 field line -> point where it leaves the T96 magnetopause.

Tracing (IGRF + T96, geopack): from the spacecraft away from the Earth, i.e. antiparallel to B in the
northern hemisphere (geopack dir=+1) and parallel in the southern one (dir=-1). Along the line, the signed
distance to the T96 magnetopause (`t96_mgnp`) changes sign where the line leaves the boundary; the root is
interpolated linearly between the bracketing trace points and projected onto the boundary.
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Callable

import numpy as np
from geopack import geopack as gp

from ..model import CLOSED, OPEN, TAIL, UNRESOLVED, MapResult
from . import magnetopause as mp
from .drivers import DriverSource
from .geopack_lock import GEOPACK_LOCK
from .position import PositionSource

RE_KM = 6371.2
RLIM = 60.0        # R_E, outer tracing limit
MAXLOOP = 4000
CACHE_SIZE = 512
TIME_QUANTUM = 1.0  # s: results are cached per second of time


def geo_to_gsm(t: float, geo_km) -> np.ndarray:
    """Caller holds GEOPACK_LOCK and has called gp.recalc(t)."""
    return np.array(gp.geogsm(*(np.asarray(geo_km, float) / RE_KM), 1))


def mlat_mlt(gsm) -> tuple[float, float]:
    """Caller holds GEOPACK_LOCK after gp.recalc(t)."""
    x, y, z = gp.smgsm(*gsm, -1)
    r = float(np.sqrt(x * x + y * y + z * z))
    return float(np.degrees(np.arcsin(z / r))), float((np.degrees(np.arctan2(y, x)) / 15.0 + 12.0) % 24.0)


def trace_line(t: float, gsm, parmod) -> np.ndarray:
    """Field line from gsm, away from the Earth. Caller holds GEOPACK_LOCK after gp.recalc(t)."""
    direction = 1.0 if gsm[2] > 0 else -1.0
    _, _, _, xx, yy, zz = gp.trace(float(gsm[0]), float(gsm[1]), float(gsm[2]), direction, rlim=RLIM, r0=1.0,
                                   parmod=parmod, exname="t96", inname="igrf", maxloop=MAXLOOP)
    return np.column_stack([xx, yy, zz])


def classify(line: np.ndarray, pdyn: float):
    """(status, crossing or None, min signed distance or None, nearest boundary point or None).

    For lines that do not leave the magnetopause, `nearest` is the boundary point associated with the line
    point of smallest distance (t96_mgnp's tau projection, which tends to the true nearest point as the
    distance goes to zero).
    """
    s = np.array([mp.signed_distance(pdyn, p) for p in line])
    out = np.flatnonzero(s < 0)
    if out.size and out[0] > 0:
        k = out[0]
        f = s[k - 1] / (s[k - 1] - s[k])
        pc = line[k - 1] + f * (line[k] - line[k - 1])
        return OPEN, tuple(float(v) for v in mp.boundary_point(pdyn, pc)), None, None
    r = np.linalg.norm(line, axis=1)
    k = int(np.argmin(s))
    smin = float(s[k])
    nearest = tuple(float(v) for v in mp.boundary_point(pdyn, line[k]))
    if r[-1] < 1.05 and r.max() > 1.5:
        return CLOSED, None, smin, nearest
    if r[-1] >= RLIM - 0.5 or line[-1, 0] >= 20 - 1e-6 or np.hypot(line[-1, 1], line[-1, 2]) >= 40 - 1e-6:
        return TAIL, None, smin, nearest  # geopack also stops at x >= 20 or y^2 + z^2 >= 1600
    return UNRESOLVED, None, smin, nearest


class Mapper:
    """Thread-safe. map(t) costs one T96 trace (~1-3 s) unless cached."""

    def __init__(self, satellite: str, positions: PositionSource | None = None,
                 drivers: DriverSource | None = None):
        self.satellite = satellite
        self.positions = positions or PositionSource(satellite)
        self.drivers = drivers or DriverSource()
        self._cache: OrderedDict[float, MapResult] = OrderedDict()
        self._cache_lock = threading.Lock()

    def cached(self, t: float) -> MapResult | None:
        key = round(float(t) / TIME_QUANTUM) * TIME_QUANTUM
        with self._cache_lock:
            return self._cache.get(key)

    def map(self, t: float, should_cancel: Callable[[], bool] = lambda: False) -> MapResult | None:
        key = round(float(t) / TIME_QUANTUM) * TIME_QUANTUM
        hit = self.cached(key)
        if hit is not None:
            return hit
        geo = self.positions.geo_km(key)
        drv = self.drivers.at(key)
        if should_cancel():
            return None
        with GEOPACK_LOCK:
            gp.recalc(key)
            gsm = geo_to_gsm(key, geo)
            mlat, mlt = mlat_mlt(gsm)
            line = trace_line(key, gsm, drv.parmod)
        status, crossing, smin, nearest = classify(line, drv.pdyn)
        res = MapResult(t=key, satellite=self.satellite, status=status, sc_gsm=tuple(float(v) for v in gsm),
                        mlat=mlat, mlt=mlt, drivers=drv, crossing=crossing, min_dist=smin, nearest=nearest)
        with self._cache_lock:
            self._cache[key] = res
            while len(self._cache) > CACHE_SIZE:
                self._cache.popitem(last=False)
        return res
