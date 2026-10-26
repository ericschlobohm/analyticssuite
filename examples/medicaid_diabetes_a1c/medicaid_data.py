"""Medicaid Adult Core Set HbA1c poor-control data access (2020-2024) for the example dashboard.

Source: Medicaid.gov "Child and Adult Health Care Quality Measures" (one dataset per Core Set year).
Measure: share of Medicaid adults aged 18-64/75 with diabetes whose HbA1c was in poor control (>9.0%).
Lower is better. IMPORTANT: the measure covers type 1 AND type 2 diabetes combined; no public dataset
reports type 1 diabetes alone with state geography.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

SOURCES = {
    "Medicaid.gov quality measures (catalog)": "https://data.medicaid.gov/dataset/e85033c7-367e-467e-9e81-8e85048102b8",
    "Adult Core Set overview": "https://www.medicaid.gov/medicaid/quality-of-care/quality-of-care-performance-measurement/adult-and-child-health-care-quality-measures/index.html",
    "NCQA HEDIS HBD measure": "https://www.ncqa.org/hedis/measures/",
    "CDC National Diabetes Statistics Report": "https://www.cdc.gov/diabetes/php/data-research/index.html",
}

# Core Set year -> data.medicaid.gov dataset id
DATASETS = {
    2020: "fbbe1734-b448-4e5a-bc94-3f8688534741",
    2021: "a058ef78-e18b-4435-94aa-b70ab6ce5904",
    2022: "dfd13757-d763-4f7a-9641-3f06ce21b4c6",
    2023: "e85033c7-367e-467e-9e81-8e85048102b8",
    2024: "a5023394-ab10-465b-bb4a-7de5ac98d90c",
}

STATE_ABBR = {
    "Alabama": "AL", "Alaska": "AK", "Arizona": "AZ", "Arkansas": "AR", "California": "CA", "Colorado": "CO",
    "Connecticut": "CT", "Delaware": "DE", "District of Columbia": "DC", "Florida": "FL", "Georgia": "GA",
    "Hawaii": "HI", "Idaho": "ID", "Illinois": "IL", "Indiana": "IN", "Iowa": "IA", "Kansas": "KS",
    "Kentucky": "KY", "Louisiana": "LA", "Maine": "ME", "Maryland": "MD", "Massachusetts": "MA",
    "Michigan": "MI", "Minnesota": "MN", "Mississippi": "MS", "Missouri": "MO", "Montana": "MT",
    "Nebraska": "NE", "Nevada": "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM",
    "New York": "NY", "North Carolina": "NC", "North Dakota": "ND", "Ohio": "OH", "Oklahoma": "OK",
    "Oregon": "OR", "Pennsylvania": "PA", "Rhode Island": "RI", "South Carolina": "SC",
    "South Dakota": "SD", "Tennessee": "TN", "Texas": "TX", "Utah": "UT", "Vermont": "VT",
    "Virginia": "VA", "Washington": "WA", "West Virginia": "WV", "Wisconsin": "WI", "Wyoming": "WY",
}

HEADERS = {"User-Agent": "curl/8.0"}


def fetch_year(year: int, raw_dir: Path) -> pd.DataFrame:
    """Download (and cache as CSV) all hemoglobin A1c rows of one Core Set year."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    cache = raw_dir / f"medicaid_hba1c_{year}.csv"
    if cache.exists():
        return pd.read_csv(cache)
    url = f"https://data.medicaid.gov/api/1/datastore/query/{DATASETS[year]}/0"
    params = {
        "limit": 2000,
        "conditions[0][property]": "measure_name",
        "conditions[0][value]": "%emoglobin%",
        "conditions[0][operator]": "like",
    }
    resp = requests.get(url, params=params, headers=HEADERS, timeout=120)
    resp.raise_for_status()
    df = pd.DataFrame(resp.json()["results"])
    df["core_set_year"] = year
    df.to_csv(cache, index=False)
    return df


def load_all(raw_dir: Path) -> pd.DataFrame:
    return clean(pd.concat([fetch_year(y, raw_dir) for y in DATASETS], ignore_index=True))


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Keep Medicaid-inclusive poor-control (>9.0%) rows of real states with numeric rates; one row per state-year-population."""
    d = df[df["rate_definition"].str.contains("Poor Control", case=False, na=False)].copy()
    d["rate"] = pd.to_numeric(d["state_rate"], errors="coerce")
    d["state"] = d["state"].map(STATE_ABBR)
    d = d.dropna(subset=["rate", "state"])
    # Stand-alone CHIP populations are tiny and often report 0/100%; keep Medicaid-inclusive rows only.
    d = d[d["population"].str.contains("Medicaid", case=False, na=False)]
    d["year"] = d["core_set_year"].astype(int)
    return d[["state", "year", "population", "methodology", "rate"]].reset_index(drop=True)


def state_yearly(df: pd.DataFrame) -> pd.DataFrame:
    """Mean poor-control rate per state-year (mean across reported populations/methods)."""
    return df.groupby(["state", "year"], as_index=False)["rate"].mean()


def national_yearly(df: pd.DataFrame) -> pd.DataFrame:
    """Median across states reporting that year (a reporting-set effect exists; see README)."""
    s = state_yearly(df)
    out = s.groupby("year")["rate"].agg(median="median", states="count").reset_index()
    return out
