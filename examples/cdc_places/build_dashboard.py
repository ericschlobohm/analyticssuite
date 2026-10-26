"""Build the CDC PLACES county chronic-disease dashboard (2019-2023).

Usage: python examples/cdc_places/build_dashboard.py
Outputs (examples/cdc_places/output/): dashboard.html and CSVs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import places_data as pl  # noqa: E402
from snowflake_analytics_agents.dashboard_toolkit import (  # noqa: E402
    DIVERGING_SCALE, bar_extremes, first_last_change, indexed_lines, kpi_cards, render_html,
    style_figure, table_figure,
)

OUT_DIR = Path(__file__).resolve().parent / "output"
RAW_DIR = ROOT / "data" / "cdc_places_raw"


def map_dropdown(states: dict[str, pd.DataFrame]) -> go.Figure:
    """State map of percentage-point change, one trace per measure selectable by dropdown."""
    ids = list(states)
    fig = go.Figure()
    for i, m in enumerate(ids):
        s = states[m]
        lim = max(float(s["abs_change"].abs().max()), 0.1)
        fig.add_trace(go.Choropleth(
            locations=s["state"], z=s["abs_change"], locationmode="USA-states", colorscale=DIVERGING_SCALE,
            zmin=-lim, zmax=lim, visible=(i == 0), colorbar=dict(title="pp change"),
            hovertemplate="%{location}<br>%{z:+.2f} pp<extra></extra>"))
    buttons = [dict(label=pl.MEASURES[m], method="update", args=[{"visible": [j == i for j in range(len(ids))]}])
               for i, m in enumerate(ids)]
    fig.update_layout(updatemenus=[dict(buttons=buttons, x=0.0, y=1.15, xanchor="left")])
    fig.update_geos(scope="usa")
    return style_figure(fig, "Change in age-adjusted prevalence by state (percentage points, population-weighted)", 560)


def build(df: pd.DataFrame) -> tuple[list[tuple[str, go.Figure]], str, dict[str, pd.DataFrame]]:
    first, last = int(df["year"].min()), int(df["year"].max())
    summaries, yearly = {}, {}
    for m in pl.MEASURES:
        yearly[m] = pl.state_yearly(df, m)
        summaries[m] = first_last_change(yearly[m], "value").rename(columns={"pct_change": "pct"})
        summaries[m]["pct_change"] = summaries[m]["abs_change"]  # rank/plot in percentage points
    diab = summaries["DIABETES"]
    nat = df.assign(w=df["value"] * df["population"]).groupby(["measureid", "year"], as_index=False).agg(
        w=("w", "sum"), pop=("population", "sum"))
    nat["value"] = nat["w"] / nat["pop"]
    nat["measure"] = nat["measureid"].map(pl.MEASURES)
    cc = pl.county_change(df, "DIABETES")
    cc["pct_change"] = cc["abs_change"]
    cc_ext = pd.concat([cc.head(8), cc.tail(8)])
    sections = [
        ("State change map", map_dropdown(summaries)),
        ("State extremes: diagnosed diabetes",
         bar_extremes(diab, "state", "Diagnosed diabetes: largest and smallest state change (pp)", n=8)),
        ("National trend by measure", indexed_lines(nat, "measure", "value",
                                                    "National age-adjusted prevalence (pop-weighted, indexed)")),
        ("County extremes: diagnosed diabetes",
         bar_extremes(cc_ext, "county", "Counties with the largest rise and fall in diabetes prevalence (pp)",
                      n=8, left_margin=260)),
        ("Diabetes prevalence by state and year", indexed_lines(yearly["DIABETES"], "state", "value",
                                                               "Diagnosed diabetes by state (indexed)", height=520)),
        ("Summary", table_figure(diab.round(2), "Diagnosed diabetes by state")),
    ]
    kpis = kpi_cards([
        ("Period", f"BRFSS {first} - {last}"),
        ("Counties", str(df["fips"].nunique())),
        ("Largest diabetes rise", ", ".join(f"{r.state} ({r.abs_change:+.2f} pp)" for r in diab.head(3).itertuples())),
        ("Largest diabetes fall", ", ".join(f"{r.state} ({r.abs_change:+.2f} pp)" for r in diab.tail(3).iloc[::-1].itertuples())),
    ])
    return sections, kpis, summaries


NOTES = """<ul>
<li><b>Sources:</b> <a href="https://www.cdc.gov/places/">CDC PLACES</a>; county releases on
<a href="https://data.cdc.gov/browse?q=PLACES%20county%20data">data.cdc.gov</a>;
<a href="https://www.cdc.gov/places/methodology/index.html">methodology</a>.</li>
<li>Values are model-based small-area estimates of age-adjusted prevalence from BRFSS (one survey year per release).
Cross-release changes mix real change with model and methodology updates: treat them as indicative.</li>
<li>State values are population-weighted county means (county total population). Changes are in percentage points.</li></ul>"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = pl.load_all(RAW_DIR)
    sections, kpis, summaries = build(df)
    first, last = int(df["year"].min()), int(df["year"].max())
    (OUT_DIR / "dashboard.html").write_text(
        render_html("CDC PLACES County Health Dashboard", f"Age-adjusted prevalence, BRFSS {first}-{last}",
                    sections, kpis, NOTES), encoding="utf-8")
    for m, s in summaries.items():
        s.drop(columns=["pct_change"]).to_csv(OUT_DIR / f"state_change_{m.lower()}.csv", index=False)
    print(f"Wrote {OUT_DIR / 'dashboard.html'}")


if __name__ == "__main__":
    main()
