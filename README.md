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

## Repository layout

```
index.html              self-contained page (D3 v7 from cdnjs, data inlined)
data/*.csv              source of truth for every number in the story
scripts/build_data.py   injects the CSVs into index.html
tests/                  pytest checks that each headline figure follows from data/
```

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
- This is a data-visualisation demo, not investment advice.
