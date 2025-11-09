# --- add at very top (keeps relative imports predictable) ---
from pathlib import Path
import sys
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
# ------------------------------------------------------------

"""
SmartSaverNet 💸 — Streamlit UI
- Works standalone with graceful fallbacks
- Auto-discovers agents in ./agents
- Plugs into orchestrator.{state,graph} and data.{db,seed_mock} when present
"""

from types import SimpleNamespace
import importlib
from typing import Any, Dict, List, Tuple

import streamlit as st

# ---------- safe import that returns (module, error) ----------
def _safe_import(module_path: str):
    try:
        mod = importlib.import_module(module_path)
        return mod, None
    except Exception as e:
        return None, e

StateMod, StateErr = _safe_import("orchestrator.state")
GraphMod, GraphErr = _safe_import("orchestrator.graph")
DBMod,   DBErr   = _safe_import("data.db")
SeedMod, SeedErr = _safe_import("data.seed_mock")

# ---------- session state bootstrap ----------
def _default_state_fallback() -> Dict[str, Any]:
    return {
        "income": 60000.0,
        "monthly_spend": 45000.0,
        "savings_rate": 0.15,
        "budget": {},
        "savings_suggestions": [],
        "debts": [
            {"name": "Credit Card", "balance": 30000, "apr": 0.36, "min_payment": 1500},
            {"name": "Student Loan", "balance": 120000, "apr": 0.11, "min_payment": 2500},
        ],
        "debt_strategy": "avalanche",
        "debt_plan": {},
        "goals": [],
        "alerts": [],
    }

def _get_state_obj():
    # prefer real Pydantic model if available
    if StateMod and hasattr(StateMod, "default_state"):
        return StateMod.default_state()
    # fallback that supports attribute access (prevents 'dict has no attribute')
    return SimpleNamespace(**_default_state_fallback())

def _to_view(state_obj) -> Dict[str, Any]:
    if StateMod and hasattr(state_obj, "model_dump"):
        return state_obj.model_dump()
    if isinstance(state_obj, SimpleNamespace):
        return vars(state_obj)
    return dict(state_obj)

# ---------- agent discovery / runner ----------
def discover_agent_modules() -> List[str]:
    agents_dir = BASE_DIR / "agents"
    if not agents_dir.exists():
        return []
    return sorted(p.stem for p in agents_dir.glob("*.py") if p.stem not in {"__init__"})

def _import_agent(name: str):
    mod, err = _safe_import(f"agents.{name}")
    return mod, err

def load_agents(enabled: List[str]) -> List[Any]:
    agents = []
    for name in enabled:
        mod, err = _import_agent(name)
        if err:
            st.error(f"Import error in `agents.{name}`: {err}")
            continue
        if not hasattr(mod, "Agent"):
            st.warning(f"Agent `{name}` is missing an `Agent` class.")
            continue
        try:
            agents.append(mod.Agent())
        except Exception as e:
            st.error(f"Failed to init agent `{name}`: {e}")
    return agents

def run_once_fallback(state_obj, agents):
    """If orchestrator.graph isn't ready, just run agents sequentially."""
    msgs = []

    # NEW: Coerce plain dict state to UserState so agents can use attribute access
    try:
        if isinstance(state_obj, dict) and StateMod and hasattr(StateMod, "UserState"):
            state_obj = StateMod.UserState(**state_obj)
    except Exception:
        pass

    for a in agents:
        try:
            state_obj, msg = a.step(state_obj)
            msgs.append({"agent": getattr(a, "name", a.__class__.__name__), "content": msg})
        except Exception as e:
            msgs.append({"agent": getattr(a, "name", a.__class__.__name__), "content": f"⚠️ Error: {e}"})
    return state_obj, msgs


# ---------- DB helpers ----------
def get_conn():
    return DBMod.get_conn() if DBMod and hasattr(DBMod, "get_conn") else None

def ensure_schema(conn):
    return DBMod.ensure_schema(conn) if DBMod and hasattr(DBMod, "ensure_schema") else None

def seed_transactions(conn, user_id="demo") -> int:
    return SeedMod.seed_transactions(conn, user_id=user_id) if SeedMod and hasattr(SeedMod, "seed_transactions") else 0

# ---------- UI ----------
st.set_page_config(page_title="SmartSaverNet", page_icon="💸", layout="wide")
st.title("SmartSaverNet 💸 — Multi-Agent Financial Coach")

if "user_state" not in st.session_state:
    st.session_state.user_state = _get_state_obj()

