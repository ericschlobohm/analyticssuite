"""Build the Medicaid diabetes HbA1c poor-control dashboard (2020-2024).

Usage: python examples/medicaid_diabetes_a1c/build_dashboard.py
Outputs (examples/medicaid_diabetes_a1c/output/): dashboard.html and CSVs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import medicaid_data as md  # noqa: E402
from snowflake_analytics_agents.dashboard_toolkit import (  # noqa: E402
    bar_extremes, choropleth_change, common_keys, first_last_change, indexed_lines, kpi_cards,
    render_html, style_figure, table_figure,
)

OUT_DIR = Path(__file__).resolve().parent / "output"
RAW_DIR = ROOT / "data" / "medicaid_raw"


def level_map(latest) -> go.Figure:
    last = int(latest["year"].max())
    fig = go.Figure(go.Choropleth(
        locations=latest["state"], z=latest["rate"], locationmode="USA-states", colorscale="YlOrRd",
        colorbar=dict(title="% poor control"), hovertemplate="%{location}<br>%{z:.1f}%<extra></extra>"))
    fig.update_geos(scope="usa")
    return style_figure(fig, f"HbA1c poor control (>9%) among Medicaid adults with diabetes, {last}", 520)


def build(df):
    yearly = md.state_yearly(df)
    first, last = int(yearly["year"].min()), int(yearly["year"].max())
    balanced = common_keys(yearly, ["state"])
    summary = first_last_change(balanced, "rate")
    summary = summary.sort_values("abs_change", ascending=False)
    summary["pct_change"] = summary["abs_change"]  # percentage points; negative = improvement
    nat = md.national_yearly(df)
    nat_long = nat.assign(series="National median of states")[["year", "series", "median"]]
    latest = yearly[yearly["year"] == last]
    improved, worsened = summary.tail(3).iloc[::-1], summary.head(3)
    kpis = kpi_cards([
        ("Period", f"Core Set {first} - {last}"),
        ("States in all years", str(balanced["state"].nunique())),
        ("Most improved (pp)", ", ".join(f"{r.state} ({r.abs_change:+.1f})" for r in improved.itertuples())),
        ("Most worsened (pp)", ", ".join(f"{r.state} ({r.abs_change:+.1f})" for r in worsened.itertuples())),
        (f"National median {last}", f"{float(nat.loc[nat['year'] == last, 'median'].iloc[0]):.1f}%"),
    ])
    sections = [
        (f"Poor control by state, {last}", level_map(latest)),
        ("Change map", choropleth_change(summary["state"], summary["abs_change"],
                                         f"Change in poor-control rate, {first} to {last} (pp; blue = worse)",
                                         colorbar_title="pp change")),
        ("State extremes", bar_extremes(summary, "state", "Largest worsening and improvement (pp)", n=8)),
        ("National trend", indexed_lines(nat_long.rename(columns={"median": "rate"}), "series", "rate",
                                         "National median of state poor-control rates (indexed)")),
        ("State trends", indexed_lines(balanced, "state", "rate", "Poor-control rate by state (indexed)", height=520)),
        ("State table", table_figure(summary.round(2), "Poor-control rate by state: first vs last year")),
    ]
    return sections, kpis, summary, yearly


NOTES = """<ul>
<li><b>Sources:</b> <a href="https://data.medicaid.gov/dataset/e85033c7-367e-467e-9e81-8e85048102b8">Medicaid.gov Child and Adult Health Care Quality Measures</a>
(annual Core Set datasets); <a href="https://www.medicaid.gov/medicaid/quality-of-care/quality-of-care-performance-measurement/adult-and-child-health-care-quality-measures/index.html">Core Set overview</a>.</li>
<li><b>Type 1 vs type 2:</b> the measure covers adults with <i>type 1 or type 2</i> diabetes combined. No public state-level dataset isolates type 1.</li>
<li>Measure: HbA1c &gt;9.0% (poor control), lower is better. Named HPC-AD (2020-22) and HBD-AD (2023-24); age bands (18-64/75) and populations differ across years, and states opt in to reporting, so changes are indicative. State values average the reported population/method rows.</li></ul>"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df = md.load_all(RAW_DIR)
    sections, kpis, summary, yearly = build(df)
    (OUT_DIR / "dashboard.html").write_text(
        render_html("Medicaid Diabetes HbA1c Dashboard", "HbA1c poor control among Medicaid adults with diabetes",
                    sections, kpis, NOTES), encoding="utf-8")
    yearly.to_csv(OUT_DIR / "state_year_poor_control.csv", index=False)
    summary.drop(columns=["pct_change"]).to_csv(OUT_DIR / "state_change.csv", index=False)
    print(f"Wrote {OUT_DIR / 'dashboard.html'}")


if __name__ == "__main__":
    main()
