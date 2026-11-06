"""Find the hiking-trail stretch whose elevation profile best matches the 2026 Nasdaq path.

Usage::

    python scripts/run_trail_match.py /path/to/gpx_corpus

The corpus is a folder of cloned GPX repositories (see TRAILS below). DEM
tiles are downloaded once to ~/.cache/viz_demo_dem. Writes data/trail_match.json.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis import dem  # noqa: E402
from analysis.match import pearson_rows, target_series  # noqa: E402
from analysis.profiles import Profile, profile_from_latlon, read_gpx_segments, windowed  # noqa: E402

N = 200                     # points per shape
START, END = "2025-12-31", "2026-11-05"
DX = 10.0                   # m, along-track resampling
MIN_RELIEF = 150.0          # m, a "hike" must actually climb
WIN_KM = [1.5, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60, 80, 100]
N_NULL = 500
SEED = 20261105

# (relative path, display name, region, source repo, licence)
TRAILS = [
    ("thomasturrell_running-routes/src/fell/bob-graham-round/bob-graham-round.gpx", "Bob Graham Round", "Lake District, England", "thomasturrell/running-routes", "Apache-2.0; route © OpenStreetMap contributors (ODbL)"),
    ("thomasturrell_running-routes/src/fell/paddy-buckley-round/paddy-buckley-round.gpx", "Paddy Buckley Round", "Eryri (Snowdonia), Wales", "thomasturrell/running-routes", "Apache-2.0; route © OpenStreetMap contributors (ODbL)"),
    ("thomasturrell_running-routes/src/fell/ramsay-round/ramsay-round.gpx", "Ramsay Round", "Lochaber, Scotland", "thomasturrell/running-routes", "Apache-2.0; route © OpenStreetMap contributors (ODbL)"),
    ("thomasturrell_running-routes/src/fell/wicklow-round/wicklow-round.gpx", "Wicklow Round", "Wicklow Mountains, Ireland", "thomasturrell/running-routes", "Apache-2.0; route © OpenStreetMap contributors (ODbL)"),
    ("thomasturrell_running-routes/src/fell/allermuir-hill-race/allermuir-hill-race.gpx", "Allermuir Hill Race", "Pentland Hills, Scotland", "thomasturrell/running-routes", "Apache-2.0; route © OpenStreetMap contributors (ODbL)"),
    ("dwmkerr_gpx-routes/routes/00-sorting-importing/01-planning/Ambleside to Grassmere Coffin Road.gpx", "Coffin Route, Ambleside–Grasmere", "Lake District, England", "dwmkerr/gpx-routes", "MIT"),
    ("dwmkerr_gpx-routes/routes/00-sorting-importing/02-testing/Howgills-Winder&amp;Crook6K_400m.gpx", "Howgills: Winder & Crook", "Howgill Fells, England", "dwmkerr/gpx-routes", "MIT"),
    ("dwmkerr_gpx-routes/routes/00-sorting-importing/OldManofConiston,BrimFell,SwirlHow.gpx", "Old Man of Coniston, Brim Fell & Swirl How", "Lake District, England", "dwmkerr/gpx-routes", "MIT"),
    ("dwmkerr_gpx-routes/routes/00-sorting-importing/OldManofConiston,GoatsWater.gpx", "Old Man of Coniston via Goat's Water", "Lake District, England", "dwmkerr/gpx-routes", "MIT"),
    ("dwmkerr_gpx-routes/routes/00-sorting-importing/RydalWaterRound10K.gpx", "Rydal Water Round", "Lake District, England", "dwmkerr/gpx-routes", "MIT"),
    ("dwmkerr_gpx-routes/routes/00-sorting-importing/scrambles/scramble-whitegill,rake,langdale-pikes.gpx", "Langdale Pikes via Whitegill", "Lake District, England", "dwmkerr/gpx-routes", "MIT"),
    ("dwmkerr_gpx-routes/routes/01-working/02-SeathwaiteTarnScrambles-garmin.gpx", "Seathwaite Tarn scrambles", "Lake District, England", "dwmkerr/gpx-routes", "MIT"),
    ("dwmkerr_gpx-routes/routes/01-working/GummersHoweandBirchFellWoods.gpx", "Gummer's How & Birch Fell", "Lake District, England", "dwmkerr/gpx-routes", "MIT"),
    ("hsnetzer_lt-gpx/B.gpx", "Long Trail (central)", "Green Mountains, Vermont", "hsnetzer/lt-gpx", "CC BY-SA 4.0"),
    ("hsnetzer_lt-gpx/C.gpx", "Long Trail (north)", "Green Mountains, Vermont", "hsnetzer/lt-gpx", "CC BY-SA 4.0"),
    ("nicholas-fong_Hong-Kong-Trails-GPX-KML/HongKong-Trail/GPX-Track/Hong-Kong-Trail-track.gpx", "Hong Kong Trail", "Hong Kong Island", "nicholas-fong/Hong-Kong-Trails-GPX-KML", "CC0-1.0"),
    ("nicholas-fong_Hong-Kong-Trails-GPX-KML/Lantau-Trail/GPX-Track/Lantau-Trail-track.gpx", "Lantau Trail", "Lantau Island, Hong Kong", "nicholas-fong/Hong-Kong-Trails-GPX-KML", "CC0-1.0"),
    ("nicholas-fong_Hong-Kong-Trails-GPX-KML/MacLehose-Trail/GPX-Track/MacLehose-Trail-track.gpx", "MacLehose Trail", "New Territories, Hong Kong", "nicholas-fong/Hong-Kong-Trails-GPX-KML", "CC0-1.0"),
    ("nicholas-fong_Hong-Kong-Trails-GPX-KML/Wilson-Trail/GPX-Track/Wilson-Trail-Hong-Kong-track.gpx", "Wilson Trail (Island)", "Hong Kong Island", "nicholas-fong/Hong-Kong-Trails-GPX-KML", "CC0-1.0"),
    ("nicholas-fong_Hong-Kong-Trails-GPX-KML/Wilson-Trail/GPX-Track/Wilson-Trail-Kowloon-track.gpx", "Wilson Trail (Kowloon & NT)", "Hong Kong", "nicholas-fong/Hong-Kong-Trails-GPX-KML", "CC0-1.0"),
]


def null_targets(t_grid, anchors_t, rng) -> np.ndarray:
    """Random-walk 'fake indices' sampled and interpolated exactly like the real one.

    Daily Gaussian log-returns are sampled at the same reported-close dates
    then linearly interpolated onto the same grid, so they share the target's
    smoothness and the comparison against the real series is fair.
    """
    days = np.arange(int((anchors_t[-1] - anchors_t[0]) / np.timedelta64(1, "D")) + 1)
    walks = np.cumsum(rng.standard_normal((N_NULL, len(days))) * 0.015, axis=1)
    idx = ((anchors_t - anchors_t[0]) / np.timedelta64(1, "D")).astype(int)
    tg = (t_grid.values - anchors_t[0]) / np.timedelta64(1, "D")
    return np.array([np.interp(tg, idx, w[idx]) for w in walks])


def nearby_waypoints(gpx_path: Path, la, lo, e, max_m: float = 200.0) -> list[dict]:
    """Named waypoints (from a sibling ``*-waypoints.gpx``) lying within ``max_m`` of the window."""
    wp_path = gpx_path.with_name(gpx_path.stem + "-waypoints.gpx")
    if not wp_path.exists():
        return []
    import gpxpy
    from analysis.profiles import haversine
    with open(wp_path, encoding="utf-8", errors="replace") as fh:
        wps = gpxpy.parse(fh).waypoints
    out = []
    for w in wps:
        d = haversine(la, lo, w.latitude, w.longitude)
        i = int(np.argmin(d))
        if d[i] <= max_m:
            out.append({"name": w.name, "km": round(i * DX / 1000, 3), "elev_m": round(float(e[i]), 1),
                        "map_ele_m": w.elevation, "offset_m": round(float(d[i]))})
    return sorted(out, key=lambda x: x["km"])


def search(profiles: list[Profile], targets: np.ndarray):
    """Best r per target over every window, length and direction. Also returns all real-target rows."""
    best = np.full(len(targets), -np.inf)
    rows = []
    rev = targets[:, ::-1]
    for pi, p in enumerate(profiles):
        for km in WIN_KM:
            win = int(round(km * 1000 / DX))
            if win > len(p.elev):
                continue
            step = max(1, win // 50)
            starts, w = windowed(p.elev, win, N, step)
            relief = w.max(1) - w.min(1)
            ok = relief >= MIN_RELIEF
            if not ok.any():
                continue
            starts, w = starts[ok], w[ok]
            r_f = pearson_rows(w, targets)       # walking forwards
            r_b = pearson_rows(w, rev)           # walking the other way
            best = np.maximum(best, np.nanmax(np.maximum(r_f, r_b), axis=0))
            for j in range(len(starts)):
                rows.append((pi, km, int(starts[j]), win, float(r_f[j, 0]), float(r_b[j, 0])))
    return best, rows


def transects_jotunheimen(target: np.ndarray, n_dense: int = 600):
    """Straight-line transects in DEM tile N61E008 (core Jotunheimen)."""
    best = None
    count = 0
    lat0s = np.arange(61.05, 61.96, 0.02)
    lon0s = np.arange(8.05, 8.96, 0.04)
    LA, LO = np.meshgrid(lat0s, lon0s, indexing="ij")
    LA, LO = LA.ravel(), LO.ravel()
    frac = np.linspace(0, 1, n_dense)
    for km in (6, 10, 15, 20):
        for az in range(0, 180, 10):
            a = np.radians(az)
            dlat = km * 1000 * np.cos(a) / 111_195.0
            dlon = km * 1000 * np.sin(a) / (111_195.0 * np.cos(np.radians(LA)))
            la1, lo1 = LA + dlat, LO + dlon
            ok = (la1 > 61.005) & (la1 < 61.995) & (lo1 > 8.005) & (lo1 < 8.995)
            if not ok.any():
                continue
            la = LA[ok, None] + frac[None] * dlat
            lo = LO[ok, None] + frac[None] * dlon[ok, None]
            e = dem.sample(la, lo)
            e = e.reshape(len(e), N, -1).mean(2)
            relief = e.max(1) - e.min(1)
            r = np.maximum(pearson_rows(e, target[None])[:, 0], pearson_rows(e, target[None, ::-1])[:, 0])
            r[relief < MIN_RELIEF] = -1
            count += int(ok.sum())
            j = int(np.nanargmax(r))
            if best is None or r[j] > best["r"]:
                fwd = pearson_rows(e[j:j + 1], target[None])[0, 0] >= pearson_rows(e[j:j + 1], target[None, ::-1])[0, 0]
                prof = e[j] if fwd else e[j][::-1]
                p0 = (float(LA[ok][j]), float(LO[ok][j]))
                p1 = (float(la1[ok][j]), float(lo1[ok][j]))
                best = {"r": float(r[j]), "km": km, "azimuth_deg": az if fwd else (az + 180) % 360,
                        "start": p0 if fwd else p1, "end": p1 if fwd else p0, "elev": prof.round(1).tolist()}
    best["n_transects"] = count * 2
    return best


def main(corpus: Path) -> None:
    t0 = time.time()
    t_grid, target = target_series(ROOT / "data" / "nasdaq_closes.csv", START, END, N)
    import pandas as pd
    df = pd.read_csv(ROOT / "data" / "nasdaq_closes.csv", parse_dates=["date"])
    anchors = df[(df.kind != "intraday") & (df.date >= START) & (df.date <= END)].date.values
    rng = np.random.default_rng(SEED)
    nulls = null_targets(t_grid, anchors, rng)

    profiles, meta = [], []
    for rel, name, region, repo, lic in TRAILS:
        segs = read_gpx_segments(corpus / rel)
        for k, (lat, lon) in enumerate(segs):
            p = profile_from_latlon(lat, lon, name, repo, DX)
            profiles.append(p)
            meta.append({"name": name, "region": region, "repo": repo, "licence": lic, "file": rel.split("/", 1)[1],
                         "segment": k, "length_km": round(p.length_m / 1000, 1)})
        tot = sum(m["length_km"] for m in meta if m["name"] == name)
        print(f"{name:45s} {len(segs):3d} seg {tot:7.1f} km")

    targets = np.vstack([target, nulls])
    best, rows = search(profiles, targets)
    real_best, null_best = best[0], best[1:]
    rows.sort(key=lambda r: -max(r[4], r[5]))

    # best window per trail
    per_trail, seen = [], set()
    for pi, km, s, win, rf, rb in rows:
        if meta[pi]["name"] in seen:
            continue
        seen.add(meta[pi]["name"])
        per_trail.append({"trail": meta[pi]["name"], "region": meta[pi]["region"], "window_km": km, "r": round(max(rf, rb), 4)})
    pi, km, s, win, rf, rb = rows[0]
    p = profiles[pi]
    fwd = rf >= rb
    seg = slice(s, s + win)
    e, la, lo = p.elev[seg], p.lat[seg], p.lon[seg]
    if not fwd:
        e, la, lo = e[::-1], la[::-1], lo[::-1]
    k = max(1, len(e) // 400)  # thin for the web page
    winner = {
        **meta[pi], "r": round(max(rf, rb), 4), "window_km": km, "direction": "as recorded" if fwd else "reversed",
        "start_km": round(s * DX / 1000, 2), "dist_km": (np.arange(0, len(e), k) * DX / 1000).round(3).tolist(),
        "elev_m": e[::k].round(1).tolist(), "lat": la[::k].round(5).tolist(), "lon": lo[::k].round(5).tolist(),
    }
    winner["waypoints"] = nearby_waypoints(corpus / TRAILS[[t[1] for t in TRAILS].index(winner["name"])][0], la, lo, e)
    jot = transects_jotunheimen(target)
    out = {
        "target": {"start": START, "end": END, "n": N, "values": target.round(2).tolist()},
        "winner": winner,
        "per_trail": per_trail,
        "n_windows": len(rows) * 2,
        "n_trails": len(TRAILS),
        "total_km": round(sum(m["length_km"] for m in meta), 0),
        "null": {"n": N_NULL, "best_r": np.sort(null_best).round(4).tolist(),
                 "share_beating_real": float((null_best >= real_best).mean())},
        "jotunheimen": jot,
        "dem": "AWS Terrain Tiles (Mapzen skadi, 1 arc-second); heights in m above EGM96 geoid",
    }
    (ROOT / "data" / "trail_match.json").write_text(json.dumps(out))
    print(f"\nwinner: {winner['name']} window {km} km from {winner['start_km']} km, r={winner['r']}")
    print("top trails:", per_trail[:6])
    print(f"windows tested: {out['n_windows']:,}; null median best r={np.median(null_best):.3f}, share ≥ real: {out['null']['share_beating_real']:.2%}")
    print(f"Jotunheimen: r={jot['r']:.3f} {jot['km']} km az {jot['azimuth_deg']} from {jot['start']} to {jot['end']} ({jot['n_transects']:,} transects)")
    print("waypoints:", winner["waypoints"])
    print(f"done in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
