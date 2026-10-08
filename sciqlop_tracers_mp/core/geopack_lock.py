"""geopack keeps the dipole tilt and IGRF coefficients in module globals set by `recalc`.

Every recalc + trace/convert sequence in this plugin runs under this lock. Code outside the plugin
(e.g. a notebook in the same kernel) does not take it: avoid tracing in a notebook while a map is computing.
"""
from __future__ import annotations

import threading

GEOPACK_LOCK = threading.Lock()
