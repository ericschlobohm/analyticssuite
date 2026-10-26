# Dashboard toolkit (`snowflake_analytics_agents.dashboard_toolkit`)

Dataset-agnostic helpers for building static, change-over-time dashboards. It knows nothing about any
specific data source; example projects under [`examples/`](../examples) supply their own loaders.

## API

| Function | Purpose |
|----------|---------|
| `download_zip(url, target_dir, marker_glob)` | Cached download + extract (browser User-Agent by default) |
| `common_keys(df, keys, period)` | Keep entities present in every period (like-for-like comparisons) |
| `first_last_change(yearly, value, key)` | First-to-last absolute/percent change, sorted descending |
| `choropleth_change(locations, values, title)` | Zero-centred diverging map (US states by default) |
| `bar_extremes(summary, label, title, n)` | Top-n increases and decreases as coloured bars |
| `indexed_lines(yearly, key, value, title, ...)` | Lines indexed to 100 at the first period, optional highlights |
| `table_figure(df, title)` | Styled table |
| `kpi_cards(cards)` / `render_html(...)` | Assemble a self-contained HTML page (plotly embedded once) |

## Data conventions

* "Yearly" frames are long format: one row per (key, period) with a numeric value.
* Change summaries have `<value>_<first>`, `<value>_<last>`, `abs_change`, `pct_change`.
* Text passed to `kpi_cards`, titles and headings is HTML-escaped; `kpis_html`/`notes_html` are trusted fragments.

## Minimal usage

```python
from snowflake_analytics_agents.dashboard_toolkit import *

summary = first_last_change(yearly, "value", key="state")
sections = [
    ("Map", choropleth_change(summary["state"], summary["pct_change"], "% change")),
    ("Ranking", bar_extremes(summary, "state", "Top/bottom 10")),
]
Path("dashboard.html").write_text(render_html("Title", "Subtitle", sections), encoding="utf-8")
```

Tests: `tests/test_dashboard_toolkit.py`. Worked example: [examples/cms_medicare](../examples/cms_medicare/README.md).
