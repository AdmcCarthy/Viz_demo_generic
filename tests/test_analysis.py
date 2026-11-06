"""Unit tests for the trail-matching pipeline (offline: DEM tiles are faked)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analysis import dem
from analysis.match import pearson_rows, target_series
from analysis.profiles import haversine, profile_from_latlon, read_gpx_segments, windowed

ROOT = __import__("pathlib").Path(__file__).resolve().parents[1]


def test_haversine_one_degree_latitude():
    assert haversine(60.0, 5.0, 61.0, 5.0) == pytest.approx(111_195, rel=1e-3)


def test_windowed_block_average():
    elev = np.arange(100.0)
    starts, w = windowed(elev, win=20, n_out=4, step=10)
    assert starts.tolist() == list(range(0, 81, 10))
    np.testing.assert_allclose(w[0], [2, 7, 12, 17])  # means of 0-4, 5-9, ...
    assert windowed(elev, 200, 4, 1)[1].shape == (0, 4)


def test_pearson_is_shape_only():
    x = np.sin(np.linspace(0, 6, 50))
    r = pearson_rows(np.vstack([3 * x + 100, -x]), x[None])
    np.testing.assert_allclose(r[:, 0], [1, -1])


def test_target_series_hits_anchors():
    t, v = target_series(ROOT / "data" / "nasdaq_closes.csv", "2025-12-31", "2026-11-05", 200)
    assert len(t) == 200 and v[0] == pytest.approx(23242.0) and v[-1] == pytest.approx(24315.0)
    assert v.max() == pytest.approx(27599.79, abs=60)  # Oct-6 record, softened by grid spacing
    assert np.ptp(v) > 5000, "series must not be flat (datetime unit bug)"


def test_dem_bilinear_orientation(monkeypatch):
    n = 11  # tiny fake tile: elevation = 100*row + col, row 0 = north edge
    tile = (100 * np.arange(n)[:, None] + np.arange(n)[None, :]).astype(np.float32)
    monkeypatch.setattr(dem, "load_tile", lambda la, lo: tile)
    # north-west corner -> row 0 col 0; half a cell east of it -> 0.5
    # (62.0 itself belongs to the next tile north, so stay just inside)
    out = dem.sample(np.array([61.99999, 61.99999, 61.0]), np.array([8.0, 8.05, 8.0]))
    np.testing.assert_allclose(out, [0.0, 0.5, 1000.0], atol=0.02)


def test_segments_split_on_gaps(tmp_path):
    pts = "".join(f'<trkpt lat="{60 + i * 1e-3:.6f}" lon="5.0"/>' for i in range(20))
    far = "".join(f'<trkpt lat="{61 + i * 1e-3:.6f}" lon="5.0"/>' for i in range(20))
    f = tmp_path / "t.gpx"
    f.write_text(f'<gpx version="1.1" creator="t"><trk><trkseg>{pts}{far}</trkseg></trk></gpx>')
    segs = read_gpx_segments(f, max_gap_m=250, min_len_m=1000)
    assert len(segs) == 2 and all(len(s[0]) == 20 for s in segs)


def test_profile_spacing(monkeypatch):
    monkeypatch.setattr(dem, "sample", lambda la, lo: np.full(np.shape(la), 500.0))
    lat = np.linspace(60, 60.01, 30)
    p = profile_from_latlon(lat, np.full(30, 5.0), "x", "y", dx=10)
    assert p.length_m == pytest.approx(1110, abs=15) and np.all(p.elev == 500)
