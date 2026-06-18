"""
environmental_data.py
Fetches global environmental data from:
  - World Bank API
  - Global Forest Watch API
  - Our World in Data (static fallback datasets)
  - Climatiq
All API keys loaded from config (sourced from .env).
"""
import requests
import pandas as pd
import numpy as np
from config import Config


# ──────────────────────────────────────────────────────────────────────────
# WORLD BANK — CO₂ & environmental indicators
# ──────────────────────────────────────────────────────────────────────────

WB_INDICATORS = {
    "co2_per_capita":    "EN.ATM.CO2E.PC",
    "forest_area_pct":   "AG.LND.FRST.ZS",
    "forest_area_km2":   "AG.LND.FRST.K2",
    "renewable_energy":  "EG.FEC.RNEW.ZS",
    "population":        "SP.POP.TOTL",
}


def fetch_world_bank(indicator_key: str, country: str = "WLD",
                     start_year: int = 2000, end_year: int = 2022) -> pd.DataFrame:
    """Fetch a World Bank indicator time series."""
    indicator = WB_INDICATORS.get(indicator_key, indicator_key)
    url = (
        f"{Config.WORLD_BANK_BASE_URL}/country/{country}/indicator/{indicator}"
        f"?format=json&per_page=100&mrv=30&date={start_year}:{end_year}"
    )
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        raw = resp.json()
        if len(raw) < 2 or not raw[1]:
            return _fallback_wb_data(indicator_key, country)
        records = [
            {"year": int(r["date"]), "value": r["value"], "country": r["country"]["value"]}
            for r in raw[1] if r.get("value") is not None
        ]
        return pd.DataFrame(records).sort_values("year")
    except Exception:
        return _fallback_wb_data(indicator_key, country)


def _fallback_wb_data(indicator_key: str, country: str) -> pd.DataFrame:
    """Return synthetic realistic data when API is unreachable."""
    years = list(range(2000, 2023))
    fallbacks = {
        "co2_per_capita":  [4.0 + i * 0.05 for i in range(len(years))],
        "forest_area_pct": [31.0 - i * 0.05 for i in range(len(years))],
        "forest_area_km2": [40_000_000 - i * 100_000 for i in range(len(years))],
        "renewable_energy":[17.0 + i * 0.2 for i in range(len(years))],
        "population":      [6_000_000_000 + i * 80_000_000 for i in range(len(years))],
    }
    values = fallbacks.get(indicator_key, [0] * len(years))
    return pd.DataFrame({"year": years, "value": values, "country": country})


def fetch_co2_by_country(year: int = 2020) -> pd.DataFrame:
    """Return top CO₂-emitting countries for a given year."""
    countries = ["USA", "CHN", "IND", "RUS", "DEU", "GBR", "JPN", "BRA", "CAN", "AUS"]
    rows = []
    for c in countries:
        df = fetch_world_bank("co2_per_capita", c)
        subset = df[df["year"] <= year]
        if not subset.empty:
            latest = subset.iloc[-1]
            rows.append({"country": latest["country"], "co2_per_capita": latest["value"]})
    if not rows:
        rows = [
            {"country": "United States", "co2_per_capita": 14.9},
            {"country": "China",         "co2_per_capita": 7.4},
            {"country": "India",         "co2_per_capita": 1.9},
            {"country": "Russia",        "co2_per_capita": 11.4},
            {"country": "Germany",       "co2_per_capita": 7.9},
            {"country": "United Kingdom","co2_per_capita": 5.3},
            {"country": "Japan",         "co2_per_capita": 8.7},
            {"country": "Brazil",        "co2_per_capita": 2.2},
            {"country": "Canada",        "co2_per_capita": 14.2},
            {"country": "Australia",     "co2_per_capita": 15.1},
        ]
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────────────
# GLOBAL FOREST WATCH — Deforestation data
# ──────────────────────────────────────────────────────────────────────────

def fetch_forest_data(country_iso: str = "BRA") -> dict:
    """
    Fetch forest cover & deforestation stats from GFW.
    Falls back to curated dataset if key not configured.
    """
    key = Config.GFW_API_KEY
    if not key or key == "your_gfw_api_key_here":
        return _fallback_forest_data(country_iso)

    headers = {"x-api-key": key}
    url = f"{Config.GFW_BASE_URL}/dataset/umd_tree_cover_loss/latest/query"
    params = {"sql": f"SELECT * FROM data WHERE iso='{country_iso}' LIMIT 50"}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        return {"source": "gfw", "data": data, "country": country_iso}
    except Exception as e:
        return {**_fallback_forest_data(country_iso), "error": str(e)}


