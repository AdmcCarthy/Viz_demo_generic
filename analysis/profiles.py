"""Trail geometry → uniformly resampled elevation profiles."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import gpxpy
import numpy as np

from . import dem

EARTH_R = 6_371_008.8  # mean Earth radius, m


def haversine(lat1, lon1, lat2, lon2) -> np.ndarray:
    """Great-circle distance in metres between point arrays (degrees)."""
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = p2 - p1, np.radians(np.asarray(lon2) - np.asarray(lon1))
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * EARTH_R * np.arcsin(np.sqrt(a))


@dataclass
class Profile:
    """Elevation (m) on a uniform along-track distance grid."""

    name: str
    source: str
    dx: float                 # grid spacing, m
    elev: np.ndarray          # m above EGM96 geoid
    lat: np.ndarray
    lon: np.ndarray

    @property
    def length_m(self) -> float:
        return self.dx * (len(self.elev) - 1)


def read_gpx_segments(path: Path, max_gap_m: float = 250.0, min_len_m: float = 1000.0) -> list[tuple[np.ndarray, np.ndarray]]:
    """Continuous lat/lon pieces of a GPX file.

    Track segments are concatenated, then split wherever consecutive points
    are more than ``max_gap_m`` apart, so side trails or missing stretches
    never get bridged by a fake straight line. Pieces shorter than
    ``min_len_m`` are dropped.
    """
    with open(path, encoding="utf-8", errors="replace") as fh:
        g = gpxpy.parse(fh)
    segs = [s.points for t in g.tracks for s in t.segments] or [r.points for r in g.routes]
    out = []
    for pts in segs:
        if len(pts) < 2:
            continue
        lat = np.array([p.latitude for p in pts])
        lon = np.array([p.longitude for p in pts])
        gap = haversine(lat[:-1], lon[:-1], lat[1:], lon[1:])
        cuts = np.flatnonzero(gap > max_gap_m) + 1
        for la, lo in zip(np.split(lat, cuts), np.split(lon, cuts)):
            if len(la) > 1 and haversine(la[:-1], lo[:-1], la[1:], lo[1:]).sum() >= min_len_m:
                out.append((la, lo))
    if not out:
        raise ValueError(f"{path.name}: no usable segments")
    return out


def profile_from_latlon(lat, lon, name: str, source: str, dx: float = 10.0) -> Profile:
    """Resample a polyline to spacing ``dx`` and sample elevations from the DEM.

    Zero-length steps (duplicate points) are dropped so distance is strictly
    increasing before interpolation.
    """
    lat, lon = np.asarray(lat, float), np.asarray(lon, float)
    step = haversine(lat[:-1], lon[:-1], lat[1:], lon[1:])
    keep = np.r_[True, step > 0.01]
    lat, lon = lat[keep], lon[keep]
    s = np.r_[0.0, np.cumsum(haversine(lat[:-1], lon[:-1], lat[1:], lon[1:]))]
    if s[-1] < 10 * dx:
        raise ValueError(f"{name}: track too short ({s[-1]:.0f} m)")
    grid = np.arange(0.0, s[-1], dx)
    glat, glon = np.interp(grid, s, lat), np.interp(grid, s, lon)
    elev = dem.sample(glat, glon)
    if np.isnan(elev).mean() > 0.01:
        raise ValueError(f"{name}: >1% DEM voids")
    if np.isnan(elev).any():  # fill isolated voids along track
        ok = ~np.isnan(elev)
        elev = np.interp(grid, grid[ok], elev[ok])
    return Profile(name, source, dx, elev, glat, glon)


def windowed(elev: np.ndarray, win: int, n_out: int, step: int) -> tuple[np.ndarray, np.ndarray]:
    """All windows of ``win`` samples (stride ``step``), block-averaged to ``n_out`` points.

    Returns (starts, profiles[n_windows, n_out]). Block averaging acts as an
    anti-alias filter so a 40 km window isn't sampled from 10 m DEM noise.
    """
    if win > len(elev):
        return np.empty(0, int), np.empty((0, n_out))
    starts = np.arange(0, len(elev) - win + 1, step)
    cs = np.r_[0.0, np.cumsum(elev)]
    edges = np.linspace(0, win, n_out + 1).round().astype(int)
    lo = starts[:, None] + edges[None, :-1]
    hi = starts[:, None] + np.maximum(edges[None, 1:], edges[None, :-1] + 1)
    return starts, (cs[hi] - cs[lo]) / (hi - lo)
