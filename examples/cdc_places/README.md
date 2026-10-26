# Example: CDC PLACES County Health (BRFSS 2019–2023)

Age-adjusted county prevalence of diagnosed diabetes, obesity, high blood pressure, depression, annual checkup and
uninsured adults, with a state change map (dropdown per measure), state/county extremes and trends.

```bash
python examples/cdc_places/build_dashboard.py   # downloads to data/cdc_places_raw/ (gitignored), writes output/
```

| File | Purpose |
|------|---------|
| `places_data.py` | Socrata release IDs, download/cache, cleaning, population-weighted state aggregation |
| `build_dashboard.py` | Figures via the shared toolkit, HTML and CSVs |
| `SOURCES.md` | Links to every data source and reference |

**Method and caveats:** values are model-based small-area estimates; each release is one BRFSS year and
methodology changes between releases, so changes are indicative. State values are population-weighted over counties
reported in every year (about 47 states/DC; some states lack consistent geography). Changes are in percentage points.
See [SOURCES.md](SOURCES.md).
