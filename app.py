"""
app.py — EcoTracker Complete Streamlit Application
Run: streamlit run app.py
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time, json

from config import Config
from activity_tracker import (
    classify_activity, calculate_carbon, carbon_saved_vs_car,
    predict_future_impact, get_climatiq_emission, Trip, DailyLog,
)
from environmental_data import (
    fetch_world_bank, fetch_co2_by_country,
    fetch_forest_data, get_global_forest_summary,
    fetch_plastic_data, calculate_trees_needed,
)
from ai_insights import (
    get_daily_insight, get_prediction_insight,
    get_eco_tips, get_plastic_insight,
)
from data_simulator import simulate_weekly_trend, simulate_daily_log, simulate_gps_points

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="🌍 EcoTracker",
    page_icon="🌿",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Dark background */
.main .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }

/* ── KPI Cards ── */
.kpi-grid { display:flex; gap:16px; margin-bottom:16px; flex-wrap:wrap; }
.kpi-card {
    flex:1; min-width:140px;
    background:linear-gradient(145deg,#0f2319,#162d1e);
    border:1px solid #2e5c35;
    border-radius:14px;
    padding:18px 20px;
    text-align:center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    transition: transform 0.2s;
}
.kpi-card:hover { transform:translateY(-2px); }
.kpi-icon  { font-size:2rem; }
.kpi-value { font-size:1.7rem; font-weight:700; color:#56d364; margin:4px 0; }
.kpi-label { font-size:0.78rem; color:#8b949e; letter-spacing:0.03em; }

/* ── Alert boxes ── */
.alert-green {
    background:linear-gradient(135deg,#0d2818,#1a3d22);
    border-left:4px solid #56d364;
    border-radius:8px; padding:14px 16px; margin:10px 0;
    color:#c8e6c9; font-size:0.92rem; line-height:1.5;
}
.alert-orange {
    background:linear-gradient(135deg,#2d1a00,#3d2600);
    border-left:4px solid #f0a500;
    border-radius:8px; padding:14px 16px; margin:10px 0;
    color:#ffe0a3; font-size:0.92rem; line-height:1.5;
}
.alert-blue {
    background:linear-gradient(135deg,#001d3d,#00305a);
    border-left:4px solid #58a6ff;
    border-radius:8px; padding:14px 16px; margin:10px 0;
    color:#cae8ff; font-size:0.92rem; line-height:1.5;
}

/* ── Section headers ── */
.sec-header {
    font-size:1.2rem; font-weight:700; color:#56d364;
    border-bottom:1px solid #2e5c35; padding-bottom:6px; margin:20px 0 12px;
}

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background:linear-gradient(180deg,#0d1f12 0%,#0a1a0e 100%);
    border-right:1px solid #2e5c35;
}
[data-testid="stSidebar"] .stRadio label { color:#c8e6c9; }
[data-testid="stSidebar"] h1 { color:#56d364; }

/* ── Metric tweaks ── */
[data-testid="stMetricValue"]  { color:#56d364 !important; font-size:1.5rem !important; }
[data-testid="stMetricLabel"]  { color:#8b949e !important; }
[data-testid="stMetricDelta"]  { font-size:0.8rem !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { background:#0f1f14; border-radius:8px; }
.stTabs [data-baseweb="tab"]      { color:#8b949e; }
.stTabs [aria-selected="true"]    { color:#56d364 !important; background:#162d1e; border-radius:6px; }

/* ── Progress bar ── */
.stProgress > div > div { background:#56d364 !important; }

/* ── Fact card ── */
.fact-card {
    background:#0f1f14; border:1px solid #2e5c35;
    border-radius:10px; padding:12px 16px; margin:6px 0;
    color:#c8e6c9; font-size:0.88rem;
}

/* ── Live badge ── */
.live-badge {
    display:inline-block; background:#f44336;
    color:white; font-size:0.7rem; font-weight:700;
    padding:2px 8px; border-radius:20px; margin-left:8px;
    animation: pulse 1.5s infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.5} }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# COLOUR HELPERS
# ─────────────────────────────────────────────────────────────────────────────
PLOT_LAYOUT = dict(
    paper_bgcolor="#0d1f12",
    plot_bgcolor="#0d1f12",
    font_color="#c8e6c9",
    margin=dict(l=20, r=20, t=40, b=20),
    xaxis=dict(gridcolor="#1e3a22"),
    yaxis=dict(gridcolor="#1e3a22"),
)
COLORS = dict(
    green="#56d364", red="#f44336", orange="#f0a500",
    blue="#58a6ff", purple="#bc8cff", teal="#39d0d8",
)

# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE INIT
# ─────────────────────────────────────────────────────────────────────────────
if "daily_log"  not in st.session_state:
    st.session_state.daily_log  = simulate_daily_log(0)
if "weekly_df"  not in st.session_state:
    st.session_state.weekly_df  = simulate_weekly_trend(30)
if "history_df" not in st.session_state:
    rows = []
    for d in range(90, -1, -1):
        log = simulate_daily_log(d)
        s   = log.summary()
        rows.append({"date": (datetime.now()-timedelta(days=d)).strftime("%Y-%m-%d"), **s})
    st.session_state.history_df = pd.DataFrame(rows)

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center;padding:10px 0 6px'>
      <span style='font-size:3rem'>🌿</span><br>
      <span style='font-size:1.6rem;font-weight:800;color:#56d364'>EcoTracker</span><br>
      <span style='font-size:0.75rem;color:#8b949e'>Smart Environmental System</span>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    page = st.radio("", [
        "🏠  Dashboard",
        "🚶  Activity Tracker",
        "🌎  Global Context",
        "🛍️  Plastic Awareness",
        "🌲  Forest Analytics",
        "🌱  Tree Planting Model",
        "🤖  AI Insights",
        "⚙️  API Status",
    ], label_visibility="collapsed")

    st.divider()
    st.markdown('<p style="color:#56d364;font-weight:700;font-size:0.9rem">⚡ Quick Log Trip</p>', unsafe_allow_html=True)
    qa = st.selectbox("Mode", ["walking","cycling","car","motorbike"], key="qa")
    qd = st.number_input("Distance (km)", 0.1, 500.0, 5.0, step=0.5, key="qd")
    if st.button("➕ Add Trip", use_container_width=True):
        st.session_state.daily_log.add_trip(Trip(qa, qd))
        st.success(f"✅ {qd:.1f} km {qa} added!")

    st.divider()
    log     = st.session_state.daily_log
    summary = log.summary()
    st.markdown(f"""
    <div style='font-size:0.8rem;color:#8b949e'>
    Today: <span style='color:#56d364;font-weight:700'>{summary['total_carbon_kg']:.3f} kg CO₂</span><br>
    Saved: <span style='color:#58a6ff;font-weight:700'>{summary['total_saved_kg']:.3f} kg</span><br>
    Trips: <span style='color:#c8e6c9'>{summary['trips']}</span>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ██  DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
