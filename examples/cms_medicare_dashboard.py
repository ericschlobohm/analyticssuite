"""Build the CMS Medicare GAF / fee-schedule payment dashboard (CY2022-CY2026).

Usage:
    python examples/cms_medicare_dashboard.py

Outputs (examples/output/cms_medicare/): dashboard.html, dashboard_config.json, and CSV datasets.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from snowflake_analytics_agents import cms_medicare as cms  # noqa: E402
from snowflake_analytics_agents.dashboard import (  # noqa: E402
    ChartConfig,
    ChartType,
    DashboardConfig,
    DashboardLayout,
    FilterConfig,
)

OUT_DIR = ROOT / "examples" / "output" / "cms_medicare"
DIVERGING = "RdBu"
UP, DOWN = "#2166ac", "#b2182b"


def _style(fig: go.Figure, title: str, height: int = 450) -> go.Figure:
    fig.update_layout(title=title, height=height, template="plotly_white", margin=dict(l=40, r=20, t=60, b=40))
    return fig


def map_state_change(summary: pd.DataFrame, title: str) -> go.Figure:
    lim = float(summary["pct_change"].abs().max())
    fig = go.Figure(
        go.Choropleth(
            locations=summary["state"],
            z=summary["pct_change"],
            locationmode="USA-states",
            colorscale=DIVERGING,
            zmin=-lim,
            zmax=lim,
            colorbar=dict(title="% change"),
            hovertemplate="%{location}<br>%{z:.2f}%<extra></extra>",
        )
    )
    fig.update_geos(scope="usa")
    return _style(fig, title, 520)


def bar_extremes(summary: pd.DataFrame, n: int = 10) -> go.Figure:
    ext = pd.concat([summary.head(n), summary.tail(n)]).sort_values("pct_change")
    colors = [DOWN if v < 0 else UP for v in ext["pct_change"]]
    fig = go.Figure(go.Bar(x=ext["pct_change"], y=ext["state"], orientation="h", marker_color=colors))
    fig.update_xaxes(title="% change in average GAF")
    fig.update_yaxes(type="category")
    return _style(fig, f"Largest and smallest GAF change by state (top/bottom {n})", 520)


def line_states(yearly: pd.DataFrame, summary: pd.DataFrame, n: int = 5) -> go.Figure:
    base = yearly[yearly["year"] == yearly["year"].min()].set_index("state")["gaf"]
    idx = yearly.assign(index=lambda d: d["gaf"] / d["state"].map(base) * 100)
    fig = go.Figure()
    picks = [(s, UP) for s in summary.head(n)["state"]] + [(s, DOWN) for s in summary.tail(n)["state"]]
    for state, color in picks:
        d = idx[idx["state"] == state]
        fig.add_trace(go.Scatter(x=d["year"], y=d["index"], mode="lines+markers", name=state, line=dict(color=color)))
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(title=f"GAF index ({int(idx['year'].min())} = 100)")
    return _style(fig, f"GAF trend: {n} biggest gainers (blue) and decliners (red)")


def bar_localities(loc_summary: pd.DataFrame, names: pd.DataFrame, n: int = 8) -> go.Figure:
    merged = loc_summary.merge(names, on=["state", "locality"])
    merged["label"] = merged["state"] + " - " + merged["locality_name"].str.slice(0, 40)
    ext = pd.concat([merged.head(n), merged.tail(n)]).sort_values("pct_change")
    colors = [DOWN if v < 0 else UP for v in ext["pct_change"]]
    fig = go.Figure(go.Bar(x=ext["pct_change"], y=ext["label"], orientation="h", marker_color=colors))
    fig.update_xaxes(title="% change in GAF")
    fig = _style(fig, f"Localities with the largest and smallest GAF change (top/bottom {n})", 520)
    fig.update_layout(margin=dict(l=300, r=20, t=60, b=40))
    return fig


def line_components(gaf: pd.DataFrame) -> go.Figure:
    comp = gaf.groupby("year")[["gpci_work", "gpci_pe", "gpci_mp", "gaf"]].mean().reset_index()
    fig = go.Figure()
    for col, name in [("gpci_work", "Work GPCI"), ("gpci_pe", "Practice expense GPCI"),
                      ("gpci_mp", "Malpractice GPCI"), ("gaf", "Blended GAF")]:
        fig.add_trace(go.Scatter(x=comp["year"], y=comp[col] / comp[col].iloc[0] * 100, mode="lines+markers", name=name))
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(title="Index (first year = 100)")
    return _style(fig, "Average of GPCI components across localities (index)")


def line_national_payment(pay: pd.DataFrame) -> go.Figure:
    nat = pay.groupby(["year", "hcpcs", "description"], as_index=False)["national_payment"].first()
    fig = go.Figure()
    for hcpcs, d in nat.groupby("hcpcs"):
        d = d.sort_values("year")
        fig.add_trace(
            go.Scatter(
                x=d["year"], y=d["national_payment"] / d["national_payment"].iloc[0] * 100,
                mode="lines+markers", name=f"{hcpcs} {d['description'].iloc[0][:28]}",
                customdata=d["national_payment"],
                hovertemplate="%{x}: $%{customdata:.2f} (index %{y:.1f})<extra>" + hcpcs + "</extra>",
            )
        )
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(title="Index (first year = 100)")
    return _style(fig, "National base payment by procedure (GPCI = 1.0), indexed", 520)


def map_payment_dropdown(pay: pd.DataFrame) -> go.Figure:
    first, last = int(pay["year"].min()), int(pay["year"].max())
    codes = list(cms.PROCEDURES)
    summaries = {}
    for code in codes:
        yearly = pay[pay["hcpcs"] == code].groupby(["state", "year"], as_index=False)["payment"].mean()
        summaries[code] = cms.change_summary(yearly, "payment")
    lim = max(float(s["pct_change"].abs().max()) for s in summaries.values())
    fig = go.Figure()
    for i, code in enumerate(codes):
        s = summaries[code]
        fig.add_trace(
            go.Choropleth(
                locations=s["state"], z=s["pct_change"], locationmode="USA-states",
                colorscale=DIVERGING, zmin=-lim, zmax=lim, visible=(i == 0),
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
    return _style(fig, f"Change in average Medicare payment by state, {first} to {last}", 560)


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
    fig = go.Figure(
        go.Table(
            header=dict(values=list(t.columns), fill_color="#2c3e50", font=dict(color="white"), align="left"),
            cells=dict(values=[t[c] for c in t.columns], fill_color="#f7f7f7", align="left"),
        )
    )
    return _style(fig, "Procedure base payments (USD) and locality range", 520)


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
    return "".join(f'<div class="kpi"><div class="k">{k}</div><div class="v">{v}</div></div>' for k, v in cards)


def render_html(sections: list[tuple[str, go.Figure]], kpis: str, notes: str) -> str:
    parts = [
        f"<section><h2>{heading}</h2>"
        + fig.to_html(full_html=False, include_plotlyjs=(i == 0))
        + "</section>"
        for i, (heading, fig) in enumerate(sections)
    ]
    body = "".join(parts)
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>Medicare GAF Dashboard</title>
<style>body{{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f0f2f5;color:#222}}
header{{background:#1f3a5f;color:#fff;padding:18px 28px}}main{{padding:16px 28px;max-width:1300px;margin:auto}}
.kpis{{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}}.kpi{{background:#fff;border-radius:6px;padding:10px 14px;flex:1;min-width:200px}}
.k{{font-size:12px;color:#666;text-transform:uppercase}}.v{{font-size:15px;font-weight:600;margin-top:4px}}
section{{background:#fff;border-radius:6px;padding:8px 16px;margin-bottom:16px}}.notes{{font-size:13px;color:#444}}</style></head>
<body><header><h1>Medicare Geographic Adjustment Factors &amp; Fee Schedule Payments</h1>
<div>CMS Physician Fee Schedule, CY2022-CY2026</div></header><main>
<div class="kpis">{kpis}</div>{body}<section class="notes"><h2>Methodology &amp; notes</h2>{notes}</section></main></body></html>"""


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
    data = cms.build_datasets(ROOT / "data" / "cms_raw")
    gaf, pay = data["gaf_locality"], data["payments_locality"]
    first, last = int(gaf["year"].min()), int(gaf["year"].max())

    state_gaf = cms.state_yearly(gaf, "gaf")
    state_summary = cms.change_summary(state_gaf, "gaf")
    loc = gaf.assign(loc=gaf["state"] + "|" + gaf["locality"].astype(str))[["loc", "year", "gaf"]]
    loc_summary = cms.change_summary(loc, "gaf", key="loc")
    loc_summary[["state", "locality"]] = loc_summary["loc"].str.split("|", expand=True)
    loc_summary["locality"] = loc_summary["locality"].astype(int)
    names = gaf[["state", "locality", "locality_name"]].drop_duplicates()

    sections = [
        ("Where did GAF change the most? (state average, first to last year)",
         map_state_change(state_summary, f"% change in average GAF, CY{first} to CY{last}")),
        ("Ranking of greatest and least changed states", bar_extremes(state_summary)),
        ("GAF trend over time", line_states(state_gaf, state_summary)),
        ("Locality detail", bar_localities(loc_summary, names)),
        ("What drives GAF: GPCI components", line_components(gaf)),
        ("Base payments by procedure over time", line_national_payment(pay)),
        ("Payment change by state for a selected procedure", map_payment_dropdown(pay)),
        ("Procedure payment table", table_payments(pay)),
    ]
    html = render_html(sections, kpi_html(state_summary, gaf), NOTES)
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
