# Example: CMS Care Compare Hospital Quality (current snapshot)

Hospital overall star ratings and 30-day pneumonia readmission rates by state, ownership and hospital type.

```bash
python examples/cms_care_compare/build_dashboard.py   # downloads to data/care_compare_raw/ (gitignored)
```

| File | Purpose |
|------|---------|
| `care_compare_data.py` | Provider Data Catalog paging/caching, join of star ratings and readmissions, state summary |
| `build_dashboard.py` | Figures via the shared toolkit, HTML and CSV |
| `SOURCES.md` | Links to every data source and reference |

**Caveats:** Care Compare publishes only the current release (no history), so this compares geography and hospital
types instead of change over time; archive outputs each quarter to build a history. The hospital-wide readmission
measure (`Hybrid_HWR`) is currently all "Not Available", so pneumonia (`READM_30_PN`, widest coverage) is used.
States with fewer than 5 rated hospitals are omitted. The CMS API rejects some default HTTP user agents; the code
sends a `curl/8.0` User-Agent. See [SOURCES.md](SOURCES.md).