with st.sidebar:
    st.header("Agents")
    available = discover_agent_modules()
    enabled = st.multiselect("Enable agents", options=available, default=available)

    st.divider()
    st.subheader("Run Controls")
    run_once = st.button("Run Once ▶")
    reset_state = st.button("Reset State 🔄")

    st.divider()
    st.subheader("Data / Admin")
    colA, colB = st.columns(2)
    with colA:
        init_db = st.button("Init DB Schema")
    with colB:
        seed_mock = st.button("Seed Mock Txns 🧪")

# metrics
view = _to_view(st.session_state.user_state)
c1, c2, c3 = st.columns(3)
c1.metric("Monthly Income (₹)", f"{view.get('income', 0):,.0f}")
c2.metric("Monthly Spend (₹)", f"{view.get('monthly_spend', 0):,.0f}")
c3.metric("Savings Rate", f"{int(view.get('savings_rate', 0)*100)}%")

tab_overview, tab_txns, tab_goals, tab_admin = st.tabs(["Overview", "Transactions", "Goals", "Admin"])

# admin actions
if init_db:
    conn = get_conn()
    if conn:
        ensure_schema(conn)
        st.success("DB schema ensured.")
    else:
        st.warning("`data/db.py` not ready yet.")

if seed_mock:
    conn = get_conn()
    if conn:
        ensure_schema(conn)
        n = seed_transactions(conn, user_id="demo")
        st.success(f"Inserted {n} mock transactions.")
    else:
        st.warning("`data/db.py` and `data/seed_mock.py` not ready yet.")

if reset_state:
    st.session_state.user_state = _get_state_obj()
    st.success("State reset.")

# try to build a graph if present
graph = None
if GraphMod and hasattr(GraphMod, "build_graph"):
    try:
        graph = GraphMod.build_graph(active_agents=enabled)
    except Exception as e:
        st.warning(f"Graph build failed; using simple runner. Details: {e}")

# run once
latest_msgs: List[Dict[str, str]] = []
if run_once:
    agents = load_agents(enabled)
    if graph and hasattr(GraphMod, "run_graph_once"):
        try:
            new_state, latest_msgs = GraphMod.run_graph_once(graph, st.session_state.user_state)
            st.session_state.user_state = new_state
        except Exception as e:
            st.error(f"Graph run failed; falling back to simple runner. {e}")
            st.session_state.user_state, latest_msgs = run_once_fallback(st.session_state.user_state, agents)
    else:
        st.session_state.user_state, latest_msgs = run_once_fallback(st.session_state.user_state, agents)

# overview
with tab_overview:
    st.subheader("Latest Agent Messages")
    if latest_msgs:
        for m in latest_msgs:
            st.markdown(f"- **{m['agent']}**: {m['content']}")
    else:
        st.caption("Run the agents from the sidebar to see messages.")
    st.subheader("Snapshot")
    st.json(_to_view(st.session_state.user_state), expanded=False)

# txns
with tab_txns:
    st.subheader("Recent Transactions")
    conn = get_conn()
    if conn:
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT date, description, amount, category "
                "FROM transactions ORDER BY date DESC LIMIT 50"
            )
            rows = cur.fetchall()
            if rows:
                import pandas as pd
                df = pd.DataFrame(rows, columns=["date", "description", "amount", "category"])
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No transactions yet. Use 'Seed Mock Txns 🧪'.")
        except Exception as e:
            st.error(f"DB error: {e}")
    else:
        st.info("DB not initialized.")

# goals
with tab_goals:
    st.subheader("Goals")
    for g in _to_view(st.session_state.user_state).get("goals", []):
        st.write(f"🎯 **{g.get('name','Goal')}** — target ₹{g.get('target',0):,} by {g.get('deadline','—')} (saved ₹{g.get('saved',0):,})")
    if not _to_view(st.session_state.user_state).get("goals", []):
        st.info("No goals yet. Enable the Goals agent and click 'Run Once'.")

# admin / diagnostics
with tab_admin:
    st.subheader("Project Health")
    st.write(
        "- **State module**: " + ("✅ found" if StateMod else f"❌ import error: {StateErr}") + "\n"
        "- **Graph module**: " + ("✅ found" if GraphMod else f"❌ import error: {GraphErr}") + "\n"
        "- **DB module**: " + ("✅ found" if DBMod else f"❌ import error: {DBErr}") + "\n"
        "- **Seed module**: " + ("✅ found" if SeedMod else f"❌ import error: {SeedErr}")
    )
    st.caption("Tip: if a module exists but shows ❌, click the error to see the exact import exception.")


# # --- put this at the very top of app.py ---
# from pathlib import Path
# import sys

# BASE_DIR = Path(__file__).resolve().parent
# if str(BASE_DIR) not in sys.path:
#     sys.path.insert(0, str(BASE_DIR))
# # ------------------------------------------

