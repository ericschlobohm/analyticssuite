"""Dataset-agnostic helpers for building static, change-over-time dashboards.

This module contains no knowledge of any particular data source. Example projects
(see ``examples/``) combine these helpers with their own data loaders:

* **Data acquisition**: :func:`download_zip` (cached download + extract).
* **Analysis**: :func:`common_keys`, :func:`first_last_change`.
* **Plotly figures**: :func:`choropleth_change`, :func:`bar_extremes`,
  :func:`indexed_lines`, :func:`table_figure`.
* **Page assembly**: :func:`kpi_cards`, :func:`render_html`.

Conventions
-----------
* "Yearly" frames are long format: one row per (key, year) with a numeric value column.
* Change summaries have columns ``<value>_<first>``, ``<value>_<last>``,
  ``abs_change`` and ``pct_change`` and are sorted by ``pct_change`` descending.
* Diverging colour scales are centred on zero so decreases and increases are comparable.
"""

from __future__ import annotations

import html
import io
import zipfile
from pathlib import Path
from typing import Iterable, Sequence

import pandas as pd
import plotly.graph_objects as go
import requests

# Colours used for increases / decreases in bar and line charts.
UP_COLOR = "#2166ac"
DOWN_COLOR = "#b2182b"
DIVERGING_SCALE = "RdBu"

# Some public sites (e.g. cms.gov) reject requests without a browser-like User-Agent.
DEFAULT_HEADERS = {"User-Agent": "Mozilla/5.0"}


# --------------------------------------------------------------------------- data acquisition
def download_zip(
    url: str,
    target_dir: Path,
    marker_glob: str = "*",
    headers: dict[str, str] | None = None,
    timeout: int = 120,
) -> Path:
    """Download a zip archive and extract it into ``target_dir``, skipping if already cached.

    Args:
        url: Archive URL.
        target_dir: Directory to extract into (created if needed).
        marker_glob: Glob that proves a previous extraction succeeded; if any file in
            ``target_dir`` matches, the download is skipped.
        headers: HTTP headers; defaults to :data:`DEFAULT_HEADERS`.
        timeout: Request timeout in seconds.

    Returns:
        ``target_dir``.
    """
    if target_dir.exists() and any(target_dir.glob(marker_glob)):
        return target_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, headers=headers or DEFAULT_HEADERS, timeout=timeout)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        zf.extractall(target_dir)
    return target_dir


# --------------------------------------------------------------------------- analysis
def common_keys(df: pd.DataFrame, keys: Sequence[str], period: str = "year") -> pd.DataFrame:
    """Keep only rows whose ``keys`` combination appears in every period.

    Guarantees like-for-like comparisons when entities are created or retired over time.
    """
    n_periods = df[period].nunique()
    complete = df.groupby(list(keys))[period].transform("nunique") == n_periods
    return df[complete].copy()


def first_last_change(yearly: pd.DataFrame, value: str, key: str = "state", period: str = "year") -> pd.DataFrame:
    """First-to-last period absolute and percent change of ``value`` per ``key``.

    Returns a frame sorted by ``pct_change`` descending (greatest increase first).
    """
    wide = yearly.pivot(index=key, columns=period, values=value)
    first, last = wide.columns.min(), wide.columns.max()
    out = pd.DataFrame(
        {
            f"{value}_{first}": wide[first],
            f"{value}_{last}": wide[last],
            "abs_change": wide[last] - wide[first],
            "pct_change": (wide[last] / wide[first] - 1) * 100,
        }
    )
    return out.sort_values("pct_change", ascending=False).reset_index()


# --------------------------------------------------------------------------- figures
def style_figure(fig: go.Figure, title: str, height: int = 450) -> go.Figure:
    """Apply the shared look (white template, title, margins) to a figure."""
    fig.update_layout(title=title, height=height, template="plotly_white", margin=dict(l=40, r=20, t=60, b=40))
    return fig


def choropleth_change(
    locations: pd.Series,
    values: pd.Series,
    title: str,
    colorbar_title: str = "% change",
    location_mode: str = "USA-states",
    scope: str = "usa",
) -> go.Figure:
    """Zero-centred diverging choropleth, e.g. percent change by US state."""
    lim = float(values.abs().max())
    fig = go.Figure(
        go.Choropleth(
            locations=locations,
            z=values,
            locationmode=location_mode,
            colorscale=DIVERGING_SCALE,
            zmin=-lim,
            zmax=lim,
            colorbar=dict(title=colorbar_title),
            hovertemplate="%{location}<br>%{z:.2f}<extra></extra>",
        )
    )
    fig.update_geos(scope=scope)
    return style_figure(fig, title, 520)


