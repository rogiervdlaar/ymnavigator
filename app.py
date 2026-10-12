import streamlit as st
import math
import matplotlib.pyplot as plt
import numpy as np
import random


# ==========================================
# 1. CALLBACKS & STATE MANAGEMENT
# ==========================================
def generate_random_scenario():
    """Callback to randomize all environment variables in session state."""
    st.session_state.boat_speed = round(random.uniform(4.0, 8.0), 1)
    st.session_state.desired_course = random.randint(0, 359)
    st.session_state.tide_set = random.randint(0, 359)

    spring = round(random.uniform(1.5, 4.0), 1)
    neap = round(random.uniform(0.5, spring - 0.5), 1)

    st.session_state.spring_rate = spring
    st.session_state.neap_rate = neap
    st.session_state.days_since_spring = random.randint(0, 7)

    st.session_state.wind_dir = random.randint(0, 359)
    st.session_state.leeway_angle = random.randint(2, 10)
    st.session_state.variation = random.randint(-15, 15)


# ==========================================
# 2. CORE MATH LOGIC
# ==========================================
def calculate_tidal_drift(spring_rate, neap_rate, days_since_spring):
    factor = days_since_spring / 7.0
    range_diff = spring_rate - neap_rate
    return round(spring_rate - (range_diff * factor), 1)


def calculate_full_cts(desired_course, boat_speed, tide_set, tide_drift, wind_dir, leeway_angle, variation):
    course_rad = math.radians(desired_course)
    tide_rad = math.radians(tide_set)
    tide_angle = tide_rad - course_rad
    cross_current = tide_drift * math.sin(tide_angle)

    if abs(cross_current) >= boat_speed:
        return None, None, None, "Tide is too strong to make this course."

    crab_angle_rad = math.asin(cross_current / boat_speed)
    water_track = (desired_course - math.degrees(crab_angle_rad)) % 360
    sog = (boat_speed * math.cos(crab_angle_rad)) + (tide_drift * math.cos(tide_angle))

    relative_wind = (wind_dir - water_track) % 360
    if relative_wind == 0 or relative_wind == 180:
        true_cts = water_track
        leeway_note = "0° (Wind dead ahead/astern)"
    elif relative_wind < 180:
        true_cts = (water_track + leeway_angle) % 360
        leeway_note = f"+{leeway_angle}° (Wind on Starboard)"
    else:
        true_cts = (water_track - leeway_angle) % 360
        leeway_note = f"-{leeway_angle}° (Wind on Port)"

    mag_cts = (true_cts - variation) % 360
    return round(true_cts, 1), round(mag_cts, 1), round(sog, 1), leeway_note


def calculate_rule_of_twelfths(low_water, high_water, hours_since_low):
    tidal_range = high_water - low_water
    one_twelfth = tidal_range / 12.0
    increments = [1, 2, 3, 3, 2, 1]
    hours = max(0, min(6, hours_since_low))

    current_height = low_water
    for i in range(hours):
        current_height += (one_twelfth * increments[i])

    return round(current_height, 2), round(tidal_range, 2), round(one_twelfth, 2)


# ==========================================
# 3. MATPLOTLIB VISUALIZATIONS
# ==========================================
def plot_vector_triangle(desired_course, tide_set, actual_drift, sog, true_cts, boat_speed):
    def compass_to_math(compass_deg):
        return math.radians((90 - compass_deg) % 360)

    fig, ax = plt.subplots(figsize=(8, 8))
    A = (0, 0)

    tide_rad = compass_to_math(tide_set)
    B = (actual_drift * math.cos(tide_rad), actual_drift * math.sin(tide_rad))

    track_rad = compass_to_math(desired_course)
    C = (sog * math.cos(track_rad), sog * math.sin(track_rad))

    ax.annotate('', xy=B, xytext=A, arrowprops=dict(arrowstyle="->", color='blue', lw=2))
    ax.text(B[0] / 2, B[1] / 2, f' Tide\n {actual_drift}kn', color='blue', fontsize=10)

    ax.annotate('', xy=C, xytext=B, arrowprops=dict(arrowstyle="->", color='red', lw=2))
    ax.text((B[0] + C[0]) / 2, (B[1] + C[1]) / 2, f' Water Track\n {boat_speed}kn', color='red', fontsize=10)

    ax.annotate('', xy=C, xytext=A, arrowprops=dict(arrowstyle="->", color='green', lw=2, ls='--'))
    ax.text(C[0] / 2, C[1] / 2, f' Ground Track\n {sog}kn', color='green', fontsize=10)

    max_val = max(boat_speed, actual_drift, sog) * 1.2
    ax.annotate('N', xy=(0.95 * max_val, 0.95 * max_val), xytext=(0.95 * max_val, 0.85 * max_val),
                arrowprops=dict(facecolor='black', width=2, headwidth=8), ha='center')

    ax.set_aspect('equal')
    ax.set_xlim(-max_val, max_val)
    ax.set_ylim(-max_val, max_val)
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    return fig