if page == "🏠  Dashboard":
    st.markdown(f"## 🌍 EcoTracker Dashboard")
    st.caption(f"📅 {datetime.now().strftime('%A, %d %B %Y')} · Simulated Demo Mode")

    log     = st.session_state.daily_log
    summary = log.summary()
    wdf     = st.session_state.weekly_df
    hdf     = st.session_state.history_df

    daily_c      = summary["total_carbon_kg"]
    global_daily = 4700 / 365
    pct_global   = (daily_c / global_daily) * 100
    trees_yr     = (daily_c * 365) / Config.CO2_PER_TREE_PER_YEAR_KG

    # ── KPI Cards ──────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-icon">🔥</div>
        <div class="kpi-value">{daily_c:.3f}</div>
        <div class="kpi-label">kg CO₂ Today</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">💚</div>
        <div class="kpi-value">{summary['total_saved_kg']:.3f}</div>
        <div class="kpi-label">kg CO₂ Saved</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">🚗</div>
        <div class="kpi-value">{summary['total_distance_km']:.1f}</div>
        <div class="kpi-label">km Travelled</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">🌳</div>
        <div class="kpi-value">{trees_yr:.1f}</div>
        <div class="kpi-label">Trees to Offset/yr</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">🌍</div>
        <div class="kpi-value">{pct_global:.0f}%</div>
        <div class="kpi-label">of Global Daily Avg</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Charts row ─────────────────────────────────────────────────────────
    c1, c2 = st.columns([3, 2])

    with c1:
        st.markdown('<div class="sec-header">📊 30-Day Carbon Trend</div>', unsafe_allow_html=True)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=wdf["date"], y=wdf["total_carbon_kg"],
            name="CO₂ Emitted", fill="tozeroy",
            line=dict(color=COLORS["red"], width=2),
            fillcolor="rgba(244,67,54,0.15)",
        ))
        fig.add_trace(go.Scatter(
            x=wdf["date"], y=wdf["total_saved_kg"],
            name="CO₂ Saved", fill="tozeroy",
            line=dict(color=COLORS["green"], width=2),
            fillcolor="rgba(86,211,100,0.15)",
        ))
        fig.update_layout(**PLOT_LAYOUT, height=280, legend=dict(orientation="h", y=1.15))
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown('<div class="sec-header">🚶 Activity Mix</div>', unsafe_allow_html=True)
        ab = summary["activity_breakdown"]
        if ab:
            fig2 = px.pie(
                values=list(ab.values()), names=list(ab.keys()),
                color_discrete_sequence=[COLORS["green"], COLORS["blue"], COLORS["orange"], COLORS["purple"]],
                hole=0.5,
            )
            fig2.update_traces(textposition="inside", textinfo="percent+label")
            fig2.update_layout(**PLOT_LAYOUT, height=280, showlegend=False)
            st.plotly_chart(fig2, use_container_width=True)

    # ── 90-day history ──────────────────────────────────────────────────────
    st.markdown('<div class="sec-header">📈 90-Day History</div>', unsafe_allow_html=True)
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        x=hdf["date"], y=hdf["total_carbon_kg"],
        name="Daily CO₂",
        marker_color=hdf["total_carbon_kg"].apply(
            lambda v: COLORS["green"] if v < 1 else COLORS["orange"] if v < 3 else COLORS["red"]
        ),
    ))
    # 7-day rolling avg
    hdf["rolling_avg"] = hdf["total_carbon_kg"].rolling(7).mean()
    fig3.add_trace(go.Scatter(
        x=hdf["date"], y=hdf["rolling_avg"],
        name="7-day avg", line=dict(color=COLORS["blue"], width=2, dash="dash"),
    ))
    fig3.update_layout(**PLOT_LAYOUT, height=220,
                       legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig3, use_container_width=True)

    # ── AI Insight + trips ─────────────────────────────────────────────────
    c3, c4 = st.columns([3, 2])
    with c3:
        st.markdown('<div class="sec-header">🤖 Today\'s AI Insight</div>', unsafe_allow_html=True)
        insight = get_daily_insight(summary)
        st.markdown(f'<div class="alert-green">{insight}</div>', unsafe_allow_html=True)

        # Eco tips
        tips = get_eco_tips(summary["activity_breakdown"])
        st.markdown('<div class="sec-header">💡 Quick Tips</div>', unsafe_allow_html=True)
        for tip in tips[:3]:
            st.markdown(f'<div class="fact-card">{tip}</div>', unsafe_allow_html=True)

    with c4:
        st.markdown('<div class="sec-header">📋 Today\'s Trips</div>', unsafe_allow_html=True)
        if log.trips:
            for t in log.trips:
                icon = {"walking":"🚶","cycling":"🚴","car":"🚗","motorbike":"🏍️","stationary":"🧍"}.get(t.activity,"🚗")
                st.markdown(f"""
                <div class="fact-card">
                  {icon} <b>{t.activity.title()}</b> · {t.distance_km:.1f} km<br>
                  <span style='color:#f44336'>▲ {t.carbon_kg:.4f} kg CO₂</span>
                  &nbsp;|&nbsp;
                  <span style='color:#56d364'>💚 {t.saved_kg:.4f} kg saved</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No trips yet. Use the sidebar to log one.")

# ─────────────────────────────────────────────────────────────────────────────
# ██  ACTIVITY TRACKER
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🚶  Activity Tracker":
    st.markdown("## 📡 Activity Tracker")
    st.caption("GPS-based movement detection · Carbon calculation · Climatiq API integration")

    tab1, tab2, tab3 = st.tabs(["🗺️ Live GPS Simulation", "📝 Manual Entry", "🔮 Predictions"])

    # ── Tab 1: Live GPS ────────────────────────────────────────────────────
    with tab1:
        st.markdown("""
        <div class="alert-blue">
        Simulates a real GPS track. Speed is used to auto-detect activity type.
        Emissions are calculated using Climatiq API (falls back to local model if key not set).
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3 = st.columns(3)
        with c1: sim_act  = st.selectbox("Transport Mode", ["walking","cycling","car","motorbike"])
        with c2: sim_dist = st.slider("Distance (km)", 0.5, 50.0, 10.0)
        with c3: sim_pts  = st.slider("GPS Points", 10, 60, 20)

        if st.button("▶️ Start GPS Simulation", use_container_width=True, type="primary"):
            pts      = simulate_gps_points(sim_act, sim_dist, sim_pts)
            progress = st.progress(0, text="Tracking…")
            status   = st.empty()
            live_ph  = st.empty()
            speeds, co2s, lats, lons = [], [], [], []

            for i, pt in enumerate(pts):
                progress.progress((i+1)/len(pts), text=f"Point {i+1}/{len(pts)}")
                speeds.append(pt["speed_kmh"])
                co2s.append(calculate_carbon(pt["activity"], sim_dist / sim_pts))
                lats.append(pt["lat"]); lons.append(pt["lon"])

                status.markdown(f"""
                <div class="fact-card">
                  📍 <b>Point {i+1}/{len(pts)}</b> &nbsp;|&nbsp;
                  Speed: <code>{pt['speed_kmh']} km/h</code> &nbsp;|&nbsp;
                  Mode: <code>{pt['activity']}</code> &nbsp;|&nbsp;
                  Lat: <code>{pt['lat']}</code> Lon: <code>{pt['lon']}</code>
                </div>
                """, unsafe_allow_html=True)

                cumco2 = [sum(co2s[:j+1]) for j in range(len(co2s))]
                fig = make_subplots(rows=1, cols=2,
                                    subplot_titles=("Speed (km/h)", "Cumulative CO₂ (kg)"))
                fig.add_trace(go.Scatter(y=speeds, line=dict(color=COLORS["blue"],  width=2), name="Speed"), 1, 1)
                fig.add_trace(go.Scatter(y=cumco2, line=dict(color=COLORS["red"], width=2), name="CO₂"), 1, 2)
                fig.update_layout(**PLOT_LAYOUT, height=220, showlegend=False)
                live_ph.plotly_chart(fig, use_container_width=True)
                time.sleep(0.08)

            progress.empty()
            total_co2 = sum(co2s)
            saved     = carbon_saved_vs_car(sim_act, sim_dist)
            st.session_state.daily_log.add_trip(Trip(sim_act, sim_dist))

            c1, c2, c3 = st.columns(3)
            c1.metric("CO₂ Emitted",         f"{total_co2:.4f} kg")
            c2.metric("Saved vs Driving",     f"{saved:.4f} kg")
            c3.metric("Avg Speed",            f"{np.mean(speeds):.1f} km/h")

            # Map path
            st.markdown('<div class="sec-header">🗺️ Trip Path (Simulated)</div>', unsafe_allow_html=True)
            map_df = pd.DataFrame({"lat": lats, "lon": lons})
            st.map(map_df, zoom=13, color="#56d364")

    # ── Tab 2: Manual Entry ────────────────────────────────────────────────
    with tab2:
        st.markdown('<div class="sec-header">📝 Log Trips Manually</div>', unsafe_allow_html=True)
        n = st.number_input("Number of trips to log", 1, 8, 3)
        cols_data = []
        for i in range(int(n)):
            c1, c2, c3 = st.columns([2, 2, 1])
            with c1: m = st.selectbox(f"Trip {i+1} — Mode", ["walking","cycling","car","motorbike","bus","train"], key=f"mm{i}")
            with c2: d = st.number_input(f"Distance (km)", 0.1, 500.0, 5.0, key=f"dd{i}")
            with c3:
                emi = get_climatiq_emission(m, d)
                st.metric("Est. CO₂", f"{emi['carbon_kg']:.4f} kg")
            cols_data.append((m, d))

        if st.button("💾 Save All Trips", type="primary", use_container_width=True):
            for m, d in cols_data:
                st.session_state.daily_log.add_trip(Trip(m, d))
            s = st.session_state.daily_log.summary()
            st.success(f"✅ Saved! Today total: **{s['total_carbon_kg']:.3f} kg CO₂** | Saved: **{s['total_saved_kg']:.3f} kg**")

    # ── Tab 3: Predictions ─────────────────────────────────────────────────
    with tab3:
        st.markdown('<div class="sec-header">🔮 Future Impact Prediction</div>', unsafe_allow_html=True)
        log     = st.session_state.daily_log
        summary = log.summary()
        days    = st.slider("Project forward (days)", 30, 730, 365)
        proj    = predict_future_impact(summary["total_carbon_kg"], days)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric(f"CO₂ in {days}d",   f"{proj['projected_tonnes']:.2f} t")
        c2.metric("Trees Needed",       f"{proj['trees_to_offset']:.0f}")
        c3.metric("vs Global Avg",      f"{proj['pct_of_global_avg']:.0f}%")
        c4.metric("Daily Rate",         f"{summary['total_carbon_kg']:.3f} kg/day")

        # Projection chart
        future_days  = list(range(1, days+1, max(1, days//60)))
        future_co2   = [summary["total_carbon_kg"] * d / 1000 for d in future_days]
        global_proj  = [4.7 * d / 365 for d in future_days]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=future_days, y=future_co2,
                                 name="Your Trajectory", line=dict(color=COLORS["green"], width=2.5)))
        fig.add_trace(go.Scatter(x=future_days, y=global_proj,
                                 name="Global Average", line=dict(color=COLORS["orange"], width=2, dash="dash")))
        fig.update_layout(**PLOT_LAYOUT, height=300,
                          xaxis_title="Days", yaxis_title="Cumulative CO₂ (tonnes)",
                          legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig, use_container_width=True)

        text = get_prediction_insight(proj)
        st.markdown(f'<div class="alert-orange">{text}</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ██  GLOBAL CONTEXT
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🌎  Global Context":
    st.markdown("## 🌎 Global Carbon Context")

    log          = st.session_state.daily_log
    summary      = log.summary()
    annual_t     = summary["total_carbon_kg"] * 365 / 1000
    global_avg_t = 4.7

    # KPI
    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-icon">👤</div>
        <div class="kpi-value">{annual_t:.2f} t</div>
        <div class="kpi-label">Your Annual CO₂</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">🌍</div>
        <div class="kpi-value">4.70 t</div>
        <div class="kpi-label">Global Average</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">🇺🇸</div>
        <div class="kpi-value">14.9 t</div>
        <div class="kpi-label">US Average</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">🇮🇳</div>
        <div class="kpi-value">1.9 t</div>
        <div class="kpi-label">India Average</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">{'✅' if annual_t < global_avg_t else '⚠️'}</div>
        <div class="kpi-value">{annual_t - global_avg_t:+.2f} t</div>
        <div class="kpi-label">vs Global Avg</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="sec-header">🏆 You vs The World</div>', unsafe_allow_html=True)
        labels = ["You", "Global", "US", "EU", "China", "India", "UK"]
        vals   = [annual_t, 4.7, 14.9, 7.3, 7.4, 1.9, 5.3]
        colors = [COLORS["green"] if annual_t < 4.7 else COLORS["red"]] + \
                 [COLORS["blue"], "#e53935", "#fb8c00", "#ef5350", "#43a047", "#7986cb"]
        fig = go.Figure(go.Bar(
            x=labels, y=vals, marker_color=colors,
            text=[f"{v:.1f}t" for v in vals], textposition="outside",
        ))
        fig.update_layout(**PLOT_LAYOUT, height=320, yaxis_title="tonnes CO₂/year")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown('<div class="sec-header">🌍 CO₂ by Country (per capita)</div>', unsafe_allow_html=True)
        cdf = fetch_co2_by_country()
        fig2 = px.bar(cdf.sort_values("co2_per_capita"),
                      x="co2_per_capita", y="country", orientation="h",
                      color="co2_per_capita",
                      color_continuous_scale=["#1a3a22","#56d364","#f0a500","#f44336"],
                      text=cdf["co2_per_capita"].map(lambda x: f"{x:.1f}"),
                      labels={"co2_per_capita": "t CO₂/capita"})
        fig2.update_layout(**PLOT_LAYOUT, height=320, coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)

    # World trend
    st.markdown('<div class="sec-header">📈 World CO₂ Trend (World Bank Data)</div>', unsafe_allow_html=True)
    with st.spinner("Fetching World Bank data…"):
        wdf = fetch_world_bank("co2_per_capita", "WLD")
    fig3 = go.Figure()
    fig3.add_trace(go.Scatter(
        x=wdf["year"], y=wdf["value"], mode="lines+markers",
        line=dict(color=COLORS["orange"], width=2.5),
        fill="tozeroy", fillcolor="rgba(240,165,0,0.1)",
        name="Global avg t CO₂/capita",
    ))
    fig3.update_layout(**PLOT_LAYOUT, height=260,
                       xaxis_title="Year", yaxis_title="t CO₂/capita")
    st.plotly_chart(fig3, use_container_width=True)

    # Renewable energy
    st.markdown('<div class="sec-header">⚡ Renewable Energy Share (World)</div>', unsafe_allow_html=True)
    with st.spinner("Fetching renewable energy data…"):
        rdf = fetch_world_bank("renewable_energy", "WLD")
    fig4 = px.area(rdf, x="year", y="value",
                   labels={"value":"% of final energy"},
                   color_discrete_sequence=[COLORS["teal"]])
    fig4.update_layout(**PLOT_LAYOUT, height=220)
    st.plotly_chart(fig4, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# ██  PLASTIC AWARENESS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🛍️  Plastic Awareness":
    st.markdown("## 🛍️ Plastic Usage & Environmental Impact")

    plastic = fetch_plastic_data()
    g       = plastic["global"]

    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-icon">🏭</div>
        <div class="kpi-value">{g['annual_production_mt']}</div>
        <div class="kpi-label">Mt Plastic / Year</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">🗑️</div>
        <div class="kpi-value">{g['annual_mismanaged_mt']}</div>
        <div class="kpi-label">Mt Mismanaged</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">♻️</div>
        <div class="kpi-value">{g['recycling_rate_pct']}%</div>
        <div class="kpi-label">Recycled</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">🌊</div>
        <div class="kpi-value">{g['ocean_plastic_mt_cumulative']} Mt</div>
        <div class="kpi-label">In Oceans (total)</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">💨</div>
        <div class="kpi-value">{g['co2_plastic_production_mt']:,}</div>
        <div class="kpi-label">Mt CO₂ from Plastic/yr</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="sec-header">🗑️ Plastic End-of-Life Fate</div>', unsafe_allow_html=True)
        fig = px.pie(
            values=[g["recycling_rate_pct"], g["incineration_rate_pct"], g["landfill_rate_pct"]],
            names=["Recycled ♻️", "Incinerated 🔥", "Landfill / Ocean 🌊"],
            color_discrete_sequence=[COLORS["green"], COLORS["orange"], COLORS["red"]],
            hole=0.45,
        )
        fig.update_traces(textposition="outside", textinfo="percent+label")
        fig.update_layout(**PLOT_LAYOUT, height=300, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown('<div class="sec-header">🌍 Plastic Per Capita by Country</div>', unsafe_allow_html=True)
        pc_df = pd.DataFrame(plastic["per_country"]).sort_values("kg_per_capita")
        fig2  = px.bar(pc_df, x="kg_per_capita", y="country", orientation="h",
                       color="kg_per_capita",
                       color_continuous_scale=["#1a3a22","#56d364","#f0a500","#f44336"],
                       text=pc_df["kg_per_capita"].map(lambda x: f"{x:.0f} kg"))
        fig2.update_layout(**PLOT_LAYOUT, height=300, coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)

    # Personal calculator
    st.markdown('<div class="sec-header">👤 Your Plastic Footprint Calculator</div>', unsafe_allow_html=True)
    personal_p = st.slider("Estimated plastic use (kg/year)", 5.0, 200.0, 40.0)
    co2_plastic = personal_p * 6
    ocean_share = personal_p * 0.022

    c1, c2, c3 = st.columns(3)
    c1.metric("CO₂ from your plastic",     f"{co2_plastic:.1f} kg/yr")
    c2.metric("Potential ocean contribution", f"{ocean_share:.2f} kg/yr")
    c3.metric("vs avg Indian (12.9 kg)",    f"{personal_p/12.9:.1f}×")

    ai_tip = get_plastic_insight(personal_p)
    st.markdown(f'<div class="alert-orange">{ai_tip}</div>', unsafe_allow_html=True)

    # Facts
    st.markdown('<div class="sec-header">❌ Plastic Impact Facts</div>', unsafe_allow_html=True)
    fc1, fc2 = st.columns(2)
    for i, fact in enumerate(plastic["facts"]):
        (fc1 if i % 2 == 0 else fc2).markdown(f'<div class="fact-card">📌 {fact}</div>', unsafe_allow_html=True)

    # How plastic contributes to CO₂
    st.markdown('<div class="sec-header">📈 Plastic → Carbon Pathway</div>', unsafe_allow_html=True)
    stages = ["Extraction", "Refining", "Manufacturing", "Transport", "Incineration", "Decomposition"]
    kg_co2 = [1.2, 0.8, 2.5, 0.4, 0.9, 0.2]
    fig3 = go.Figure(go.Bar(
        x=stages, y=kg_co2, marker_color=COLORS["orange"],
        text=[f"{v} kg" for v in kg_co2], textposition="outside",
    ))
    fig3.update_layout(**PLOT_LAYOUT, height=250,
                       title="CO₂ per kg of Plastic across Lifecycle",
                       yaxis_title="kg CO₂ per kg plastic")
    st.plotly_chart(fig3, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# ██  FOREST ANALYTICS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🌲  Forest Analytics":
    st.markdown("## 🌲 Forest & Deforestation Analytics")

    gf = get_global_forest_summary()

    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-icon">🌳</div>
        <div class="kpi-value">{gf['total_forest_bn_ha']:.2f}bn</div>
        <div class="kpi-label">Hectares of Forest</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">🌍</div>
        <div class="kpi-value">{gf['pct_earth_land']}%</div>
        <div class="kpi-label">of Earth's Land</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">📉</div>
        <div class="kpi-value">{gf['annual_loss_mha']}</div>
        <div class="kpi-label">Mha Lost per Year</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">📈</div>
        <div class="kpi-value">{gf['annual_gain_mha']}</div>
        <div class="kpi-label">Mha Gained per Year</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">💨</div>
        <div class="kpi-value">{gf['co2_from_deforestation_gt_yr']}</div>
        <div class="kpi-label">Gt CO₂ / Year</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="sec-header">🌲 Causes of Deforestation</div>', unsafe_allow_html=True)
        causes = gf["deforestation_causes"]
        fig = px.pie(values=list(causes.values()), names=list(causes.keys()),
                     color_discrete_sequence=[COLORS["red"],"#ff7043","#ffa726","#ffca28",
                                              "#a5d6a7",COLORS["green"]],
                     hole=0.4)
        fig.update_traces(textposition="outside", textinfo="percent+label")
        fig.update_layout(**PLOT_LAYOUT, height=320, showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown('<div class="sec-header">🗺️ Forest Cover by Country</div>', unsafe_allow_html=True)
        isos = ["BRA","IDN","RUS","CAN","USA","COD","AUS","IND","CHN","GBR"]
        frows = [fetch_forest_data(iso) for iso in isos]
        fdf   = pd.DataFrame([{
            "Country": d.get("name", d["country"]),
            "Cover %": d.get("forest_cover_pct", 0),
            "Loss km²/yr": d.get("annual_loss_km2", 0),
        } for d in frows]).sort_values("Cover %")
        fig2 = px.bar(fdf, x="Cover %", y="Country", orientation="h",
                      color="Cover %", color_continuous_scale="Greens",
                      text=fdf["Cover %"].map(lambda x: f"{x:.0f}%"))
        fig2.update_layout(**PLOT_LAYOUT, height=320, coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)

    # Deforestation rate per country
    st.markdown('<div class="sec-header">📉 Annual Deforestation Rate (km²/yr)</div>', unsafe_allow_html=True)
    fdf_sorted = fdf.sort_values("Loss km²/yr", ascending=True)
    fig3 = px.bar(fdf_sorted, x="Loss km²/yr", y="Country", orientation="h",
                  color="Loss km²/yr",
                  color_continuous_scale=["#1a3a22","#f0a500","#f44336"])
    fig3.update_layout(**PLOT_LAYOUT, height=300, coloraxis_showscale=False)
    st.plotly_chart(fig3, use_container_width=True)

    # World Bank forest area trend
    st.markdown('<div class="sec-header">📈 Global Forest Area Trend (% of land)</div>', unsafe_allow_html=True)
    with st.spinner("Fetching World Bank data…"):
        ftrend = fetch_world_bank("forest_area_pct", "WLD")
    fig4 = go.Figure(go.Scatter(
        x=ftrend["year"], y=ftrend["value"],
        fill="tozeroy", fillcolor="rgba(86,211,100,0.12)",
        line=dict(color=COLORS["green"], width=2.5),
    ))
    fig4.update_layout(**PLOT_LAYOUT, height=230,
                       yaxis_title="% of land area")
    st.plotly_chart(fig4, use_container_width=True)

    # Impact table
    st.markdown('<div class="sec-header">🔥 Deforestation Carbon Impact</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="fact-card">
    | Source | Annual CO₂ |
    |---|---|
    | Tropical Deforestation | **4.8 Gt CO₂/year** |
    | Forest Degradation | **2.1 Gt CO₂/year** |
    | Peat Destruction | **1.5 Gt CO₂/year** |
    | Wildfire (deforestation-linked) | **1.0 Gt CO₂/year** |
    
    > 🌍 Deforestation = **10–15%** of global GHG emissions &nbsp;|&nbsp;
    > 1 hectare of tropical forest = **~400 t CO₂** stored
    </div>
    """, unsafe_allow_html=True)
    with st.expander("❗ Root Causes of Deforestation"):
        st.markdown("""
        - **Agriculture (73%)** — Cattle ranching, soy, palm oil clear vast forest areas each year.
        - **Logging (10%)** — Both legal and illegal timber operations degrade and remove forests.
        - **Infrastructure (2%)** — Roads built into forests fragment habitat and enable further clearing.
        - **Urbanisation (3%)** — Expanding cities consume peri-urban forests in developing nations.
        - **Wildfire (3%)** — Climate change-amplified fires destroy millions of hectares annually.
        - **Mining** — Open-pit mining removes forest and releases stored carbon in soil and peat.
        """)

# ─────────────────────────────────────────────────────────────────────────────
# ██  TREE PLANTING MODEL
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🌱  Tree Planting Model":
    st.markdown("## 🌱 Tree Plantation Offset Model")

    log     = st.session_state.daily_log
    summary = log.summary()
    ann_kg  = summary["total_carbon_kg"] * 365
    td      = calculate_trees_needed(ann_kg)

    st.markdown(f"""
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-icon">🌳</div>
        <div class="kpi-value">{td['personal_trees_needed']:.0f}</div>
        <div class="kpi-label">Trees YOU Need</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">🌍</div>
        <div class="kpi-value">{td['global_trees_needed_bn']:.1f}bn</div>
        <div class="kpi-label">World Needs</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">🌱</div>
        <div class="kpi-value">{td['trees_planted_per_year_bn']:.0f}bn</div>
        <div class="kpi-label">Planted/yr Now</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">🪓</div>
        <div class="kpi-value">{td['trees_cut_per_year_bn']:.0f}bn</div>
        <div class="kpi-label">Cut/yr Now</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">⚠️</div>
        <div class="kpi-value">{td['deficit_bn']:.1f}bn</div>
        <div class="kpi-label">Plantation Deficit</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown('<div class="sec-header">📊 Required vs Planted (Global, bn trees)</div>', unsafe_allow_html=True)
        fig = go.Figure(go.Bar(
            x=["Needed to Offset", "Currently Planted/yr", "Currently Cut/yr"],
            y=[td["global_trees_needed_bn"], td["trees_planted_per_year_bn"], td["trees_cut_per_year_bn"]],
            marker_color=[COLORS["red"], COLORS["green"], COLORS["orange"]],
            text=[f"{v:.1f}bn" for v in [td["global_trees_needed_bn"], 15.0, 15.0]],
            textposition="outside",
        ))
        fig.update_layout(**PLOT_LAYOUT, height=300, yaxis_title="Billion Trees")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        st.markdown('<div class="sec-header">🧮 Personal Calculator</div>', unsafe_allow_html=True)
        custom_co2 = st.slider("Your annual CO₂ (kg)", 100, 20000, int(ann_kg), step=100)
        td2 = calculate_trees_needed(custom_co2)
        st.metric("Trees you need", f"{td2['personal_trees_needed']:.0f}")
        st.metric("Land needed",    f"{td2['personal_trees_needed'] * 25:.0f} m²")
        st.metric("CO₂ absorbed per tree/yr", f"{td2['co2_per_tree_kg_yr']:.1f} kg")
        st.markdown(f"""
        <div class="alert-green">
        🌍 If every person on Earth planted <b>{td2['personal_trees_needed']:.0f} trees</b>,
        and they all survived, the planet would offset ~<b>{custom_co2/1000:.2f} t CO₂/person/year</b>.
        It takes a tree about 10 years to reach full carbon-absorption capacity — start planting today!
        </div>
        """, unsafe_allow_html=True)

    # Net forest change by country
    st.markdown('<div class="sec-header">🌏 Net Forest Change by Country (Mha/yr)</div>', unsafe_allow_html=True)
    net_data = {
        "Country":  ["Brazil","Indonesia","DR Congo","USA","China","India","Russia"],
        "Planted":  [2.0, 1.2, 0.8, 3.5, 10.0, 2.3, 1.5],
        "Lost":     [11.6, 3.8, 1.4, 2.1, 1.0, 0.2, 4.4],
    }
    ndf = pd.DataFrame(net_data)
    fig2 = go.Figure()
    fig2.add_trace(go.Bar(name="Planted", x=ndf["Country"], y=ndf["Planted"],  marker_color=COLORS["green"]))
    fig2.add_trace(go.Bar(name="Lost",    x=ndf["Country"], y=[-v for v in ndf["Lost"]], marker_color=COLORS["red"]))
    fig2.update_layout(**PLOT_LAYOUT, barmode="relative", height=300,
                       yaxis_title="Mha/year", legend=dict(orientation="h", y=1.12))
    st.plotly_chart(fig2, use_container_width=True)

    # Offset growth over time
    st.markdown('<div class="sec-header">⏱️ Carbon Offset Growth of a Single Tree</div>', unsafe_allow_html=True)
    tree_years = list(range(1, 51))
    cumulative = [min(y * Config.CO2_PER_TREE_PER_YEAR_KG, y * Config.CO2_PER_TREE_PER_YEAR_KG) for y in tree_years]
    fig3 = go.Figure(go.Scatter(
        x=tree_years, y=cumulative,
        fill="tozeroy", fillcolor="rgba(86,211,100,0.15)",
        line=dict(color=COLORS["green"], width=2.5),
    ))
    fig3.update_layout(**PLOT_LAYOUT, height=220,
                       xaxis_title="Tree Age (years)", yaxis_title="Cumulative CO₂ absorbed (kg)")
    st.plotly_chart(fig3, use_container_width=True)

# ─────────────────────────────────────────────────────────────────────────────
# ██  AI INSIGHTS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🤖  AI Insights":
    st.markdown("## 🤖 AI-Powered Eco Insights")
    st.caption("Powered by Groq LLaMA 3 · Falls back to curated insights if key not set")

    log     = st.session_state.daily_log
    summary = log.summary()

    tab1, tab2, tab3 = st.tabs(["📅 Daily Insight", "🔮 Predictions", "♻️ Plastic & Tips"])

    with tab1:
        st.markdown('<div class="sec-header">📅 Today\'s Personalised Eco Report</div>', unsafe_allow_html=True)
        with st.spinner("🤖 Generating insight…"):
            insight = get_daily_insight(summary)
        st.markdown(f'<div class="alert-green">{insight}</div>', unsafe_allow_html=True)

        # Behaviour consequence dial
        st.markdown('<div class="sec-header">📊 Behaviour → Consequence</div>', unsafe_allow_html=True)
        scenarios = {
            "All Walking/Cycling": 0.0,
            "50% Cycling, 50% Car": summary["total_carbon_kg"] * 0.5,
            "Current Habits":      summary["total_carbon_kg"],
            "All Car":             summary["total_distance_km"] * Config.EMISSION_FACTORS["car"],
        }
        sc_df = pd.DataFrame({"Scenario": list(scenarios.keys()), "Daily CO₂ (kg)": list(scenarios.values())})
        fig = px.bar(sc_df, x="Scenario", y="Daily CO₂ (kg)",
                     color="Daily CO₂ (kg)",
                     color_continuous_scale=["#56d364","#f0a500","#f44336"])
        fig.update_layout(**PLOT_LAYOUT, height=280, coloraxis_showscale=False)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("""
        <div class="alert-blue">
        💡 <b>Driving more → higher footprint.</b> Switching just 2 car trips per week to cycling 
        can save ~150 kg CO₂/year — equivalent to 7 mature trees' annual absorption.
        </div>
        """, unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="sec-header">🔮 Future Impact Predictor</div>', unsafe_allow_html=True)
        days = st.slider("Project forward (days)", 30, 730, 365, key="ai_days")
        proj = predict_future_impact(summary["total_carbon_kg"], days)

        c1, c2, c3 = st.columns(3)
        c1.metric(f"CO₂ in {days}d", f"{proj['projected_tonnes']:.2f} t")
        c2.metric("Trees Needed",    f"{proj['trees_to_offset']:.0f}")
        c3.metric("vs Global Avg",   f"{proj['pct_of_global_avg']:.0f}%")

        with st.spinner("🤖 Generating prediction…"):
            pred_text = get_prediction_insight(proj)
        st.markdown(f'<div class="alert-orange">{pred_text}</div>', unsafe_allow_html=True)

        # Trend comparison
        fd   = list(range(1, days+1, max(1, days//80)))
        your = [summary["total_carbon_kg"] * d / 1000 for d in fd]
        glb  = [4.7 * d / 365 for d in fd]
        tgt  = [1.5 * d / 365 for d in fd]  # Paris Agreement target
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=fd, y=your, name="You",           line=dict(color=COLORS["green"], width=2.5)))
        fig2.add_trace(go.Scatter(x=fd, y=glb,  name="Global Avg",    line=dict(color=COLORS["orange"], width=2, dash="dash")))
        fig2.add_trace(go.Scatter(x=fd, y=tgt,  name="Paris Target",  line=dict(color=COLORS["blue"], width=2, dash="dot")))
        fig2.update_layout(**PLOT_LAYOUT, height=300,
                           xaxis_title="Days", yaxis_title="Cumulative CO₂ (tonnes)",
                           legend=dict(orientation="h", y=1.12))
        st.plotly_chart(fig2, use_container_width=True)

    with tab3:
        st.markdown('<div class="sec-header">♻️ Plastic Reduction Insight</div>', unsafe_allow_html=True)
        pp = st.slider("Plastic use estimate (kg/year)", 5.0, 200.0, 40.0, key="ai_pp")
        with st.spinner("🤖 Generating insight…"):
            p_ins = get_plastic_insight(pp)
        st.markdown(f'<div class="alert-orange">{p_ins}</div>', unsafe_allow_html=True)

        st.markdown('<div class="sec-header">💡 Personalised Eco Tips</div>', unsafe_allow_html=True)
        tips = get_eco_tips(summary["activity_breakdown"])
        for tip in tips:
            st.markdown(f'<div class="fact-card">{tip}</div>', unsafe_allow_html=True)

        st.markdown('<div class="sec-header">✅ Eco Habit Score</div>', unsafe_allow_html=True)
        daily_c    = summary["total_carbon_kg"]
        score      = max(0, min(100, int(100 - (daily_c / (4700/365)) * 100)))
        color      = COLORS["green"] if score >= 70 else COLORS["orange"] if score >= 40 else COLORS["red"]
        if score >= 70:
            score_msg = "🌿 Excellent! You are a climate champion."
        elif score >= 40:
            score_msg = "🌱 Good progress — a few tweaks and you will be green."
        else:
            score_msg = "⚠️ High footprint — consider switching to sustainable transport."
        st.markdown(f"""
        <div style="background:#0f1f14;border:1px solid #2e5c35;border-radius:14px;padding:20px;text-align:center">
          <div style="font-size:3.5rem;font-weight:800;color:{color}">{score}</div>
          <div style="color:#8b949e;font-size:0.9rem">Eco Score / 100</div>
          <div style="margin-top:12px;font-size:0.85rem;color:#c8e6c9">{score_msg}</div>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ██  API STATUS
# ─────────────────────────────────────────────────────────────────────────────
elif page == "⚙️  API Status":
    st.markdown("## ⚙️ API Configuration & Status")
    st.caption("All keys are loaded exclusively from the `.env` file in the project root.")

    status = Config.validate()
    sc1, sc2 = st.columns(2)
    for i, (api, ok) in enumerate(status.items()):
        icon  = "✅" if ok else "⚠️"
        color = COLORS["green"] if ok else COLORS["orange"]
        note  = "Configured & Active" if ok else "Not set — graceful fallback active"
        (sc1 if i % 2 == 0 else sc2).markdown(
            f'<div style="border-left:4px solid {color};padding:12px 16px;margin:8px 0;'
            f'background:#0f1f14;border-radius:8px">'
            f'<b>{icon} {api}</b><br>'
            f'<span style="color:{color};font-size:0.82rem">{note}</span></div>',
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown('<div class="sec-header">📋 .env Template</div>', unsafe_allow_html=True)
    import os
    _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    try:
        with open(_env_path, encoding="utf-8") as f:
            env_text = f.read()
    except FileNotFoundError:
        env_text = "# .env file not found.\n# Create a file named .env in the same folder as app.py\n# and add your API keys as shown in the table below."
    st.code(env_text, language="bash")

    st.markdown('<div class="sec-header">🔗 Get Your API Keys</div>', unsafe_allow_html=True)
    st.markdown("""
    | Service | URL | Cost |
    |---------|-----|------|
    | **Climatiq** (carbon emissions) | https://www.climatiq.io | Free tier |
    | **Global Forest Watch** (forests) | https://www.globalforestwatch.org | Free |
    | **Groq AI** (LLaMA 3 insights) | https://console.groq.com | Free tier |
    | **World Bank** (global stats) | https://datahelpdesk.worldbank.org | No key needed |
    | **Our World in Data** | https://ourworldindata.org | No key needed |
    | **OpenStreetMap / Nominatim** | https://nominatim.org | No key needed |
    """)

    st.markdown('<div class="sec-header">🚀 How to Run</div>', unsafe_allow_html=True)
    st.code("""# 1. Clone / enter project folder
cd eco_tracker

# 2. Install dependencies
pip install -r requirements.txt

# 3. Add your API keys to .env
nano .env   # or open in any editor

# 4. Launch the app
streamlit run app.py
""", language="bash")
