import os
import pathlib

import numpy as np
import pytest

DATA = pathlib.Path(__file__).parent / "data"
T_0815 = 1759220100.0  # 2025-09-30T08:15:00Z


@pytest.fixture(scope="session")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def fake_position_fetch(satellite, t0, t1):
    """SSCWeb tracers2 GEO 2025-09-30 08:00-08:30 (60 s), saved from speasy."""
    d = np.load(DATA / "ts2_ssc_geo_20250930.npz")
    m = (d["t"] >= t0) & (d["t"] <= t1)
    return (d["t"][m], d["xyz"][m]) if m.any() else None


def fake_omni_fetch(param, t0, t1):
    """OMNI_HRO_1MIN 2025-09-30 07:00-09:30, fill values already NaN."""
    d = np.load(DATA / "omni_20250930.npz")
    t, y = d["t_" + param], d[param]
    m = (t >= t0) & (t <= t1)
    return (t[m], y[m]) if m.any() else None


@pytest.fixture
def mapper():
    from sciqlop_tracers_mp.core.drivers import DriverSource
    from sciqlop_tracers_mp.core.mapping import Mapper
    from sciqlop_tracers_mp.core.position import PositionSource
    return Mapper("tracers2", PositionSource("tracers2", fake_position_fetch), DriverSource(fake_omni_fetch))
