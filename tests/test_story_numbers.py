"""Sanity checks: every headline number in the story must follow from data/."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_data import load_data  # noqa: E402


@pytest.fixture(scope="module")
def data() -> dict:
    return load_data()


@pytest.fixture(scope="module")
def close(data):
    d = {r[0]: r[1] for r in data["nasdaq"]}
    return d.__getitem__


def test_dates_monotonic_and_positive(data):
    dates = [r[0] for r in data["nasdaq"]]
    assert dates == sorted(dates) and len(set(dates)) == len(dates)
    assert all(r[1] > 0 for r in data["nasdaq"])


def test_html_embeds_current_csv(data):
    html = (ROOT / "index.html").read_text()
    m = re.search(r"const DATA = (\{.*?\});\n/\*DATA-END\*/", html, re.S)
    assert m, "data block missing"
    assert json.loads(m.group(1)) == data, "run scripts/build_data.py"


def test_nov5_drop(close):
    pct = close("2026-11-05") / close("2026-11-04") - 1
    pts = close("2026-11-05") - close("2026-11-04")
    assert pct == pytest.approx(-0.0552, abs=5e-4)
    assert pts == pytest.approx(-1421.51, abs=0.01)


def test_nov4_rally(close):
    assert close("2026-11-04") / close("2026-11-03") - 1 == pytest.approx(0.0144, abs=5e-4)


def test_drawdown_is_correction(close):
    dd = close("2026-11-05") / close("2026-10-06") - 1
    assert dd == pytest.approx(-0.119, abs=5e-4)
    assert dd < -0.10


def test_ai_era_ledger(close):
    gpt, peak = close("2022-11-30"), close("2026-10-06")
    gain = peak - gpt
    assert peak / gpt - 1 == pytest.approx(1.41, abs=5e-3)
    assert gain == pytest.approx(16132, abs=1)
    pre = peak - close("2026-11-04")
    day = close("2026-11-04") - close("2026-11-05")
    kept = close("2026-11-05") - gpt
    assert pre / gain == pytest.approx(0.116, abs=1e-3)
    assert day / gain == pytest.approx(0.088, abs=1e-3)
    assert kept / gain == pytest.approx(0.796, abs=1e-3)
    assert (peak - close("2026-11-05")) == pytest.approx(3285, abs=1)
    assert close("2026-11-05") / gpt == pytest.approx(2.12, abs=0.01)


def test_two_day_net(close):
    assert close("2026-11-06") / close("2026-11-04") - 1 == pytest.approx(-0.039, abs=1e-3)


def test_nov5_is_record_points_not_percent(data):
    worst = data["worst"]
    nov5 = next(r for r in worst if r[0] == "2026-11-05")
    assert min(r[3] for r in worst) == nov5[3]
    assert sorted(r[2] for r in worst).index(nov5[2]) >= 5


def test_satire_forecast_is_anchored_and_consistent(data, close):
    fc = data["trail"]["forecast"]
    jf = fc["jotunheimen"]
    assert fc["steps"] == len(jf["forecast"]) == 36  # 5 Nov -> 31 Dec at the target grid spacing
    # anchored: first step stays near the last real close, not the fitted level
    assert abs(jf["forecast"][0] - close("2026-11-05")) < 300
    assert jf["naive_log10_p"] < -100  # the deliberately absurd p-value the satire quotes
    assert jf["r2"] == pytest.approx(data["trail"]["jotunheimen"]["r"] ** 2)
    ends = [t["forecast"][-1] for t in fc["trails"]]
    assert len(fc["trails"]) == 25 and max(ends) - min(ends) > 3000  # the "drivers" disagree
    # the Line called Friday down; Friday was actually up
    assert jf["forecast"][0] < close("2026-11-05") < close("2026-11-06")
