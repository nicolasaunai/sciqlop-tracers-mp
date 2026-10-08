# sciqlop-tracers-mp

SciQLop plugin: where the magnetic field line through TRACERS-1 or TRACERS-2 meets the T96 magnetopause.

## Use

1. In a plot panel, click **MP ▾** (panel header) and pick TRACERS-1 or TRACERS-2
   (the satellite whose products are on the panel is listed first).
2. A black bar spans all plots of the panel and a dock opens beside it.
3. Drag the bar. After ~0.25 s the field line at that time is traced (IGRF + T96, ~1-4 s) and the dock shows:
   - the magnetopause seen from the Sun (Y-Z GSM, dusk on the left), cross-sections at X = 8, 5, 0, -10, -20 R_E;
   - the point on the magnetopause: **filled** if the line crosses it, **hollow** = closest-approach point
     for lines that stay inside (closed lines, lobe/tail lines), labelled with time and X;
   - the spacecraft MLat/MLT and the OMNI inputs; a warning when they are outside the T96 range.
4. **Pin** keeps the current point (own colour, table row with X/Y/Z); × removes a pin, **Clear** removes all.
   Pins are not saved when the dock closes.

## Physics

- Position: SSCWeb `tracers1` / `tracers2`, GEO, 60 s samples, cubic spline (within 0.4 km of the 1 s
  `TS2_L2_MAG` GEO position), GEO -> GSM with geopack.
- Inputs: `OMNI_HRO_1MIN` Pressure, SYM_H (as Dst), BY_GSM, BZ_GSM, interpolated at t (error if no valid
  sample within 30 min).
- Field: IGRF (geopack, IGRF-14) + T96. Traced away from the Earth to r = 60 R_E.
- Magnetopause: the T96 boundary (`t96_mgnp`), the one the field model is built with. Axisymmetric about X.
- T96 has no reconnection topology: lobe lines stay inside the boundary to 60 R_E. The plotted point is a
  geometric mapping, not a reconnection site.

## Develop

```
cd sciqlop_tracers_mp
../.venv-b/bin/python -m pytest -q        # offline, fixtures for 2025-09-30
```

Design notes: `docs/design.md`.
