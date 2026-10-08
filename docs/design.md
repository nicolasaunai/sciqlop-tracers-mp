# sciqlop-tracers-mp — design (v0.1.0, 2026-10-08)

## Decisions (agreed with N. Aunai)

- TRACERS only (TS1, TS2). Field and magnetopause model: T96 only.
- One live bar per dock, spanning every plot of the panel, plus **pins** (frozen results).
- Dock beside the panel showing the magnetopause seen from the Sun (Y-Z GSM) at several X.

## Decisions taken during implementation

- **Position from SSCWeb, not from `TS2_L2_MAG_BDC-16SPS`.** There is no TS1 MAG dataset on CDAWeb. In
  addition, the MAG `ts2_l2_mag_1sps_gei2000_pos`/`_vel` are rotated by about -51° about Z relative to true
  GEI (2025-09-30 08:14-08:17). Evidence: IGRF evaluated at the MAG/SSCWeb GEO position is within 0.3° of the
  measured `ts2_l2_mag_16sps_gei2000_b`; evaluated at `gei2000_pos`, it is 12.6° off. `geo_pos` and SSCWeb agree
  to 0.4 km. To report to the TRACERS MAG team.
- **Closest-approach point for lines that do not cross the boundary.** With T96, cusp-region lines on
  2025-09-30 are either lobe lines (inside the boundary to 60 R_E) or closed. Neither crosses the
  magnetopause; both graze it (0.3-1.2 R_E). Without this point the map would be empty. It is drawn hollow;
  crossings are drawn filled.
- Circles for the T96 boundary are redrawn when Pdyn changes by more than 1 %. Each pin keeps the point
  computed with its own Pdyn.

## Errors and edge cases

| case | behaviour |
|---|---|
| no SSCWeb position / outside coverage | red status line, live point cleared, pins kept |
| no OMNI sample within 30 min | same |
| inputs outside T96 range | computed anyway, ⚠ and orange inputs line, details in tooltip |
| bar dragged quickly | 250 ms debounce, stale results dropped (generation counter) |
| time already computed (same second) | shown at once from the cache (512 entries) |
| dock × | bar removed, worker stopped |
| panel closed | worker stopped, dock closed, the dying panel's bar not touched |
| geopack global state | all recalc+trace under one lock; notebook code in the same kernel does not take it |

## Structure

- `core/` (Qt-free): `position.py`, `drivers.py`, `magnetopause.py`, `mapping.py`, `geopack_lock.py`.
- `model.py`: `Drivers`, `MapResult`, `Pin`, errors.
- `ui/bar.py`: the only user of SciQLopPlots `MultiPlotsVerticalLine` (private `panel._impl`).
- `ui/dock.py`: the only user of the QtAds dock manager (adapted from sciqlop_vdf).
- `ui/attach.py`: "MP ▾" button in `PanelContainer.chrome_row` (private, as in sciqlop_vdf).
- `ui/viewer.py`, `ui/widget.py`, `ui/controller.py`, `ui/format.py`.

## SciQLopPlots quirks relied on (viewer.py)

- XY axes cannot be reversed: horizontal coordinate is -Y with relabelled ticks.
- Line graphs draw y(x): circles as two halves.
- Marker shape/size via graph components (private `_impl`).
- `Text` renders only with an explicit `coordinate_system`.

## Tests

`pytest` offline (31 tests): Qt-free boundaries, magnetopause geometry, sources with saved 2025-09-30
fixtures, mapping results (lobe 08:14, closed 08:16, transition between 08:15:20 and 08:15:30), GEO->GSM vs
spacepy (< 2 km), formatting, dock lifecycle, widget pins.

## Not in v0.1

Saving pins, export, drawing the field lines, other missions, T01/TS04.
