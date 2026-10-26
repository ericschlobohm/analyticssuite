# Dashboard toolkit (`snowflake_analytics_agents.dashboard_toolkit`)

Dataset-agnostic helpers for building static, change-over-time dashboards. It knows nothing about any
specific data source; example projects under [`examples/`](../examples/README.md) supply their own loaders.

**Requirements:** `pandas`, `plotly` and `requests`. These are not yet declared in `pyproject.toml`, so install them
manually (`pip install pandas plotly requests`) before running the examples or `tests/test_dashboard_toolkit.py`.

## API

| Function | Purpose |
|----------|---------|
| `download_zip(url, target_dir, marker_glob="*", headers=None, timeout=120)` | Cached download + extract (browser User-Agent by default); skipped if `marker_glob` already matches in `target_dir` |
| `common_keys(df, keys, period="year")` | Keep entities present in every period (like-for-like comparisons) |
| `first_last_change(yearly, value, key="state", period="year")` | First-to-last absolute/percent change, sorted by `pct_change` descending |
| `style_figure(fig, title, height=450)` | Apply the shared look (white template, title, margins) |
| `choropleth_change(locations, values, title, colorbar_title="% change", location_mode="USA-states", scope="usa")` | Zero-centred diverging map |
| `bar_extremes(summary, label, title, n=10, value="pct_change", left_margin=40)` | Top-n increases and decreases as coloured bars |
| `indexed_lines(yearly, key, value, title, highlight_up=(), highlight_down=(), period="year", height=450)` | Lines indexed to 100 at the first period, optional highlights |
| `table_figure(table, title, height=520)` | Styled table |
| `kpi_cards(cards)` | HTML for `(label, value)` KPI cards |
| `render_html(page_title, subtitle, sections, kpis_html="", notes_html="")` | Self-contained HTML page (plotly JS embedded once) |

Constants: `UP_COLOR`, `DOWN_COLOR`, `DIVERGING_SCALE`, `DEFAULT_HEADERS`.

## Data conventions

* "Yearly" frames are long format: one row per (key, period) with a numeric value.
* Change summaries have `<value>_<first>`, `<value>_<last>`, `abs_change`, `pct_change`.
* Text passed to `kpi_cards`, titles and headings is HTML-escaped; `kpis_html`/`notes_html` are trusted fragments.

## Minimal usage

```python
from pathlib import Path

from snowflake_analytics_agents.dashboard_toolkit import (
    bar_extremes, choropleth_change, first_last_change, kpi_cards, render_html,
)

summary = first_last_change(yearly, "value", key="state")
sections = [
    ("Map", choropleth_change(summary["state"], summary["pct_change"], "% change")),
    ("Ranking", bar_extremes(summary, "state", "Top/bottom 10")),
]
html = render_html("Title", "Subtitle", sections, kpis_html=kpi_cards([("States", str(len(summary)))]))
Path("dashboard.html").write_text(html, encoding="utf-8")
```

## Examples using the toolkit

| Example | Run |
|---------|-----|
| [cms_medicare](../examples/cms_medicare/README.md) | `python examples/cms_medicare/build_dashboard.py` |
| [cdc_places](../examples/cdc_places/README.md) | `python examples/cdc_places/build_dashboard.py` |
| [cms_care_compare](../examples/cms_care_compare/README.md) | `python examples/cms_care_compare/build_dashboard.py` |
| [medicaid_diabetes_a1c](../examples/medicaid_diabetes_a1c/README.md) | `python examples/medicaid_diabetes_a1c/build_dashboard.py` |

To add your own, see [Adding a new example](../examples/README.md#adding-a-new-example).

Tests: `tests/test_dashboard_toolkit.py`; run `python -m pytest tests -q --no-cov`.
