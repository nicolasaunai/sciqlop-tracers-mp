import numpy as np
import pytest

from conftest import T_0815
from sciqlop_tracers_mp.core.mapping import RE_KM, classify, geo_to_gsm
from sciqlop_tracers_mp.model import CLOSED, OPEN, TAIL


def test_geo_to_gsm_matches_spacepy():
    spc = pytest.importorskip("spacepy.coordinates")
    from datetime import datetime, timezone
    from geopack import geopack as gp
    from spacepy.time import Ticktock
    geo = np.array([425.0, 1222.6, 6835.4])  # km, TS2 at 08:14:00
    gp.recalc(T_0815)
    ours = geo_to_gsm(T_0815, geo)
    c = spc.Coords(np.atleast_2d(geo / RE_KM), "GEO", "car", units=["Re"] * 3,
                   ticks=Ticktock([datetime.fromtimestamp(T_0815, timezone.utc).replace(tzinfo=None)], "UTC"))
    ref = c.convert("GSM", "car").data[0]
    assert np.linalg.norm(ours - ref) * RE_KM < 2.0  # km


def test_lobe_line_at_0814(mapper):
    r = mapper.map(T_0815 - 60)
    assert r.status == TAIL
    assert 70 < r.mlat < 72 and 14.0 < r.mlt < 14.5
    assert r.crossing is None and r.nearest is not None and r.nearest[2] > 8  # high-latitude grazing point


def test_closed_line_at_0816(mapper):
    r = mapper.map(T_0815 + 60)
    assert r.status == CLOSED
    assert r.nearest[0] == pytest.approx(9.9, abs=0.2)   # grazes the dayside boundary near the nose
    assert 0 < r.min_dist < 1


def test_open_closed_boundary_between_0815_20_and_0815_30(mapper):
    assert mapper.map(T_0815 + 20).status == TAIL
    assert mapper.map(T_0815 + 30).status == CLOSED


def test_cache_hit_same_second(mapper):
    a = mapper.map(T_0815 + 0.2)
    assert mapper.cached(T_0815 - 0.3) is a


def test_classify_open_synthetic():
    # straight line from inside (x=0) to far outside along +y: crosses the boundary at |y| = rho(0)
    from sciqlop_tracers_mp.core import magnetopause as mp
    line = np.column_stack([np.zeros(200), np.linspace(1.5, 40, 200), np.zeros(200)])
    status, crossing, _, _ = classify(line, 4.08)
    assert status == OPEN
    assert crossing[1] == pytest.approx(mp.radius_at(4.08, 0.0), abs=0.05)