def plot_rule_of_twelfths_curve(low_water, high_water):
    tidal_range = high_water - low_water
    one_twelfth = tidal_range / 12.0
    increments = [0, 1, 2, 3, 3, 2, 1]

    hours = list(range(7))
    heights = [low_water]
    for i in range(1, 7):
        heights.append(heights[i - 1] + (increments[i] * one_twelfth))

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(hours, heights, marker='o', linestyle='-', color='#1f77b4', linewidth=2, markersize=8)
    ax.fill_between(hours, low_water, heights, color='#1f77b4', alpha=0.2)

    ax.set_title("Rule of Twelfths Tidal Curve", fontsize=14, pad=15)
    ax.set_xlabel("Hours from Low Water", fontsize=12)
    ax.set_ylabel("Height of Tide (m)", fontsize=12)
    ax.set_ylim(max(0, low_water - 1), high_water + 1)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    labels = ["", "+1/12", "+2/12", "+3/12", "+3/12", "+2/12", "+1/12"]
    for i in range(1, 7):
        mid_x = (hours[i - 1] + hours[i]) / 2
        mid_y = (heights[i - 1] + heights[i]) / 2
        ax.text(mid_x, mid_y + 0.3, labels[i], ha='center', fontsize=10, color='darkblue')
    return fig


# ==========================================
# 4. STREAMLIT UI SETUP
# ==========================================
st.set_page_config(page_title="YM Navigator", layout="wide")
st.title("Yachtmaster Navigation Training")

if 'boat_speed' not in st.session_state:
    st.session_state.boat_speed = 7.0
    st.session_state.desired_course = 90
    st.session_state.tide_set = 140
    st.session_state.spring_rate = 2.8
    st.session_state.neap_rate = 1.4
    st.session_state.days_since_spring = 3
    st.session_state.wind_dir = 20
    st.session_state.leeway_angle = 5
    st.session_state.variation = -2

st.sidebar.button("🎲 Generate Random Scenario", on_click=generate_random_scenario, type="primary")
st.sidebar.markdown("---")

st.sidebar.header("1. Vessel Parameters")
boat_speed = st.sidebar.slider("Boat Speed (kn)", 3.0, 10.0, key="boat_speed", step=0.5)
desired_course = st.sidebar.number_input("Intended Ground Track (°T)", 0, 359, key="desired_course")

st.sidebar.header("2. Tidal Data (From Diamond)")
tide_set = st.sidebar.number_input("Tidal Set (°T)", 0, 359, key="tide_set")
spring_rate = st.sidebar.number_input("Spring Rate (kn)", 0.0, 5.0, key="spring_rate", step=0.1)
neap_rate = st.sidebar.number_input("Neap Rate (kn)", 0.0, 5.0, key="neap_rate", step=0.1)
days_since_spring = st.sidebar.slider("Days Since Springs", 0, 7, key="days_since_spring")

st.sidebar.header("3. Environment")
wind_dir = st.sidebar.number_input("Wind Direction (°T)", 0, 359, key="wind_dir")
leeway_angle = st.sidebar.slider("Estimated Leeway (°)", 0, 15, key="leeway_angle")
variation = st.sidebar.number_input("Magnetic Variation (+E / -W)", -30, 30, key="variation")

# ==========================================
# 5. RENDER TABS
# ==========================================
tab1, tab2 = st.tabs(["Course to Steer (CTS)", "Tidal Clearance (Rule of 12ths)"])

