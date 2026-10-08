import numpy as np
import pytest

from sciqlop_tracers_mp.core import magnetopause as mp


def test_standoff_decreases_with_pressure():
    assert mp.standoff(1.0) > mp.standoff(4.08) > mp.standoff(10.0)


def test_standoff_value_2025_09_30():
    # Pdyn 4.08 nPa (OMNI 08:14-08:17): 10.03 R_E, same value as the notebook's ray-bisection
    assert mp.standoff(4.08) == pytest.approx(10.03, abs=0.02)


@pytest.mark.parametrize("x", [8.0, 5.0, 0.0, -10.0, -20.0])
def test_cross_section_points_lie_on_boundary(x):
    y, zz = mp.cross_section(4.08, x)
    for k in (0, 45, 90, 135, 180):
        for z in zz[k]:
            assert abs(mp.signed_distance(4.08, (x, y[k], z))) < 2e-3


def test_boundary_is_axisymmetric():
    rho = mp.radius_at(4.08, 0.0)
    for ang in np.radians([0, 37, 90, 151, 270]):
        p = (0.0, rho * np.cos(ang), rho * np.sin(ang))
        assert abs(mp.signed_distance(4.08, p)) < 2e-3


def test_no_cross_section_sunward_of_nose():
    assert mp.cross_section(4.08, 12.0) is None
