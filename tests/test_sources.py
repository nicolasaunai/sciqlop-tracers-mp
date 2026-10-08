import numpy as np
import pytest

from conftest import T_0815, fake_omni_fetch, fake_position_fetch
from sciqlop_tracers_mp.core.drivers import DriverSource, range_warnings
from sciqlop_tracers_mp.core.position import PositionSource
from sciqlop_tracers_mp.model import NoDriversError, NoPositionError


def test_position_spline_hits_samples():
    ps = PositionSource("tracers2", fake_position_fetch)
    t, xyz = fake_position_fetch("tracers2", T_0815 - 300, T_0815 + 300)
    for k in range(len(t)):
        assert np.allclose(ps.geo_km(t[k]), xyz[k], atol=1e-6)


def test_position_altitude_leo():
    r = np.linalg.norm(PositionSource("tracers2", fake_position_fetch).geo_km(T_0815))
    assert 6371.0 + 550 < r < 6371.0 + 620


def test_position_outside_coverage_raises():
    ps = PositionSource("tracers2", fake_position_fetch)
    with pytest.raises(NoPositionError):
        ps.geo_km(T_0815 + 86400)


def test_drivers_values_2025_09_30_0815():
    d = DriverSource(fake_omni_fetch).at(T_0815)
    assert d.pdyn == pytest.approx(4.09, abs=0.05)
    assert d.symh == pytest.approx(-122, abs=1)
    assert d.by == pytest.approx(10.67, abs=0.05)
    assert d.bz == pytest.approx(11.54, abs=0.05)
    assert len(d.warnings) == 3  # SYM-H, By, Bz outside the T96 range


def test_drivers_gap_raises():
    def gappy(param, t0, t1):
        t, y = fake_omni_fetch(param, t0, t1)
        y = y.copy()
        y[np.abs(t - T_0815) < 3600] = np.nan
        return t, y
    with pytest.raises(NoDriversError):
        DriverSource(gappy).at(T_0815)


def test_range_warnings_empty_inside_range():
    assert range_warnings({"pdyn": 2.0, "symh": -20.0, "by": 3.0, "bz": -4.0}) == ()
