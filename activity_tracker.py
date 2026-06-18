"""
activity_tracker.py
GPS-based activity classification + carbon emission calculations.
"""
import math
import requests
from datetime import datetime, timedelta
from config import Config


# ── Speed thresholds (km/h) ────────────────────────────────────────────────
SPEED_THRESHOLDS = {
    "stationary": (0,   2),
    "walking":    (2,   7),
    "cycling":    (7,   25),
    "motorbike":  (25,  60),
    "car":        (25,  200),
}


def haversine_distance(lat1, lon1, lat2, lon2) -> float:
    """Return great-circle distance in km between two GPS coordinates."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi       = math.radians(lat2 - lat1)
    dlambda    = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def classify_activity(speed_kmh: float) -> str:
    """Classify transport mode from GPS speed (km/h)."""
    if speed_kmh < 2:
        return "stationary"
    elif speed_kmh < 7:
        return "walking"
    elif speed_kmh < 25:
        return "cycling"
    elif speed_kmh < 60:
        return "motorbike"
    else:
        return "car"


def calculate_carbon(activity: str, distance_km: float) -> float:
    """Return kg CO₂ emitted for a given activity over distance_km."""
    factor = Config.EMISSION_FACTORS.get(activity, 0.0)
    return factor * distance_km


def carbon_saved_vs_car(activity: str, distance_km: float) -> float:
    """Return kg CO₂ saved compared to driving the same distance by car."""
    car_emissions   = Config.EMISSION_FACTORS["car"] * distance_km
    act_emissions   = calculate_carbon(activity, distance_km)
    return max(0.0, car_emissions - act_emissions)


# ── Session / trip data structures ────────────────────────────────────────

class Trip:
    def __init__(self, activity: str, distance_km: float,
                 start_time: datetime = None, end_time: datetime = None):
        self.activity    = activity
        self.distance_km = distance_km
        self.start_time  = start_time or datetime.now()
        self.end_time    = end_time   or datetime.now()
        self.carbon_kg   = calculate_carbon(activity, distance_km)
        self.saved_kg    = carbon_saved_vs_car(activity, distance_km)

    def to_dict(self):
        return {
            "activity":    self.activity,
            "distance_km": round(self.distance_km, 3),
            "carbon_kg":   round(self.carbon_kg,   4),
            "saved_kg":    round(self.saved_kg,     4),
            "start_time":  self.start_time.isoformat(),
            "end_time":    self.end_time.isoformat(),
        }


class DailyLog:
    def __init__(self):
        self.trips: list[Trip] = []

    def add_trip(self, trip: Trip):
        self.trips.append(trip)

    @property
    def total_carbon_kg(self) -> float:
        return sum(t.carbon_kg for t in self.trips)

    @property
    def total_saved_kg(self) -> float:
        return sum(t.saved_kg for t in self.trips)

    @property
    def total_distance_km(self) -> float:
        return sum(t.distance_km for t in self.trips)

    def activity_breakdown(self) -> dict:
        breakdown = {}
        for t in self.trips:
            breakdown[t.activity] = breakdown.get(t.activity, 0) + t.distance_km
        return breakdown

    def summary(self) -> dict:
        return {
            "total_carbon_kg":   round(self.total_carbon_kg, 4),
            "total_saved_kg":    round(self.total_saved_kg,  4),
            "total_distance_km": round(self.total_distance_km, 3),
            "trips":             len(self.trips),
            "activity_breakdown": self.activity_breakdown(),
        }


# ── Climatiq API integration ───────────────────────────────────────────────

def get_climatiq_emission(activity: str, distance_km: float) -> dict:
    """
    Call Climatiq API for accurate emission data.
    Falls back to local factors if the key is not configured.
    """
    key = Config.CLIMATIQ_API_KEY
    if not key or key == "your_climatiq_api_key_here":
        # Graceful fallback
        return {
            "source":     "local_model",
            "carbon_kg":  calculate_carbon(activity, distance_km),
            "activity":   activity,
            "distance_km": distance_km,
        }

    # Map our activities to Climatiq emission factors
    factor_map = {
        "car":       "passenger_vehicle-vehicle_type_car-fuel_source_petrol-engine_size_na-vehicle_age_na-vehicle_weight_na",
        "motorbike": "passenger_vehicle-vehicle_type_motorbike-fuel_source_petrol-engine_size_na-vehicle_age_na-vehicle_weight_na",
        "bus":       "passenger_vehicle-vehicle_type_bus-fuel_source_na-engine_size_na-vehicle_age_na-vehicle_weight_na",
        "train":     "passenger_vehicle-vehicle_type_rail-fuel_source_na-engine_size_na-vehicle_age_na-vehicle_weight_na",
    }

    if activity in ("walking", "cycling", "stationary"):
        return {"source": "local_model", "carbon_kg": 0.0, "activity": activity}

    factor_id = factor_map.get(activity)
    if not factor_id:
        return {"source": "local_model", "carbon_kg": calculate_carbon(activity, distance_km)}

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
    }
    payload = {
        "emission_factor": {"activity_id": factor_id},
        "parameters": {
            "passengers":   1,
            "distance":     distance_km,
            "distance_unit": "km",
        },
    }
    try:
        resp = requests.post(
            f"{Config.CLIMATIQ_BASE_URL}/estimate",
            json=payload, headers=headers, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "source":     "climatiq",
            "carbon_kg":  data.get("co2e", calculate_carbon(activity, distance_km)),
            "activity":   activity,
            "distance_km": distance_km,
        }
    except Exception as e:
        return {
            "source":     "local_model",
            "carbon_kg":  calculate_carbon(activity, distance_km),
            "error":      str(e),
        }


# ── Prediction helpers ─────────────────────────────────────────────────────

def predict_future_impact(daily_carbon_kg: float, days: int = 365) -> dict:
    """Project emissions forward and calculate trees needed to offset."""
    annual_kg       = daily_carbon_kg * days
    annual_tonnes   = annual_kg / 1000
    trees_needed    = annual_kg / Config.CO2_PER_TREE_PER_YEAR_KG

    # Global average for comparison: ~4.7 tonnes CO₂/person/year
    global_avg_tonnes = 4.7
    pct_of_global     = (annual_tonnes / global_avg_tonnes) * 100 if global_avg_tonnes else 0

    return {
        "projection_days":    days,
        "projected_carbon_kg": round(annual_kg, 2),
        "projected_tonnes":   round(annual_tonnes, 4),
        "trees_to_offset":    round(trees_needed, 1),
        "pct_of_global_avg":  round(pct_of_global, 1),
    }
