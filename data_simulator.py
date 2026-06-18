"""
data_simulator.py
Generates realistic demo data for GPS trips, daily logs, and weekly trends.
Used when no live GPS device is connected.
"""
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from activity_tracker import Trip, DailyLog, classify_activity, predict_future_impact


random.seed(42)


def simulate_gps_points(activity: str = "car", distance_km: float = 10.0,
                         n_points: int = 20) -> list[dict]:
    """Generate a fake GPS track for demonstration."""
    # Start near a generic city center
    lat, lon = 22.57, 88.36  # Kolkata, India (close to user's region)
    speed_map = {
        "walking":    random.uniform(4, 6),
        "cycling":    random.uniform(12, 20),
        "car":        random.uniform(40, 80),
        "motorbike":  random.uniform(35, 55),
        "stationary": 0,
    }
    speed_kmh = speed_map.get(activity, 30)
    points = []
    step_km = distance_km / n_points
    # Simple straight-line simulation
    for i in range(n_points):
        lat += step_km * 0.009   # ~1 km ≈ 0.009°
        lon += step_km * 0.009
        points.append({
            "lat":       round(lat + random.uniform(-0.001, 0.001), 6),
            "lon":       round(lon + random.uniform(-0.001, 0.001), 6),
            "speed_kmh": round(speed_kmh + random.uniform(-3, 3), 1),
            "timestamp": (datetime.now() + timedelta(seconds=i * 60)).isoformat(),
            "activity":  classify_activity(speed_kmh),
        })
    return points


def simulate_daily_log(day_offset: int = 0) -> DailyLog:
    """Return a realistic DailyLog for a given day."""
    log = DailyLog()
    base = datetime.now() - timedelta(days=day_offset)
    # Morning commute
    commute_mode = random.choices(
        ["car", "cycling", "walking", "motorbike"],
        weights=[50, 25, 15, 10]
    )[0]
    log.add_trip(Trip(commute_mode, random.uniform(3, 20), base.replace(hour=8), base.replace(hour=9)))
    # Lunch errand
    if random.random() > 0.4:
        mode = random.choices(["walking", "car", "cycling"], weights=[50, 30, 20])[0]
        log.add_trip(Trip(mode, random.uniform(0.5, 3), base.replace(hour=12), base.replace(hour=13)))
    # Evening commute
    log.add_trip(Trip(commute_mode, random.uniform(3, 20), base.replace(hour=17), base.replace(hour=18)))
    # Weekend leisure
    if day_offset % 7 in (0, 6):
        mode = random.choices(["cycling", "walking", "car"], weights=[40, 30, 30])[0]
        log.add_trip(Trip(mode, random.uniform(5, 30), base.replace(hour=10), base.replace(hour=11)))
    return log


def simulate_weekly_trend(n_days: int = 30) -> pd.DataFrame:
    """Return a DataFrame of daily carbon stats over the last n_days."""
    rows = []
    for d in range(n_days, -1, -1):
        log = simulate_daily_log(d)
        s   = log.summary()
        date = datetime.now() - timedelta(days=d)
        rows.append({
            "date":              date.strftime("%Y-%m-%d"),
            "total_carbon_kg":   s["total_carbon_kg"],
            "total_saved_kg":    s["total_saved_kg"],
            "total_distance_km": s["total_distance_km"],
            "trips":             s["trips"],
        })
    return pd.DataFrame(rows)


def simulate_realtime_gps_stream(n_steps: int = 10):
    """Yield simulated GPS readings one-by-one (for live demo)."""
    activity = random.choice(["walking", "cycling", "car"])
    points   = simulate_gps_points(activity, distance_km=5, n_points=n_steps)
    for p in points:
        yield p