# --- TAB 1: COURSE TO STEER ---
with tab1:
    actual_drift = calculate_tidal_drift(spring_rate, neap_rate, days_since_spring)
    true_cts, mag_cts, sog, leeway_note = calculate_full_cts(
        desired_course, boat_speed, tide_set, actual_drift, wind_dir, leeway_angle, variation
    )

    st.markdown("### CTS Practice Scenario")
    st.info(f"""
    **SITUATION:**  
    You need to make good a track of **{desired_course:03d}°(T)** at an engine speed of **{boat_speed} knots**.

    **ENVIRONMENT:**  
    Today is **{days_since_spring} days** past Springs. The nearest tidal diamond shows a set of **{tide_set:03d}°(T)** with a Spring rate of {spring_rate}kn and a Neap rate of {neap_rate}kn.  
    The wind is blowing from **{wind_dir:03d}°(T)**, causing an estimated **{leeway_angle}°** of leeway. Local magnetic variation is **{abs(variation)}° {'East' if variation > 0 else 'West'}**.
    """)

    with st.expander("Reveal Step-by-Step RYA Working Out"):
        st.write(
            f"**1. Tidal Rate:** Interpolated {days_since_spring} days past Springs gives a drift of **{actual_drift} knots**.")

        if true_cts is None:
            st.error(leeway_note)
        else:
            st.markdown(f"""
            **2. The Vector Triangle (Water Track):**
            * Plot the tide setting **{tide_set:03d}°** for **{actual_drift} NM** (Point A to B).
            * From Point B, swing an arc of **{boat_speed} NM** to intersect your intended track of **{desired_course:03d}°**.
            * The line connecting Point B to that intersection is your True Water Track: **{true_cts:03.1f}°(T)**.
            * *Measuring Point A to the intersection gives your SOG: **{sog} knots**.*

            **3. Apply Leeway:**
            * Wind is blowing from **{wind_dir:03d}°(T)**. 
            * Compared to your {true_cts:03.1f}° track, the wind pushes you, requiring you to steer into it.
            * Adjustment: **{leeway_note}**.
            * True Course to Steer: **{(true_cts + (leeway_angle if "Starboard" in leeway_note else -leeway_angle if "Port" in leeway_note else 0)) % 360:03.1f}°(T)**.

            **4. Apply Magnetic Variation:**
            * True to Magnetic: Add West, Subtract East.
            * Variation is **{abs(variation)}° {'East' if variation > 0 else 'West'}**.
            * Final calculation yields your compass heading.
            """)

            st.success(f"**Final Compass Course to Steer:** {mag_cts:03.1f}°(M)")

            # Matplotlib figure
            st.markdown("**5. Visual Chartwork Check:**")
            fig = plot_vector_triangle(desired_course, tide_set, actual_drift, sog, true_cts, boat_speed)
            st.pyplot(fig)

# --- TAB 2: TIDAL HEIGHTS ---
with tab2:
    st.markdown("### Depth & Clearance Calculator")

    col1, col2, col3 = st.columns(3)
    with col1:
        low_water = st.number_input("Low Water Height (m)", 0.0, 15.0, 1.2, 0.1)
    with col2:
        high_water = st.number_input("High Water Height (m)", 0.0, 15.0, 5.4, 0.1)
    with col3:
        hours_since_low = st.slider("Hours Since Low Water", 0, 6, 2)

    current_height, tidal_range, one_twelfth = calculate_rule_of_twelfths(low_water, high_water, hours_since_low)

    st.markdown("---")
    st.success(f"**Estimated Depth at Hour {hours_since_low}:** {current_height} meters")

    st.markdown("#### Tidal Curve Profile")
    fig2 = plot_rule_of_twelfths_curve(low_water, high_water)
    st.pyplot(fig2)

    with st.expander("Show Rule of Twelfths Breakdown"):
        st.write(f"**Total Range:** {tidal_range:.2f}m")
        st.write(f"**One Twelfth (1/12):** {one_twelfth:.2f}m")
        st.markdown("""
        **Hourly Accumulation:**
        * **Hour 1 (+1/12):** Water rises slowly as the tide turns.
        * **Hour 2 (+2/12):** Flow accelerates.
        * **Hour 3 (+3/12):** Maximum flow (Mid-tide).
        * **Hour 4 (+3/12):** Maximum flow (Mid-tide).
        * **Hour 5 (+2/12):** Flow decelerates.
        * **Hour 6 (+1/12):** Water rises slowly as it nears High Water.
        """)