def bar_extremes(
    summary: pd.DataFrame, label: str, title: str, n: int = 10, value: str = "pct_change", left_margin: int = 40
) -> go.Figure:
    """Horizontal bars for the ``n`` largest increases and ``n`` largest decreases.

    ``summary`` must be sorted descending by ``value`` (as :func:`first_last_change` returns).
    """
    ext = pd.concat([summary.head(n), summary.tail(n)]).sort_values(value)
    colors = [DOWN_COLOR if v < 0 else UP_COLOR for v in ext[value]]
    fig = go.Figure(go.Bar(x=ext[value], y=ext[label], orientation="h", marker_color=colors))
    fig.update_yaxes(type="category")
    fig = style_figure(fig, title, 520)
    fig.update_layout(margin=dict(l=left_margin, r=20, t=60, b=40))
    return fig


def indexed_lines(
    yearly: pd.DataFrame,
    key: str,
    value: str,
    title: str,
    highlight_up: Iterable[str] = (),
    highlight_down: Iterable[str] = (),
    period: str = "year",
    height: int = 450,
) -> go.Figure:
    """Line chart of ``value`` indexed to 100 at the first period.

    ``highlight_up`` / ``highlight_down`` keys are coloured blue / red; when both are empty
    every key is drawn with the default palette.
    """
    base_period = yearly[period].min()
    base = yearly[yearly[period] == base_period].set_index(key)[value]
    idx = yearly.assign(_index=lambda d: d[value] / d[key].map(base) * 100)
    colored = [(k, UP_COLOR) for k in highlight_up] + [(k, DOWN_COLOR) for k in highlight_down]
    picks = colored or [(k, None) for k in idx[key].unique()]
    fig = go.Figure()
    for k, color in picks:
        d = idx[idx[key] == k].sort_values(period)
        fig.add_trace(
            go.Scatter(x=d[period], y=d["_index"], mode="lines+markers", name=str(k),
                       line=dict(color=color) if color else None)
        )
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(title=f"Index ({base_period} = 100)")
    return style_figure(fig, title, height)


def table_figure(table: pd.DataFrame, title: str, height: int = 520) -> go.Figure:
    """Render a DataFrame as a styled plotly table."""
    fig = go.Figure(
        go.Table(
            header=dict(values=list(table.columns), fill_color="#2c3e50", font=dict(color="white"), align="left"),
            cells=dict(values=[table[c] for c in table.columns], fill_color="#f7f7f7", align="left"),
        )
    )
    return style_figure(fig, title, height)


# --------------------------------------------------------------------------- page assembly
def kpi_cards(cards: Sequence[tuple[str, str]]) -> str:
    """HTML for a row of KPI cards from ``(label, value)`` pairs (text is HTML-escaped)."""
    return "".join(
        f'<div class="kpi"><div class="k">{html.escape(k)}</div><div class="v">{html.escape(v)}</div></div>'
        for k, v in cards
    )


_PAGE_CSS = (
    "body{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f0f2f5;color:#222}"
    "header{background:#1f3a5f;color:#fff;padding:18px 28px}main{padding:16px 28px;max-width:1300px;margin:auto}"
    ".kpis{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:16px}"
    ".kpi{background:#fff;border-radius:6px;padding:10px 14px;flex:1;min-width:200px}"
    ".k{font-size:12px;color:#666;text-transform:uppercase}.v{font-size:15px;font-weight:600;margin-top:4px}"
    "section{background:#fff;border-radius:6px;padding:8px 16px;margin-bottom:16px}.notes{font-size:13px;color:#444}"
)


def render_html(
    page_title: str,
    subtitle: str,
    sections: Sequence[tuple[str, go.Figure]],
    kpis_html: str = "",
    notes_html: str = "",
) -> str:
    """Assemble a single self-contained HTML dashboard page.

    Plotly's JavaScript is embedded once (with the first figure). ``kpis_html`` and
    ``notes_html`` are trusted HTML fragments; ``page_title``/``subtitle`` are escaped.
    """
    body = "".join(
        f"<section><h2>{html.escape(heading)}</h2>"
        + fig.to_html(full_html=False, include_plotlyjs=(i == 0))
        + "</section>"
        for i, (heading, fig) in enumerate(sections)
    )
    notes = f'<section class="notes"><h2>Methodology &amp; notes</h2>{notes_html}</section>' if notes_html else ""
    title, sub = html.escape(page_title), html.escape(subtitle)
    return (
        f'<!doctype html><html><head><meta charset="utf-8"><title>{title}</title><style>{_PAGE_CSS}</style></head>'
        f"<body><header><h1>{title}</h1><div>{sub}</div></header><main>"
        f'<div class="kpis">{kpis_html}</div>{body}{notes}</main></body></html>'
    )
