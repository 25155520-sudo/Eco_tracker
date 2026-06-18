"""
ai_insights.py
Uses Groq LLM to generate personalised environmental insights & predictions.
API key loaded from config (sourced from .env).
"""
import json
import requests
from config import Config


def _groq_chat(messages: list[dict], max_tokens: int = 512) -> str:
    """Raw Groq chat-completion call."""
    key = Config.GROQ_API_KEY
    if not key or key == "your_groq_api_key_here":
        return None   # caller should fall back to static text

    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":      "llama3-8b-8192",
        "messages":   messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    try:
        resp = requests.post(
            f"{Config.GROQ_BASE_URL}/openai/v1/chat/completions",
            headers=headers, json=payload, timeout=20
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"[Groq unavailable: {e}]"


# ── Public helpers ─────────────────────────────────────────────────────────

def get_daily_insight(summary: dict) -> str:
    """Generate a personalised daily eco-insight from Groq."""
    prompt = f"""
You are an environmental coach. Given this person's daily activity summary, 
provide a short (3–4 sentences), encouraging, and actionable eco-insight.

Summary:
- Total carbon emitted today: {summary.get('total_carbon_kg', 0):.3f} kg CO₂
- Carbon saved vs driving: {summary.get('total_saved_kg', 0):.3f} kg CO₂
- Activities: {json.dumps(summary.get('activity_breakdown', {}))}
- Distance: {summary.get('total_distance_km', 0):.1f} km

Mention at least one specific action they can take tomorrow.
"""
    result = _groq_chat([{"role": "user", "content": prompt}])
    if result and not result.startswith("[Groq"):
        return result
    # Fallback
    carbon = summary.get("total_carbon_kg", 0)
    saved  = summary.get("total_saved_kg",  0)
    if carbon < 0.5:
        return (
            "🌿 Fantastic day! Your low-carbon transport choices kept emissions under 0.5 kg CO₂. "
            "You're already ahead of the global average. Try swapping one car trip for a bike ride tomorrow "
            "to keep up this streak!"
        )
    elif saved > carbon:
        return (
            f"🚴 Great effort! You saved {saved:.2f} kg CO₂ compared to driving everywhere. "
            "That's the equivalent of charging dozens of smartphones. Consider meal-prepping to reduce "
            "food-delivery trips — another easy carbon win."
        )
    else:
        return (
            f"🚗 Today's carbon footprint was {carbon:.2f} kg CO₂. Small swaps add up: "
            "replacing one 5 km car trip with cycling saves ~1 kg CO₂ daily, or ~365 kg per year — "
            "about 17 mature trees' worth of absorption. Try it tomorrow!"
        )


def get_prediction_insight(projection: dict) -> str:
    """Generate an AI narrative about future carbon impact."""
    prompt = f"""
You are a climate scientist explaining future impact in plain language.
Based on this projection, write 3–4 sentences summarising the person's future 
environmental impact and one concrete behaviour change.

Projection data:
- Projected annual CO₂: {projection.get('projected_tonnes', 0):.2f} tonnes
- Trees needed to offset: {projection.get('trees_to_offset', 0):.0f}
- % of global average: {projection.get('pct_of_global_avg', 0):.1f}%
- Projection period: {projection.get('projection_days', 365)} days
"""
    result = _groq_chat([{"role": "user", "content": prompt}])
    if result and not result.startswith("[Groq"):
        return result
    # Fallback
    tonnes = projection.get("projected_tonnes", 0)
    trees  = projection.get("trees_to_offset",  0)
    pct    = projection.get("pct_of_global_avg", 100)
    return (
        f"📈 If you maintain current habits, you'll emit ~{tonnes:.2f} tonnes of CO₂ this year — "
        f"{'below' if pct < 100 else 'above'} the global average of 4.7 t. "
        f"You'd need {trees:.0f} mature trees to absorb that. "
        "Switching 30 % of car trips to cycling could cut your footprint by up to 0.4 tonnes/year."
    )


def get_eco_tips(activity_breakdown: dict) -> list[str]:
    """Return tailored eco-tips based on dominant transport mode."""
    dominant = max(activity_breakdown, key=activity_breakdown.get) if activity_breakdown else "car"
    tip_bank = {
        "car": [
            "🚗→🚌 Carpooling just twice a week cuts transport emissions by ~40 %.",
            "⚡ Electric vehicles produce 50–70 % less CO₂ over their lifetime.",
            "🛣️ Combine errands into one trip to minimise cold starts.",
            "🔧 Keeping tyres inflated to the correct pressure improves fuel efficiency by 3 %.",
        ],
        "motorbike": [
            "🏍️→🚌 Replacing one motorbike commute with public transit saves ~2 kg CO₂/trip.",
            "⚡ Electric scooters emit 80 % less CO₂ than petrol motorbikes.",
            "📱 Plan routes to avoid traffic — idling burns fuel and raises emissions.",
        ],
        "cycling": [
            "🚴 Excellent choice! Cycling 10 km daily saves ~700 kg CO₂/year vs driving.",
            "🔋 E-bikes extend range while keeping emissions near zero.",
            "🌧️ Invest in rain gear — fair-weather cycling is still cycling!",
        ],
        "walking": [
            "🚶 Walking is carbon-zero and burns calories. Keep it up!",
            "🎧 Audiobooks make long walks fly by.",
            "🌳 Choose tree-lined routes to enjoy nature while you commute.",
        ],
    }
    return tip_bank.get(dominant, tip_bank["car"])


def get_plastic_insight(personal_kg_per_year: float = 40.0) -> str:
    """AI narrative on personal plastic impact."""
    prompt = f"""
In 3 sentences, explain the environmental impact of using {personal_kg_per_year:.1f} kg of plastic 
per year and give one actionable tip to reduce plastic usage. Be concise and motivating.
"""
    result = _groq_chat([{"role": "user", "content": prompt}])
    if result and not result.startswith("[Groq"):
        return result
    co2_kg = personal_kg_per_year * 6
    return (
        f"🛍️ Using {personal_kg_per_year:.0f} kg of plastic per year generates ~{co2_kg:.0f} kg CO₂ "
        "in production alone — before counting disposal emissions. "
        "Switching to reusable bags, bottles, and containers can cut personal plastic use by up to 70 %. "
        "Start with one reusable tote bag — it replaces ~500 single-use bags over its lifetime."
    )