def _fallback_forest_data(country_iso: str) -> dict:
    FOREST_DB = {
        "BRA": {"name": "Brazil",         "forest_cover_pct": 59.4, "annual_loss_km2": 11_568, "total_forest_km2": 4_935_000},
        "IDN": {"name": "Indonesia",      "forest_cover_pct": 49.9, "annual_loss_km2":  3_752, "total_forest_km2":   895_000},
        "RUS": {"name": "Russia",         "forest_cover_pct": 49.4, "annual_loss_km2":  4_350, "total_forest_km2": 8_153_000},
        "CAN": {"name": "Canada",         "forest_cover_pct": 34.1, "annual_loss_km2":    750, "total_forest_km2": 3_470_000},
        "USA": {"name": "United States",  "forest_cover_pct": 33.9, "annual_loss_km2":  2_100, "total_forest_km2": 3_097_000},
        "COD": {"name": "DR Congo",       "forest_cover_pct": 67.5, "annual_loss_km2":  1_400, "total_forest_km2": 1_522_000},
        "AUS": {"name": "Australia",      "forest_cover_pct": 17.4, "annual_loss_km2":  1_050, "total_forest_km2": 1_311_000},
        "IND": {"name": "India",          "forest_cover_pct": 24.0, "annual_loss_km2":    210, "total_forest_km2":   721_000},
        "CHN": {"name": "China",          "forest_cover_pct": 23.0, "annual_loss_km2":    100, "total_forest_km2": 2_200_000},
        "GBR": {"name": "United Kingdom", "forest_cover_pct": 13.1, "annual_loss_km2":     10, "total_forest_km2":    32_000},
    }
    info = FOREST_DB.get(country_iso, {
        "name": country_iso, "forest_cover_pct": 25.0,
        "annual_loss_km2": 500, "total_forest_km2": 500_000,
    })
    return {"source": "local_db", "country": country_iso, **info}


def get_global_forest_summary() -> dict:
    """Return global forest statistics."""
    return {
        "total_forest_bn_ha":    4.06,
        "pct_earth_land":        31.0,
        "annual_loss_mha":       10.0,
        "annual_gain_mha":        5.0,
        "net_loss_mha_per_year":  5.0,
        "primary_forest_bn_ha":   1.11,
        "deforestation_causes": {
            "Agriculture":          73,
            "Forestry":             10,
            "Wildfire":              3,
            "Urbanization":          3,
            "Infrastructure":        2,
            "Other":                 9,
        },
        "co2_from_deforestation_gt_yr": 4.8,
    }


# ──────────────────────────────────────────────────────────────────────────
# PLASTIC DATA — OWID + curated statistics
# ──────────────────────────────────────────────────────────────────────────

def fetch_plastic_data() -> dict:
    """Return global and per-capita plastic usage statistics."""
    global_stats = {
        "annual_production_mt":         400,
        "annual_mismanaged_mt":          81,
        "ocean_plastic_mt_cumulative":    8,
        "recycling_rate_pct":             9,
        "incineration_rate_pct":         12,
        "landfill_rate_pct":             79,
        "plastic_bags_per_year_billion": 500,
        "co2_plastic_production_mt":    1_800,  # million tonnes CO₂ per year
        "single_use_plastic_pct":        40,
    }

    per_country = [
        {"country": "United States", "kg_per_capita": 105.3, "recycling_pct": 9},
        {"country": "China",         "kg_per_capita":  59.1, "recycling_pct": 25},
        {"country": "India",         "kg_per_capita":  12.9, "recycling_pct": 30},
        {"country": "Germany",       "kg_per_capita":  81.3, "recycling_pct": 38},
        {"country": "Brazil",        "kg_per_capita":  37.6, "recycling_pct": 4},
        {"country": "Japan",         "kg_per_capita":  66.9, "recycling_pct": 14},
        {"country": "Australia",     "kg_per_capita":  59.4, "recycling_pct": 12},
        {"country": "UK",            "kg_per_capita":  99.0, "recycling_pct": 45},
    ]

    plastic_facts = [
        "Producing 1 kg of plastic emits ~6 kg CO₂ equivalent.",
        "Plastic bags take 10–1,000 years to decompose.",
        "Only 9 % of all plastic ever produced has been recycled.",
        "Microplastics have been found in human blood and lungs.",
        "Plastic incineration releases dioxins and greenhouse gases.",
        "Marine plastic kills over 1 million seabirds annually.",
        "Single-use plastics account for 40 % of all plastic produced.",
        "The Great Pacific Garbage Patch is twice the size of Texas.",
    ]

    return {
        "global":      global_stats,
        "per_country": per_country,
        "facts":       plastic_facts,
    }


# ──────────────────────────────────────────────────────────────────────────
# TREE PLANTATION — offset modeling
# ──────────────────────────────────────────────────────────────────────────

def calculate_trees_needed(annual_co2_kg: float) -> dict:
    """Calculate trees required to offset personal annual emissions."""
    trees_personal     = annual_co2_kg / Config.CO2_PER_TREE_PER_YEAR_KG
    global_pop         = 8_100_000_000
    global_avg_co2_kg  = 4_700        # kg/year global average
    trees_global_needed = (global_avg_co2_kg * global_pop) / Config.CO2_PER_TREE_PER_YEAR_KG

    return {
        "personal_trees_needed":      round(trees_personal, 1),
        "annual_co2_kg":              round(annual_co2_kg, 2),
        "global_trees_needed_bn":     round(trees_global_needed / 1e9, 2),
        "trees_planted_per_year_bn":  15.0,   # current planting rate ~15 bn/yr
        "trees_cut_per_year_bn":      15.0,   # roughly equal = net zero gain
        "trees_needed_total_bn":      round(trees_global_needed / 1e9, 2),
        "deficit_bn":                 round((trees_global_needed / 1e9) - 15, 2),
        "co2_per_tree_kg_yr":         Config.CO2_PER_TREE_PER_YEAR_KG,
    }
