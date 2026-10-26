"""Build the CMS Care Compare hospital quality dashboard (current snapshot).

Usage: python examples/cms_care_compare/build_dashboard.py
Outputs (examples/cms_care_compare/output/): dashboard.html and CSVs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.express as px
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import care_compare_data as cc  # noqa: E402
from snowflake_analytics_agents.dashboard_toolkit import (  # noqa: E402
    DIVERGING_SCALE, bar_extremes, kpi_cards, render_html, style_figure, table_figure,
)

OUT_DIR = Path(__file__).resolve().parent / "output"
RAW_DIR = ROOT / "data" / "care_compare_raw"
US_STATES = 51  # 50 states + DC; territories are not drawn on the map


def state_map(s, column: str, title: str, colorscale: str, label: str) -> go.Figure:
    d = s.dropna(subset=[column])
    fig = go.Figure(go.Choropleth(locations=d["state"], z=d[column], locationmode="USA-states",
                                  colorscale=colorscale, colorbar=dict(title=label),
                                  hovertemplate="%{location}<br>%{z:.2f}<extra></extra>"))
    fig.update_geos(scope="usa")
    return style_figure(fig, title, 520)


def build(df):
    s = cc.state_summary(df)
    s = s[s["hospitals_rated"] >= 5]  # avoid tiny-n states
    ext = s.assign(pct_change=s["mean_stars"] - s["mean_stars"].mean()).sort_values("pct_change", ascending=False)
    dist = px.histogram(df.dropna(subset=["stars"]), x="stars", color="hospital_ownership", nbins=5,
                        barmode="stack")
    scatter = px.scatter(df.dropna(subset=["stars", "readmission_rate"]), x="readmission_rate", y="stars",
                         color="hospital_type", hover_name="facility_name", opacity=0.5)
    ev = bar_extremes(ext, "state", "States vs national mean star rating (difference, stars)", n=8, value="pct_change")
    sections = [
        ("Mean star rating by state", state_map(s, "mean_stars", "Mean hospital overall star rating", "RdYlGn", "stars")),
        ("Share of 4-5 star hospitals", state_map(s, "pct_4_5_star", "% of rated hospitals with 4-5 stars", "Greens", "%")),
        ("Pneumonia readmission rate by state", state_map(s, "mean_readmission_rate",
                                                "Mean pneumonia 30-day readmission rate (%) - lower is better",
                                                "RdYlGn_r", "%")),
        ("State extremes", ev),
        ("Star ratings by ownership", style_figure(dist, "Rated hospitals by star rating and ownership", 450)),
        ("Stars vs readmissions", style_figure(scatter, "Hospital star rating vs readmission rate", 500)),
        ("State table", table_figure(s.round(2), "State summary")),
    ]
    rated = df.dropna(subset=["stars"])
    best, worst = s.sort_values("mean_stars", ascending=False), s.sort_values("mean_stars")
    kpis = kpi_cards([
        ("Hospitals rated", f"{len(rated):,}"),
        ("Mean stars", f"{rated['stars'].mean():.2f}"),
        ("Highest-rated states", ", ".join(f"{r.state} ({r.mean_stars:.2f})" for r in best.head(3).itertuples())),
        ("Lowest-rated states", ", ".join(f"{r.state} ({r.mean_stars:.2f})" for r in worst.head(3).itertuples())),
    ])
    return sections, kpis, s


NOTES = """<ul>
<li><b>Sources:</b> <a href="https://data.cms.gov/provider-data/dataset/xubh-q36u">Hospital General Information</a>,
<a href="https://data.cms.gov/provider-data/dataset/632h-zaca">Unplanned Hospital Visits - Hospital</a>
(<a href="https://data.cms.gov/provider-data/topics/hospitals">Provider Data Catalog</a>);
<a href="https://www.cms.gov/medicare/quality/initiatives/hospital-quality-initiative/overall-hospital-quality-star-rating">star rating methodology</a>.</li>
<li><b>Snapshot, not a time series:</b> Care Compare publishes the current release; this dashboard compares geography and hospital type rather than change over time. Re-run quarterly and archive the CSVs to build a history.</li>
<li>States with fewer than 5 rated hospitals are omitted. State means are unweighted hospital means.</li></ul>"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = cc.load_hospitals(RAW_DIR)
    sections, kpis, s = build(df)
    (OUT_DIR / "dashboard.html").write_text(
        render_html("CMS Care Compare Hospital Quality Dashboard", "Overall star ratings and readmissions by state",
                    sections, kpis, NOTES), encoding="utf-8")
    s.to_csv(OUT_DIR / "state_summary.csv", index=False)
    print(f"Wrote {OUT_DIR / 'dashboard.html'}")


if __name__ == "__main__":
    main()

