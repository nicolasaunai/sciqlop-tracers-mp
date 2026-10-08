"""Plain data types shared by core and UI (Qt-free)."""
from __future__ import annotations

from dataclasses import dataclass, field

SATELLITES = {"tracers1": "TRACERS-1", "tracers2": "TRACERS-2"}  # SSCWeb id -> label

# Field-line topology relative to the T96 magnetopause
OPEN = "open"        # leaves the model magnetopause: `crossing` is set
TAIL = "tail"        # stays inside the magnetopause up to RLIM (lobe / tail line)
CLOSED = "closed"    # comes back to the Earth without leaving the magnetopause
UNRESOLVED = "unresolved"  # tracing stopped (step limit) before any of the above


class MPMapError(Exception):
    """Base error: shown in the dock status line."""


class NoPositionError(MPMapError):
    pass


class NoDriversError(MPMapError):
    pass


@dataclass(frozen=True)
class Drivers:
    """T96 inputs at one time, from OMNI_HRO_1MIN (SYM-H used as Dst)."""
    pdyn: float   # nPa
    symh: float   # nT
    by: float     # nT, GSM
    bz: float     # nT, GSM
    warnings: tuple[str, ...] = ()  # inputs outside the T96 fitted range

    @property
    def parmod(self) -> list[float]:
        return [self.pdyn, self.symh, self.by, self.bz, 0, 0, 0, 0, 0, 0]


@dataclass(frozen=True)
class MapResult:
    t: float                                    # epoch seconds (UTC)
    satellite: str                              # SSCWeb id
    status: str                                 # OPEN / TAIL / CLOSED / UNRESOLVED
    sc_gsm: tuple[float, float, float]          # spacecraft, R_E
    mlat: float                                 # SM magnetic latitude, deg
    mlt: float                                  # magnetic local time, h
    drivers: Drivers
    crossing: tuple[float, float, float] | None = None   # magnetopause point, GSM R_E (OPEN only)
    min_dist: float | None = None               # closest approach to the boundary, R_E (non-OPEN)
    nearest: tuple[float, float, float] | None = None    # boundary point closest to the line (non-OPEN)

    @property
    def mp_point(self) -> tuple[float, float, float] | None:
        """Point drawn on the magnetopause map: the crossing if any, else the closest-approach point."""
        return self.crossing if self.crossing is not None else self.nearest


@dataclass
class Pin:
    id: int
    result: MapResult
    color: str
    meta: dict = field(default_factory=dict)
