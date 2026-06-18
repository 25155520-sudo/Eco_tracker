"""
config.py - Centralized configuration & API key loader
All keys are read exclusively from the .env file.
"""
import os
from dotenv import load_dotenv

# Load .env from the project root
load_dotenv()

class Config:
    # ── API Keys ──────────────────────────────────────────────
    CLIMATIQ_API_KEY        = os.getenv("CLIMATIQ_API_KEY", "")
    GFW_API_KEY             = os.getenv("GLOBAL_FOREST_WATCH_API_KEY", "")
    WORLD_BANK_API_KEY      = os.getenv("WORLD_BANK_API_KEY", "")
    OWID_API_KEY            = os.getenv("OWID_API_KEY", "")
    NOMINATIM_API_KEY       = os.getenv("NOMINATIM_API_KEY", "")
    GROQ_API_KEY            = os.getenv("GROQ_API_KEY", "")

    # ── App Settings ──────────────────────────────────────────
    DEBUG     = os.getenv("APP_DEBUG", "True").lower() == "true"
    HOST      = os.getenv("APP_HOST", "0.0.0.0")
    PORT      = int(os.getenv("APP_PORT", "8501"))

    # ── API Base URLs ─────────────────────────────────────────
    CLIMATIQ_BASE_URL  = "https://beta3.api.climatiq.io"
    GFW_BASE_URL       = "https://data-api.globalforestwatch.org"
    WORLD_BANK_BASE_URL = "https://api.worldbank.org/v2"
    OWID_BASE_URL      = "https://ourworldindata.org"
    NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"
    GROQ_BASE_URL      = "https://api.groq.com"

    # ── Carbon Emission Factors (kg CO₂ per km) ───────────────
    EMISSION_FACTORS = {
        "walking":  0.000,
        "cycling":  0.000,
        "car":      0.192,   # average petrol car
        "motorbike":0.103,
        "bus":      0.089,
        "train":    0.041,
    }

    # ── Trees needed to absorb 1 tonne CO₂/year ──────────────
    CO2_PER_TREE_PER_YEAR_KG = 21.77   # ~21.77 kg CO₂/year per mature tree

    @classmethod
    def validate(cls):
        """Return a dict of which keys are configured vs missing."""
        status = {
            "Climatiq":         bool(cls.CLIMATIQ_API_KEY and cls.CLIMATIQ_API_KEY != "your_climatiq_api_key_here"),
            "Global Forest Watch": bool(cls.GFW_API_KEY and cls.GFW_API_KEY != "your_gfw_api_key_here"),
            "Groq AI":          bool(cls.GROQ_API_KEY and cls.GROQ_API_KEY != "your_groq_api_key_here"),
            "World Bank":       True,   # no key needed
            "OWID":             True,   # no key needed
            "Nominatim/OSM":    True,   # no key needed
        }
        return status
