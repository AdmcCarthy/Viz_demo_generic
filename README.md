# Forty-Eight Hours: the $2.5 trillion afternoon

A scrollytelling data story about the **5 November 2026 Nasdaq rout**. The
index fell 1,421.51 points (−5.52%), the largest point drop in its history.
The story sets that loss against the AI boom that began with ChatGPT's launch
on 30 November 2022.

**Live page:** https://admccarthy.github.io/viz_demo_generic/ (once GitHub Pages is enabled, see below)

## What's in the story

1. **The 48 hours.** A scroll-driven chart covers the post-midterm relief rally (4 Nov), the rout (5 Nov), and the move into correction territory.
2. **Zoom out.** The same chart widens to show the whole AI era: +141% from ChatGPT day to the 6 Oct 2026 record.
3. **The ledger.** One bar treats the AI-era gain as 100%: 79.6% is kept, 11.6% was lost in the month before, and 8.8% was lost on Thursday alone.
4. **Points vs percent.** An animated re-ranking shows the day is #1 by points but only mid-pack by percent.
5. **The epicentre.** Chip and AI-infrastructure stocks fell 2–3× as far as the index.
6. **Scale.** Proportional squares show the $2.5T loss is bigger than Norway's oil fund. Nvidia's one-day loss is bigger than the whole of Nvidia on ChatGPT day.
7. **Friday's bounce** and a short summary.
8. **Detour: if 2026 were a hike.** The Nasdaq's year-to-date path is matched against real trail elevation profiles. The best stretch is 6 km of the Bob Graham Round (Clough Head → Great Dodd → Watson's Dodd → Stybarrow Dodd, r = 0.958). A bonus straight-line transect in Jotunheimen scores r = 0.971.
9. **The catch.** 500 random-walk "fake indices" get the same search, and 66% of them find a closer match than the real index. That is the look-elsewhere effect, shown with data.

## Repository layout

```
index.html              self-contained page (D3 v7 from cdnjs, data inlined)
data/*.csv              source of truth for every number in the story
data/trail_match.json   output of the trail search (generated)
analysis/               DEM sampling, GPX → profile, shape matching
scripts/build_data.py   injects the CSVs + trail_match.json into index.html
scripts/run_trail_match.py   runs the trail / transect / random-walk search
tests/                  pytest: story numbers + analysis unit tests
```

### Re-running the trail search

```bash
pip install -r requirements.txt
mkdir gpx && cd gpx
for r in thomasturrell/running-routes dwmkerr/gpx-routes hsnetzer/lt-gpx nicholas-fong/Hong-Kong-Trails-GPX-KML; do
  git clone --depth 1 https://github.com/$r ${r/\//_}
done
cd .. && python scripts/run_trail_match.py gpx && python scripts/build_data.py
```

DEM tiles (AWS Terrain Tiles, about 10–25 MB each) are cached in `~/.cache/viz_demo_dem`. The search takes about 20 s.

**Assumptions:**
- Elevations are metres above the EGM96 geoid (≈ mean sea level), sampled bilinearly from 1 arc-second tiles along a 10 m resampled track.
- GPX tracks are split at gaps over 250 m.
- Windows run from 1.5 to 100 km, both directions, with at least 150 m of relief.
- The score is Pearson r on shape only, after block-averaging each window to 200 points.
- The random-walk null uses daily Gaussian steps, sampled on the same dates as the real closes and interpolated the same way.

```bash
python scripts/build_data.py   # after editing data/*.csv
python -m pytest -q            # verify the story's numbers
python -m http.server          # preview at http://localhost:8000
```

## Hosting on GitHub Pages

Go to *Settings → Pages → Build and deployment*, set *Source: Deploy from a branch*, then pick the branch and `/ (root)`.
`.nojekyll` is included so the file is served as-is.

## Data caveats

- 4–5 Nov closes, the 6 Oct record and the stock moves come from news reports (Fox Business, CNBC, Motley Fool, StockTitan, CNN). 6 Nov figures are **intraday**.
- Jan–Sep 2026 month-end closes come from a StatMuse table and are **provisional**. 2022–2025 closes and historical worst days are standard published values, rounded.
- The line chart joins reported closes. It is not a daily series.
- Trail data: thomasturrell/running-routes (Apache-2.0; routes © OpenStreetMap contributors, ODbL), dwmkerr/gpx-routes (MIT), hsnetzer/lt-gpx (CC BY-SA 4.0), nicholas-fong/Hong-Kong-Trails-GPX-KML (CC0). Only the derived profile of the winning stretch is stored here.
- This is a data-visualisation demo, not investment advice.
