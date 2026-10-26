"""CDC PLACES county data access (2019-2023 BRFSS years) for the example dashboard.

Source: CDC PLACES "Local Data for Better Health, County Data" releases on data.cdc.gov (Socrata API).
Each release holds one BRFSS year of model-based county estimates. Only age-adjusted prevalence
is used so releases are comparable despite changing population structure.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

SOURCES = {
    "PLACES project": "https://www.cdc.gov/places/",
    "Methodology": "https://www.cdc.gov/places/methodology/index.html",
    "Data catalog (data.cdc.gov)": "https://data.cdc.gov/browse?q=PLACES%20county%20data",
}

# BRFSS year -> Socrata dataset id (https://data.cdc.gov/resource/<id>)
RELEASES = {
    2023: "swc5-untb",
    2022: "fu4u-a9bh",
    2021: "h3ej-a9ec",
    2020: "duw2-7jbt",
    2019: "pqpp-u99h",
}

MEASURES = {
    "DIABETES": "Diagnosed diabetes",
    "OBESITY": "Obesity",
    "BPHIGH": "High blood pressure",
    "DEPRESSION": "Depression",
    "CHECKUP": "Annual checkup",
    "ACCESS2": "No health insurance (18-64)",
}

HEADERS = {"User-Agent": "curl/8.0"}
COLUMNS = ["year", "stateabbr", "locationid", "locationname", "measureid", "data_value", "totalpopulation"]


def fetch_release(year: int, raw_dir: Path) -> pd.DataFrame:
    """Download (and cache as CSV) age-adjusted county values for one release."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    cache = raw_dir / f"places_county_{year}.csv"
    if cache.exists():
        return pd.read_csv(cache, dtype={"locationid": str})
    measures = ",".join(f"'{m}'" for m in MEASURES)
    params = {
        "$select": ",".join(COLUMNS),
        "$where": f"datavaluetypeid='AgeAdjPrv' AND measureid in({measures})",
        "$limit": 100000,
    }
    resp = requests.get(f"https://data.cdc.gov/resource/{RELEASES[year]}.csv", params=params,
                        headers=HEADERS, timeout=180)
    resp.raise_for_status()
    cache.write_text(resp.text, encoding="utf-8")
    return pd.read_csv(cache, dtype={"locationid": str})


def load_all(raw_dir: Path) -> pd.DataFrame:
    """All releases, cleaned. One row per (year, county, measure)."""
    return clean(pd.concat([fetch_release(y, raw_dir) for y in RELEASES], ignore_index=True))


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Normalise types, drop missing values and duplicate (year, county, measure) rows."""
    out = df.copy()
    out["data_value"] = pd.to_numeric(out["data_value"], errors="coerce")
    out["totalpopulation"] = pd.to_numeric(out["totalpopulation"], errors="coerce")
    out["locationid"] = out["locationid"].astype(str).str.zfill(5)
    out = out.dropna(subset=["data_value", "year"]).drop_duplicates(["year", "locationid", "measureid"])
    out["year"] = out["year"].astype(int)
    return out.rename(columns={"stateabbr": "state", "locationid": "fips", "locationname": "county",
                               "data_value": "value", "totalpopulation": "population"})


def state_yearly(df: pd.DataFrame, measure: str) -> pd.DataFrame:
    """Population-weighted state mean per year, using only counties reported in every year."""
    d = df[(df["measureid"] == measure) & df["population"].notna()].copy()
    d = d[d.groupby("fips")["year"].transform("nunique") == d["year"].nunique()]
    d["w"] = d["value"] * d["population"]
    g = d.groupby(["state", "year"], as_index=False).agg(w=("w", "sum"), pop=("population", "sum"))
    g["value"] = g["w"] / g["pop"]
    return g[["state", "year", "value"]]


def county_change(df: pd.DataFrame, measure: str) -> pd.DataFrame:
    """Percentage-point change per county between first and last year (counties in both)."""
    d = df[df["measureid"] == measure]
    first, last = int(d["year"].min()), int(d["year"].max())
    a = d[d["year"] == first].set_index("fips")
    b = d[d["year"] == last].set_index("fips")
    idx = a.index.intersection(b.index)
    out = pd.DataFrame({
        "county": b.loc[idx, "county"] + ", " + b.loc[idx, "state"],
        "state": b.loc[idx, "state"],
        f"value_{first}": a.loc[idx, "value"],
        f"value_{last}": b.loc[idx, "value"],
    })
    out["abs_change"] = out[f"value_{last}"] - out[f"value_{first}"]
    return out.reset_index().sort_values("abs_change", ascending=False)
