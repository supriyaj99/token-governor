"""
streamlit_app.py  — the FinOps dashboard
-----------------------------------------
A live, visual control room for the system. Streamlit turns a plain Python
script into a web dashboard — no front-end code needed.

Run (from the project root), pointing at the same database the gateway uses:
    streamlit run dashboard/streamlit_app.py

What it shows:
  - Budget: spent vs remaining, and the forecaster's exhaustion prediction.
  - Burn over time: daily spend.
  - Routing: how often each tier was chosen (the router's behavior).
  - Quality by tier: average quality each tier delivered.
  - Per-identity: spend and value-per-dollar, with who the fairness layer would
    tighten — the novel Module 6 view.

This reads the database directly (read-only), so you can keep it open while the
gateway runs and refresh to watch numbers change.
"""

import pandas as pd
import streamlit as st

from app import config
from app.database import engine
from app.fairness import compute_identity_policies
from app.forecaster import decide_control_mode, forecast_exhaustion

st.set_page_config(page_title="TokenGovernor", layout="wide")
st.title("TokenGovernor — AI Cost Governance")

# Load all logged requests into a pandas DataFrame (a table in memory).
try:
    df = pd.read_sql("SELECT * FROM request_logs", engine)
except Exception as e:
    st.error(f"Could not read the database yet: {e}")
    st.stop()

if df.empty:
    st.info("No requests logged yet. Start the gateway and run "
            "`python -m rag.seed_traffic 300` to generate demo traffic.")
    st.stop()

df["created_at"] = pd.to_datetime(df["created_at"])
df["day"] = df["created_at"].dt.date

# ---- Top-line budget numbers ----
total_cost = float(df["cost_usd"].sum())
remaining = config.BUDGET_USD - total_cost
daily = df.groupby("day")["cost_usd"].sum().tolist()
fc = forecast_exhaustion(daily, config.BUDGET_USD, config.PERIOD_DAYS)
control = decide_control_mode(fc)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total spend", f"${total_cost:,.4f}")
c2.metric("Budget remaining", f"${remaining:,.4f}")
c3.metric("Requests", f"{len(df):,}")
c4.metric("Avg quality", f"{df['quality'].mean():.1%}")

st.subheader("Budget forecast (Module 5)")
proj = fc["projected_exhaustion_day"]
msg = (f"Projected to exhaust the ${config.BUDGET_USD:.0f} budget on day "
       f"{proj} of {config.PERIOD_DAYS}." if proj else
       "On track to stay within budget for the full period.")
st.write(f"**Burn rate:** ${fc['burn_rate_per_day']:.4f}/day · {msg}")
st.write(f"**Controller decision:** `{control['mode']}` — {control['reason']}")

# ---- Burn over time ----
st.subheader("Daily spend")
burn = df.groupby("day")["cost_usd"].sum()
st.bar_chart(burn)

# ---- Routing behavior ----
left, right = st.columns(2)
with left:
    st.subheader("Routing: tier chosen")
    if df["routed_tier"].notna().any():
        st.bar_chart(df["routed_tier"].value_counts())
    else:
        st.caption("No auto-routed requests yet (send requests with model='auto').")
with right:
    st.subheader("Avg quality by tier")
    byq = df.dropna(subset=["routed_tier"]).groupby("routed_tier")["quality"].mean()
    if not byq.empty:
        st.bar_chart(byq)

# ---- Per-identity + value-weighted fairness (Module 6) ----
st.subheader("Per-identity spend & value (Module 6)")
bar = config.QUALITY_BAR
per = {}
for ident, g in df.groupby("identity"):
    per[ident] = {
        "spend": float(g["cost_usd"].sum()),
        "successes": int((g["quality"] >= bar).sum()),
        "requests": int(len(g)),
    }
period_fraction = min(len(daily) / config.PERIOD_DAYS, 1.0)
pol = compute_identity_policies(per, config.BUDGET_USD, period_fraction)

rows = []
for ident, p in pol.items():
    rows.append({
        "identity": ident,
        "spend_$": round(p["spend"], 4),
        "fair_share_$": round(p["envelope"], 4),
        "value_per_$": p["value_per_dollar"],
        "over_pace": p["over_pace"],
        "action": p["action"],
    })
st.dataframe(pd.DataFrame(rows).sort_values("value_per_$"), use_container_width=True)
st.caption("The fairness layer tightens LOW value-per-dollar over-spenders first "
           "and protects high-value teams — the novel part of this project.")
