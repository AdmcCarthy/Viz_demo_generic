"""Elevation lookup from AWS Terrain Tiles (Mapzen "skadi" SRTM-format tiles).

Tiles are 1°×1° HGT grids (3601×3601 at 1 arc-second), big-endian int16,
metres above the EGM96 geoid. Elevations in this project are therefore
orthometric heights (≈ above mean sea level), not ellipsoidal.
"""
from __future__ import annotations

import gzip
import math
import urllib.request
from functools import lru_cache
from pathlib import Path

import numpy as np

TILE_URL = "https://s3.amazonaws.com/elevation-tiles-prod/skadi/{ns}{lat:02d}/{ns}{lat:02d}{ew}{lon:03d}.hgt.gz"
CACHE = Path.home() / ".cache" / "viz_demo_dem"
VOID = -32768


def tile_name(lat_floor: int, lon_floor: int) -> tuple[str, str]:
    ns = "N" if lat_floor >= 0 else "S"
    ew = "E" if lon_floor >= 0 else "W"
    url = TILE_URL.format(ns=ns, lat=abs(lat_floor), ew=ew, lon=abs(lon_floor))
    return url, url.rsplit("/", 1)[1]


@lru_cache(maxsize=32)
def load_tile(lat_floor: int, lon_floor: int) -> np.ndarray:
    """Return the tile as float32 array (row 0 = north edge); voids as NaN."""
    url, name = tile_name(lat_floor, lon_floor)
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / name
    if not path.exists():
        tmp = path.with_suffix(".part")
        urllib.request.urlretrieve(url, tmp)
        tmp.rename(path)
    raw = gzip.decompress(path.read_bytes())
    n = math.isqrt(len(raw) // 2)
    if n * n * 2 != len(raw):
        raise ValueError(f"{name}: not a square HGT grid")
    a = np.frombuffer(raw, ">i2").reshape(n, n).astype(np.float32)
    a[a == VOID] = np.nan
    return a


def sample(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Bilinear elevation (m, EGM96) at WGS84 lat/lon arrays."""
    lat = np.asarray(lat, float)
    lon = np.asarray(lon, float)
    if lat.shape != lon.shape:
        raise ValueError("lat/lon shape mismatch")
    if np.any(np.abs(lat) > 90) or np.any(np.abs(lon) > 180):
        raise ValueError("coordinates out of range")
    out = np.full(lat.shape, np.nan)
    tf_lat, tf_lon = np.floor(lat).astype(int), np.floor(lon).astype(int)
    for la, lo in set(zip(tf_lat.ravel().tolist(), tf_lon.ravel().tolist())):
        m = (tf_lat == la) & (tf_lon == lo)
        t = load_tile(la, lo)
        n = t.shape[0] - 1
        r = (la + 1 - lat[m]) * n
        c = (lon[m] - lo) * n
        r0 = np.clip(np.floor(r).astype(int), 0, n - 1)
        c0 = np.clip(np.floor(c).astype(int), 0, n - 1)
        fr, fc = r - r0, c - c0
        out[m] = (t[r0, c0] * (1 - fr) * (1 - fc) + t[r0, c0 + 1] * (1 - fr) * fc
                  + t[r0 + 1, c0] * fr * (1 - fc) + t[r0 + 1, c0 + 1] * fr * fc)
    return out
