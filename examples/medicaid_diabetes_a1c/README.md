# Example: Medicaid Diabetes HbA1c Poor Control (Core Set 2020–2024)

State-level share of Medicaid adults with diabetes whose HbA1c is in poor control (>9%), with level and change maps,
state extremes, and trends. Lower is better.

```bash
python examples/medicaid_diabetes_a1c/build_dashboard.py   # caches to data/medicaid_raw/ (gitignored)
```

| File | Purpose |
|------|---------|
| `medicaid_data.py` | data.medicaid.gov dataset IDs, download/cache, cleaning, state/national aggregation |
| `build_dashboard.py` | Figures via the shared toolkit, HTML and CSVs |
| `SOURCES.md` | Links to every data source and reference |

**Type 1 diabetes limitation:** the measure covers type 1 *and* type 2 combined. No public dataset reports type 1
diabetes HbA1c alone with state geography; treat this as the closest proxy.

**Caveats:** states opt in to reporting, so only states reporting all five years (about 21) enter the change analysis.
The measure was named HPC-AD (2020–22) and HBD-AD (2023–24) with different age bands and populations; stand-alone
CHIP rows are excluded and remaining population rows are averaged. Large jumps (e.g. MS) may reflect reporting or
methodology changes. See [SOURCES.md](SOURCES.md).
