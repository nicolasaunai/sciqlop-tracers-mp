"""T96 magnetopause (Tsyganenko 1995, 1996; pressure-scaled), as implemented by geopack.t96_mgnp.

With vel < 0 (pressure given directly) the boundary is axisymmetric about X_GSM, so a cross-section at
fixed X is a circle of radius rho(X).
"""
from __future__ import annotations

import numpy as np
from geopack import geopack as gp
from scipy.optimize import brentq

RHO_MAX = 80.0  # R_E, search bracket for the boundary radius


def signed_distance(pdyn: float, p) -> float:
    """Distance to the T96 magnetopause, > 0 inside, < 0 outside (R_E)."""
    _, _, _, dist, inside = gp.t96_mgnp(float(pdyn), -1.0, float(p[0]), float(p[1]), float(p[2]))
    return inside * dist


def boundary_point(pdyn: float, p) -> np.ndarray:
    """Point of the T96 magnetopause associated with p (same ellipsoidal tau coordinate)."""
    xm, ym, zm, _, _ = gp.t96_mgnp(float(pdyn), -1.0, float(p[0]), float(p[1]), float(p[2]))
    return np.array([xm, ym, zm])


def radius_at(pdyn: float, x: float) -> float | None:
    """Distance of the magnetopause from the X axis at X_GSM = x; None if x is sunward of the nose."""
    f = lambda rho: signed_distance(pdyn, (x, rho, 0.0))  # noqa: E731
    if f(0.0) <= 0:
        return None
    if f(RHO_MAX) > 0:
        return None
    return float(brentq(f, 0.0, RHO_MAX, xtol=1e-4))


def standoff(pdyn: float) -> float:
    """Subsolar magnetopause distance, R_E."""
    return float(brentq(lambda x: signed_distance(pdyn, (x, 0.0, 0.0)), 1.0, 40.0, xtol=1e-4))


def cross_section(pdyn: float, x: float, n: int = 181):
    """Circle at X = x as (y, z_upper_and_lower[n, 2]); None if the boundary does not reach x."""
    rho = radius_at(pdyn, x)
    if rho is None:
        return None
    y = np.linspace(-rho, rho, n)
    zu = np.sqrt(np.clip(rho * rho - y * y, 0.0, None))
    return y, np.column_stack([zu, -zu])