# # app.py
# """
# SmartSaverNet 💸 — Streamlit UI
# - Works standalone with graceful fallbacks
# - Auto-discovers agents in ./agents
# - Plugs into orchestrator.{state,graph} and data.{db,seed_mock} when present
# """

# from pathlib import Path
# import importlib
# import sys
# from typing import Any, Dict, List, Tuple

# import streamlit as st

# # --- Optional deps (don't crash if not yet created) ---
# def _safe_import(module_path: str):
#     try:
#         return importlib.import_module(module_path)
#     except Exception:
#         return None

# StateMod = _safe_import("orchestrator.state")
# GraphMod = _safe_import("orchestrator.graph")
# DBMod = _safe_import("data.db")
# SeedMod = _safe_import("data.seed_mock")

# # --- Session State bootstrap -------------------------------------------------

# def _default_state_fallback() -> Dict[str, Any]:
#     """Fallback state until orchestrator.state.default_state() exists."""
#     return {
#         "income": 60000.0,
#         "monthly_spend": 45000.0,
#         "savings_rate": 0.15,
#         "budget": {},
#         "savings_suggestions": [],
#         "debts": [
#             {"name": "Credit Card", "balance": 30000, "apr": 0.36, "min_payment": 1500},
#             {"name": "Student Loan", "balance": 120000, "apr": 0.11, "min_payment": 2500},
#         ],
#         "debt_strategy": "avalanche",
#         "debt_plan": {},
#         "goals": [],
#         "alerts": [],
#     }

# def _get_state_obj():
#     if StateMod and hasattr(StateMod, "default_state"):
#         return StateMod.default_state()
#     return _default_state_fallback()

# def _to_view(state_obj) -> Dict[str, Any]:
#     """Render-friendly dict (supports Pydantic BaseModel later)."""
#     if StateMod and hasattr(state_obj, "model_dump"):
#         return state_obj.model_dump()
#     return dict(state_obj)

# # --- Agent discovery & simple fallback runner --------------------------------

# def discover_agent_modules() -> List[str]:
#     agents_dir = Path(__file__).parent / "agents"
#     if not agents_dir.exists():
#         return []
#     return sorted(
#         p.stem for p in agents_dir.glob("*.py")
#         if p.stem not in {"__init__"} and p.is_file()
#     )

# def load_agents(enabled: List[str]) -> List[Any]:
#     agents = []
#     for name in enabled:
#         mod = _safe_import(f"agents.{name}")
#         if not mod or not hasattr(mod, "Agent"):
#             st.warning(f"Agent `{name}` not found or missing `Agent` class.")
#             continue
#         try:
#             agents.append(mod.Agent())
#         except Exception as e:
#             st.error(f"Failed to init agent `{name}`: {e}")
#     return agents

# def run_once_fallback(state_obj, agents) -> Tuple[Any, List[Dict[str, str]]]:
#     """If orchestrator.graph isn't ready, just run agents sequentially."""
#     msgs = []
#     for a in agents:
#         try:
#             state_obj, msg = a.step(state_obj)
#             msgs.append({"agent": getattr(a, "name", a.__class__.__name__), "content": msg})
#         except Exception as e:
#             msgs.append({"agent": getattr(a, "name", a.__class__.__name__), "content": f"⚠️ Error: {e}"})
#     return state_obj, msgs

# # --- DB helpers (optional) ---------------------------------------------------

# def get_conn():
#     if DBMod and hasattr(DBMod, "get_conn"):
#         return DBMod.get_conn()
#     return None

# def ensure_schema(conn):
#     if DBMod and hasattr(DBMod, "ensure_schema"):
#         return DBMod.ensure_schema(conn)

# def seed_transactions(conn, user_id="demo") -> int:
#     if SeedMod and hasattr(SeedMod, "seed_transactions"):
#         return SeedMod.seed_transactions(conn, user_id=user_id)
#     return 0

# # --- Streamlit UI ------------------------------------------------------------

# st.set_page_config(page_title="SmartSaverNet", page_icon="💸", layout="wide")
# st.title("SmartSaverNet 💸 — Multi-Agent Financial Coach")

# # one-time init
# if "user_state" not in st.session_state:
#     st.session_state.user_state = _get_state_obj()

# with st.sidebar:
#     st.header("Agents")
#     available = discover_agent_modules()
#     if not available:
#         st.info("Place agent files in `./agents/*.py` (budget, savings, debt, goals, alerts, advice).")
#     enabled = st.multiselect("Enable agents", options=available, default=available)

#     st.divider()
#     st.subheader("Run Controls")
#     run_once = st.button("Run Once ▶")
#     reset_state = st.button("Reset State 🔄")

#     st.divider()
#     st.subheader("Data / Admin")
#     colA, colB = st.columns(2)
#     with colA:
#         init_db = st.button("Init DB Schema")
#     with colB:
#         seed_mock = st.button("Seed Mock Txns 🧪")

