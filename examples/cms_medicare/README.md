# Example: Medicare GAF & Fee Schedule Payments (CY2022–CY2026)

A self-contained example that turns public CMS data into a change-over-time dashboard.
Everything specific to this dataset lives in this folder; generic building blocks come from the
shared [`dashboard_toolkit`](../../src/snowflake_analytics_agents/dashboard_toolkit.py)
(see [docs/dashboard_toolkit.md](../../docs/dashboard_toolkit.md)).

## Run

```bash
python examples/cms_medicare/build_dashboard.py
```

The first run downloads five CMS zips (~tens of MB) into `data/cms_raw/` (gitignored); later runs use the cache.
Open `output/dashboard.html` in a browser.

## Files

| File | Purpose |
|------|---------|
| `cms_data.py` | CMS-specific loading: URLs, GPCI/RVU parsing, GAF derivation, payment formula |
| `build_dashboard.py` | Builds figures with the toolkit, writes HTML, CSVs and a `DashboardConfig` JSON |
| `output/` | Generated `dashboard.html`, CSV datasets, `dashboard_config.json` |
| `../../tests/test_example_cms_medicare.py` | Offline unit tests for the calculations |

## Source and method

All source links: [SOURCES.md](SOURCES.md).


* Source: [CMS PFS Relative Value Files](https://www.cms.gov/medicare/payment/fee-schedules/physician/pfs-relative-value-files)
  (final release per year): Addendum E (GPCIs by locality) and the national RVU file (RVUs, conversion factor).
* **GAF** is derived here: 0.50866 × work GPCI + 0.44839 × practice-expense GPCI + 0.04295 × malpractice GPCI
  (CMS publishes GPCIs, not a GAF). Weights are fixed so changes reflect GPCIs only.
* **State GAF** is the unweighted mean of its localities. Only localities present in every year are compared.
* **Payment** = (work RVU × PW GPCI + PE RVU × PE GPCI + MP RVU × MP GPCI) × conversion factor, using
  facility or non-facility PE per procedure (13 curated HCPCS codes in `cms_data.PROCEDURES`).
  Payment changes mix RVU, conversion-factor and GPCI effects.
* Puerto Rico and the Virgin Islands appear in rankings but are not drawn on the US map.

## Adding a year

Add the year to `YEARS` and its zip URL to `CMS_ZIP_URLS` in `cms_data.py`, then re-run.

## Using this as a template

A new example should provide: a loader that returns long-format (key, year, value) frames, and a build script
that calls `first_last_change`, the toolkit figure helpers, and `render_html`.

