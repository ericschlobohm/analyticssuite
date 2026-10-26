"""CMS Care Compare hospital data access for the example dashboard (current snapshot).

Sources (CMS Provider Data Catalog, https://data.cms.gov/provider-data/):
  * Hospital General Information (xubh-q36u): overall star rating, type, ownership.
  * Unplanned Hospital Visits - Hospital (632h-zaca): pneumonia 30-day readmission rate.
These are rolling snapshots, not a time series, so the dashboard compares hospitals and states.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

SOURCES = {
    "Care Compare (consumer site)": "https://www.medicare.gov/care-compare/",
    "Provider Data Catalog: hospitals": "https://data.cms.gov/provider-data/topics/hospitals",
    "Hospital General Information": "https://data.cms.gov/provider-data/dataset/xubh-q36u",
    "Unplanned Hospital Visits - Hospital": "https://data.cms.gov/provider-data/dataset/632h-zaca",
    "Overall star rating methodology": "https://www.cms.gov/medicare/quality/initiatives/hospital-quality-initiative/overall-hospital-quality-star-rating",
}

API = "https://data.cms.gov/provider-data/api/1/datastore/query/{id}/0"
HEADERS = {"User-Agent": "curl/8.0"}
PAGE = 500


def fetch_dataset(dataset_id: str, raw_dir: Path, conditions: dict[str, str] | None = None) -> pd.DataFrame:
    """Page through a datastore query (cached as CSV). `conditions` are property=value filters."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    tag = "_".join(conditions.values()) if conditions else "all"
    cache = raw_dir / f"{dataset_id}_{tag}.csv"
    if cache.exists():
        return pd.read_csv(cache, dtype=str)
    params: dict[str, object] = {"limit": PAGE}
    for i, (prop, val) in enumerate((conditions or {}).items()):
        params[f"conditions[{i}][property]"] = prop
        params[f"conditions[{i}][value]"] = val
    frames, offset = [], 0
    while True:
        params["offset"] = offset
        resp = requests.get(API.format(id=dataset_id), params=params, headers=HEADERS, timeout=120)
        resp.raise_for_status()
        rows = resp.json()["results"]
        frames.append(pd.DataFrame(rows))
        if len(rows) < PAGE:
            break
        offset += PAGE
    df = pd.concat(frames, ignore_index=True)
    df.to_csv(cache, index=False)
    return df


def load_hospitals(raw_dir: Path) -> pd.DataFrame:
    """One row per hospital: star rating (1-5) joined to pneumonia 30-day readmission rate (%)."""
    info = fetch_dataset("xubh-q36u", raw_dir)
    readm = fetch_dataset("632h-zaca", raw_dir, {"measure_id": "READM_30_PN"})
    return clean(info, readm)


def clean(info: pd.DataFrame, readm: pd.DataFrame) -> pd.DataFrame:
    h = info[["facility_id", "facility_name", "state", "hospital_type", "hospital_ownership",
              "hospital_overall_rating"]].copy()
    h["stars"] = pd.to_numeric(h["hospital_overall_rating"], errors="coerce")
    r = readm[["facility_id", "score"]].copy()
    r["readmission_rate"] = pd.to_numeric(r["score"], errors="coerce")
    out = h.merge(r[["facility_id", "readmission_rate"]], on="facility_id", how="left")
    return out.drop(columns="hospital_overall_rating")


def state_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per state: hospital count, mean stars and readmission rate (rated hospitals only), % 4-5 star."""
    rated = df.dropna(subset=["stars"])
    g = rated.groupby("state")
    out = pd.DataFrame({
        "hospitals_rated": g.size(),
        "mean_stars": g["stars"].mean(),
        "pct_4_5_star": g["stars"].apply(lambda s: (s >= 4).mean() * 100),
    })
    out["mean_readmission_rate"] = df.dropna(subset=["readmission_rate"]).groupby("state")["readmission_rate"].mean()
    return out.reset_index()