# # Metrics row
# view = _to_view(st.session_state.user_state)
# c1, c2, c3 = st.columns(3)
# c1.metric("Monthly Income (₹)", f"{view.get('income', 0):,.0f}")
# c2.metric("Monthly Spend (₹)", f"{view.get('monthly_spend', 0):,.0f}")
# c3.metric("Savings Rate", f"{int(view.get('savings_rate', 0)*100)}%")

# # Tabs
# tab_overview, tab_txns, tab_goals, tab_admin = st.tabs(["Overview", "Transactions", "Goals", "Admin"])

# # Admin actions
# if init_db:
#     conn = get_conn()
#     if conn:
#         ensure_schema(conn)
#         st.success("DB schema ensured.")
#     else:
#         st.warning("`data/db.py` not ready yet (expected get_conn(), ensure_schema()).")

# if seed_mock:
#     conn = get_conn()
#     if conn:
#         ensure_schema(conn)
#         n = seed_transactions(conn, user_id="demo")
#         st.success(f"Inserted {n} mock transactions.")
#     else:
#         st.warning("`data/db.py` and `data/seed_mock.py` not ready yet.")

# if reset_state:
#     st.session_state.user_state = _get_state_obj()
#     st.success("State reset.")

# # Build graph (optional)
# graph = None
# if GraphMod and hasattr(GraphMod, "build_graph"):
#     try:
#         graph = GraphMod.build_graph(active_agents=enabled)
#     except Exception as e:
#         st.warning(f"Graph build failed; using simple runner. Details: {e}")

# # Run once
# latest_msgs: List[Dict[str, str]] = []
# if run_once:
#     agents = load_agents(enabled)
#     if graph and hasattr(GraphMod, "run_graph_once"):
#         try:
#             new_state, latest_msgs = GraphMod.run_graph_once(graph, st.session_state.user_state)
#             st.session_state.user_state = new_state
#         except Exception as e:
#             st.error(f"Graph run failed; falling back to simple runner. {e}")
#             st.session_state.user_state, latest_msgs = run_once_fallback(st.session_state.user_state, agents)
#     else:
#         st.session_state.user_state, latest_msgs = run_once_fallback(st.session_state.user_state, agents)

# # Overview tab
# with tab_overview:
#     st.subheader("Latest Agent Messages")
#     if latest_msgs:
#         for m in latest_msgs:
#             st.markdown(f"- **{m['agent']}**: {m['content']}")
#     else:
#         st.caption("Run the agents from the sidebar to see messages.")

#     st.subheader("Snapshot")
#     st.json(_to_view(st.session_state.user_state), expanded=False)

# # Transactions tab
# with tab_txns:
#     st.subheader("Recent Transactions")
#     conn = get_conn()
#     if conn:
#         try:
#             cur = conn.cursor()
#             cur.execute(
#                 "SELECT date, description, amount, category "
#                 "FROM transactions ORDER BY date DESC LIMIT 50"
#             )
#             rows = cur.fetchall()
#             if rows:
#                 import pandas as pd
#                 df = pd.DataFrame(rows, columns=["date", "description", "amount", "category"])
#                 st.dataframe(df, use_container_width=True)
#             else:
#                 st.info("No transactions yet. Use 'Seed Mock Txns 🧪' from the sidebar.")
#         except Exception as e:
#             st.error(f"DB error: {e}")
#     else:
#         st.info("DB not initialized. Implement data/db.py to enable this table.")

# # Goals tab
# with tab_goals:
#     st.subheader("Goals")
#     gs = _to_view(st.session_state.user_state).get("goals", [])
#     if gs:
#         for g in gs:
#             name = g.get("name", "Goal")
#             target = g.get("target", 0)
#             deadline = g.get("deadline", "—")
#             saved = g.get("saved", 0)
#             st.write(f"🎯 **{name}** — target ₹{target:,} by {deadline} (saved ₹{saved:,})")
#     else:
#         st.info("No goals yet. Enable the Goals agent and click 'Run Once'.")

# # Admin tab (reference info)
# with tab_admin:
#     st.subheader("Project Health")
#     st.write(
#         "- **State module**: " + ("✅ found" if StateMod else "❌ missing (orchestrator/state.py)") + "\n"
#         "- **Graph module**: " + ("✅ found" if GraphMod else "❌ missing (orchestrator/graph.py)") + "\n"
#         "- **DB module**: " + ("✅ found" if DBMod else "❌ missing (data/db.py)") + "\n"
#         "- **Seed module**: " + ("✅ found" if SeedMod else "❌ missing (data/seed_mock.py)")
#     )
#     st.caption("Tip: build incrementally—UI works even while back-end files are WIP.")
