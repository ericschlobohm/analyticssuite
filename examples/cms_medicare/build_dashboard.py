"""Build the CMS Medicare GAF / fee-schedule payment dashboard (CY2022-CY2026).

Usage:
    python examples/cms_medicare/build_dashboard.py

Outputs (examples/cms_medicare/output/): dashboard.html, dashboard_config.json, and CSV datasets.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import cms_data as cms  # noqa: E402
from snowflake_analytics_agents.dashboard import (  # noqa: E402
    ChartConfig,
    ChartType,
    DashboardConfig,
    DashboardLayout,
    FilterConfig,
)
from snowflake_analytics_agents.dashboard_toolkit import (  # noqa: E402
    DIVERGING_SCALE,
    bar_extremes,
    choropleth_change,
    first_last_change,
    indexed_lines,
    kpi_cards,
    render_html,
    style_figure,
    table_figure,
)

OUT_DIR = Path(__file__).resolve().parent / "output"
RAW_DIR = ROOT / "data" / "cms_raw"


def bar_localities(loc_summary: pd.DataFrame, names: pd.DataFrame, n: int = 8) -> go.Figure:
    merged = loc_summary.merge(names, on=["state", "locality"])
    merged["label"] = merged["state"] + " - " + merged["locality_name"].str.slice(0, 40)
    return bar_extremes(merged, "label", f"Localities with the largest and smallest GAF change (top/bottom {n})",
                        n=n, left_margin=300)


def line_components(gaf: pd.DataFrame) -> go.Figure:
    comp = gaf.groupby("year")[["gpci_work", "gpci_pe", "gpci_mp", "gaf"]].mean().reset_index()
    long = comp.melt(id_vars="year", var_name="component", value_name="value")
    long["component"] = long["component"].map(
        {"gpci_work": "Work GPCI", "gpci_pe": "Practice expense GPCI", "gpci_mp": "Malpractice GPCI", "gaf": "Blended GAF"}
    )
    return indexed_lines(long, "component", "value", "Average of GPCI components across localities (index)")


def line_national_payment(pay: pd.DataFrame) -> go.Figure:
    nat = pay.groupby(["year", "hcpcs"], as_index=False)["national_payment"].first()
    nat["label"] = nat["hcpcs"].map(lambda h: f"{h} {cms.PROCEDURES[h][0][:28]}")
    return indexed_lines(nat, "label", "national_payment",
                         "National base payment by procedure (GPCI = 1.0), indexed", height=520)


def map_payment_dropdown(pay: pd.DataFrame) -> go.Figure:
    first, last = int(pay["year"].min()), int(pay["year"].max())
    codes = list(cms.PROCEDURES)
    summaries = {}
    for code in codes:
        yearly = pay[pay["hcpcs"] == code].groupby(["state", "year"], as_index=False)["payment"].mean()
        summaries[code] = first_last_change(yearly, "payment")
    lim = max(float(s["pct_change"].abs().max()) for s in summaries.values())
    fig = go.Figure()
    for i, code in enumerate(codes):
        s = summaries[code]
        fig.add_trace(
            go.Choropleth(
                locations=s["state"], z=s["pct_change"], locationmode="USA-states",
                colorscale=DIVERGING_SCALE, zmin=-lim, zmax=lim, visible=(i == 0),
                colorbar=dict(title="% change"),
                customdata=s[[f"payment_{first}", f"payment_{last}"]],
                hovertemplate="%{location}<br>%{z:.2f}%<br>$%{customdata[0]:.2f} to $%{customdata[1]:.2f}<extra></extra>",
            )
        )
    buttons = [
        dict(label=f"{code} {cms.PROCEDURES[code][0][:30]}", method="update",
             args=[{"visible": [j == i for j in range(len(codes))]}])
        for i, code in enumerate(codes)
    ]
    fig.update_layout(updatemenus=[dict(buttons=buttons, x=0.0, y=1.15, xanchor="left")])
    fig.update_geos(scope="usa")
    return style_figure(fig, f"Change in average Medicare payment by state, {first} to {last}", 560)


def table_payments(pay: pd.DataFrame) -> go.Figure:
    first, last = int(pay["year"].min()), int(pay["year"].max())
    rows = []
    for (code, desc, setting), d in pay.groupby(["hcpcs", "description", "setting"]):
        a, b = d[d["year"] == first], d[d["year"] == last]
        n0, n1 = a["national_payment"].iloc[0], b["national_payment"].iloc[0]
        rows.append([code, desc, setting, round(n0, 2), round(n1, 2), round((n1 / n0 - 1) * 100, 1),
                     round(b["payment"].min(), 2), round(b["payment"].max(), 2)])
    t = pd.DataFrame(rows, columns=["HCPCS", "Procedure", "Setting", f"National {first}", f"National {last}",
                                    "% change", f"Lowest locality {last}", f"Highest locality {last}"])
    return table_figure(t, "Procedure base payments (USD) and locality range")


def kpi_html(summary: pd.DataFrame, gaf: pd.DataFrame) -> str:
    def fmt(df: pd.DataFrame) -> str:
        return ", ".join(f"{r.state} ({r.pct_change:+.2f}%)" for r in df.itertuples())

    first, last = int(gaf["year"].min()), int(gaf["year"].max())
    least = summary.reindex(summary["pct_change"].abs().sort_values().index).head(3)
    cards = [
        ("Period", f"CY{first} - CY{last}"),
        ("Localities compared", str(gaf[["state", "locality"]].drop_duplicates().shape[0])),
        ("Greatest GAF increase", fmt(summary.head(3))),
        ("Greatest GAF decrease", fmt(summary.tail(3).iloc[::-1])),
        ("Least changed", fmt(least)),
    ]
    return kpi_cards(cards)


NOTES = """<ul>
<li><b>Source:</b> CMS PFS Relative Value Files (final release per year): Addendum E (GPCIs by locality) and the national RVU file (RVUs, conversion factor).</li>
<li><b>GAF</b> = 0.50866 &times; Work GPCI + 0.44839 &times; PE GPCI + 0.04295 &times; MP GPCI. Fixed weights are used and the GAF is derived by this project (these files publish GPCIs, not a GAF column). Work GPCI includes the 1.0 floor where published.</li>
<li><b>State GAF</b> = unweighted mean of the state's localities (no population weighting). Only localities present in all five years are compared (retired California localities are excluded).</li>
<li><b>Payment</b> = (Work RVU &times; PW GPCI + PE RVU &times; PE GPCI + MP RVU &times; MP GPCI) &times; conversion factor. Conversion factors: 2022 $34.6062, 2023 $33.8872, 2024 $33.2875, 2025 $32.3465, 2026 $33.4009 (non-QPP). Facility vs non-facility PE RVUs are chosen per procedure (see table). Payment changes combine RVU, conversion factor and GPCI effects.</li>
<li>Puerto Rico and the Virgin Islands appear in rankings but are not drawn on the US state map.</li></ul>"""


def build_config(first: int, last: int) -> DashboardConfig:
    """Dashboard config mirroring the HTML, with Snowflake-style queries over the exported datasets."""
    cfg = DashboardConfig(
        id="cms_medicare_gaf",
        name="Medicare GAF & Fee Schedule Payments",
        description=f"CY{first}-CY{last} Medicare GAF by state/locality and base payments by procedure",
        layout=DashboardLayout.GRID,
        rows=3,
        cols=2,
        tags=["cms", "medicare", "gaf", "gpci"],
        metadata={"source": "CMS PFS Relative Value Files", "html": "dashboard.html"},
    )
    cfg.filters.append(FilterConfig(id="f_year", name="Year", filter_type="dropdown", column="YEAR",
                                    values=list(range(first, last + 1)), multi_select=True))
    cfg.filters.append(FilterConfig(id="f_proc", name="Procedure", filter_type="dropdown", column="HCPCS",
                                    values=list(cms.PROCEDURES)))
    charts = [
        ("map_gaf", "GAF % change by state", ChartType.HEATMAP,
         "SELECT STATE, PCT_CHANGE FROM CMS_GAF_STATE_CHANGE", "STATE", "PCT_CHANGE"),
        ("bar_extremes", "Largest/smallest GAF change", ChartType.BAR,
         "SELECT STATE, PCT_CHANGE FROM CMS_GAF_STATE_CHANGE "
         "QUALIFY ROW_NUMBER() OVER (ORDER BY PCT_CHANGE DESC) <= 10 "
         "OR ROW_NUMBER() OVER (ORDER BY PCT_CHANGE) <= 10", "PCT_CHANGE", "STATE"),
        ("line_state_gaf", "State GAF trend", ChartType.LINE,
         "SELECT STATE, YEAR, AVG(GAF) AS GAF FROM CMS_GAF_LOCALITY GROUP BY STATE, YEAR ORDER BY YEAR",
         "YEAR", "GAF"),
        ("bar_localities", "Locality GAF change", ChartType.BAR,
         "SELECT STATE, LOCALITY_NAME, PCT_CHANGE FROM CMS_GAF_LOCALITY_CHANGE", "PCT_CHANGE", "LOCALITY_NAME"),
        ("map_payment", "Payment % change by state and procedure", ChartType.HEATMAP,
         "SELECT STATE, HCPCS, YEAR, AVG(PAYMENT) AS PAYMENT FROM CMS_PAYMENTS_LOCALITY "
         "GROUP BY STATE, HCPCS, YEAR", "STATE", "PAYMENT"),
        ("line_national_payment", "National base payment by procedure", ChartType.LINE,
         "SELECT HCPCS, YEAR, MAX(NATIONAL_PAYMENT) AS NATIONAL_PAYMENT FROM CMS_PAYMENTS_LOCALITY "
         "GROUP BY HCPCS, YEAR", "YEAR", "NATIONAL_PAYMENT"),
    ]
    for cid, title, ctype, query, x, y in charts:
        cfg.add_chart(ChartConfig(id=cid, title=title, chart_type=ctype, query=query, x_column=x, y_column=y))
    return cfg


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    data = cms.build_datasets(RAW_DIR)
    gaf, pay = data["gaf_locality"], data["payments_locality"]
    first, last = int(gaf["year"].min()), int(gaf["year"].max())

    state_gaf = cms.state_yearly(gaf, "gaf")
    state_summary = first_last_change(state_gaf, "gaf")
    loc = gaf.assign(loc=gaf["state"] + "|" + gaf["locality"].astype(str))[["loc", "year", "gaf"]]
    loc_summary = first_last_change(loc, "gaf", key="loc")
    loc_summary[["state", "locality"]] = loc_summary["loc"].str.split("|", expand=True)
    loc_summary["locality"] = loc_summary["locality"].astype(int)
    names = gaf[["state", "locality", "locality_name"]].drop_duplicates()

    sections = [
        ("Where did GAF change the most? (state average, first to last year)",
         choropleth_change(state_summary["state"], state_summary["pct_change"],
                           f"% change in average GAF, CY{first} to CY{last}")),
        ("Ranking of greatest and least changed states", bar_extremes(state_summary, "state", "Largest and smallest GAF change by state (top/bottom 10)")),
        ("GAF trend over time", indexed_lines(state_gaf, "state", "gaf", "GAF trend: 5 biggest gainers (blue) and decliners (red)",
                       highlight_up=state_summary.head(5)["state"], highlight_down=state_summary.tail(5)["state"])),
        ("Locality detail", bar_localities(loc_summary, names)),
        ("What drives GAF: GPCI components", line_components(gaf)),
        ("Base payments by procedure over time", line_national_payment(pay)),
        ("Payment change by state for a selected procedure", map_payment_dropdown(pay)),
        ("Procedure payment table", table_payments(pay)),
    ]
    html = render_html("Medicare Geographic Adjustment Factors & Fee Schedule Payments",
                       f"CMS Physician Fee Schedule, CY{first}-CY{last}", sections, kpi_html(state_summary, gaf), NOTES)
    (OUT_DIR / "dashboard.html").write_text(html, encoding="utf-8")

    gaf.to_csv(OUT_DIR / "gaf_by_locality.csv", index=False)
    state_gaf.to_csv(OUT_DIR / "gaf_by_state_year.csv", index=False)
    state_summary.to_csv(OUT_DIR / "gaf_state_change.csv", index=False)
    loc_summary.drop(columns="loc").to_csv(OUT_DIR / "gaf_locality_change.csv", index=False)
    pay.to_csv(OUT_DIR / "payments_by_locality_procedure.csv", index=False)
    config = build_config(first, last).to_dict()
    (OUT_DIR / "dashboard_config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(f"Wrote dashboard to {OUT_DIR / 'dashboard.html'}")


if __name__ == "__main__":
    main()
