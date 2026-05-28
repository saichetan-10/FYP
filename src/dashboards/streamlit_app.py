import os
import time
from datetime import datetime
from typing import Any, Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import pandas as pd
import requests
import streamlit as st

from src.dashboards.manager import DashboardManager

API_URL = os.environ.get("API_URL", "http://localhost:8000")

st.set_page_config(
    page_title="NL Query Engine",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

[data-testid="stSidebar"] { background: #0f172a; border-right: 1px solid #1e293b; }
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }

[data-testid="stMetric"] {
    background: #1e293b; border: 1px solid #334155;
    border-radius: 10px; padding: 14px 18px;
}
[data-testid="stMetricLabel"] { color: #94a3b8 !important; font-size: 0.78rem; }
[data-testid="stMetricValue"] { color: #f1f5f9 !important; font-size: 1.5rem; font-weight: 700; }

.stTabs [data-baseweb="tab-list"] {
    gap: 2px; background: #0f172a; border-radius: 8px; padding: 4px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent; border-radius: 6px;
    color: #64748b; font-weight: 500; padding: 8px 18px;
}
.stTabs [aria-selected="true"] { background: #3b82f6 !important; color: #fff !important; }

.stButton > button {
    background: #3b82f6; color: white; border: none;
    border-radius: 8px; padding: 10px 24px; font-weight: 600;
}
.stButton > button:hover { background: #2563eb; }

.badge-green  { background:#166534; color:#86efac; padding:2px 10px; border-radius:999px; font-size:.75rem; font-weight:600; }
.badge-yellow { background:#713f12; color:#fde68a; padding:2px 10px; border-radius:999px; font-size:.75rem; font-weight:600; }
.badge-red    { background:#7f1d1d; color:#fca5a5; padding:2px 10px; border-radius:999px; font-size:.75rem; font-weight:600; }
.badge-blue   { background:#1e3a5f; color:#93c5fd; padding:2px 10px; border-radius:999px; font-size:.75rem; font-weight:600; }
.badge-purple { background:#3b0764; color:#d8b4fe; padding:2px 10px; border-radius:999px; font-size:.75rem; font-weight:600; }

.agent-card {
    background: #1e293b; border: 1px solid #334155; border-radius: 10px;
    padding: 16px 20px; margin-bottom: 10px;
}
.agent-header { font-weight: 700; font-size: 1rem; color: #f1f5f9; margin-bottom: 4px; }
.agent-sub    { font-size: .8rem; color: #64748b; }
.pipeline-step {
    display: flex; align-items: center; gap: 10px;
    background: #0f172a; border: 1px solid #1e293b;
    border-radius: 8px; padding: 12px 16px; margin-bottom: 6px;
}
.detail-panel {
    background: #0f172a; border: 1px solid #3b82f6; border-radius: 12px;
    padding: 20px 24px; margin-bottom: 18px;
}
.detail-title { font-size: 1.1rem; font-weight: 700; color: #f1f5f9; margin-bottom: 4px; }
.detail-sub   { font-size: .82rem; color: #64748b; }

/* Sidebar nav buttons — slim, ghost style */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    border: 1px solid #1e293b !important;
    color: #cbd5e1 !important;
    border-radius: 6px !important;
    padding: 6px 12px !important;
    font-size: .82rem !important;
    font-weight: 500 !important;
    text-align: left !important;
    width: 100% !important;
    margin-bottom: 2px !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #1e293b !important;
    border-color: #3b82f6 !important;
    color: #93c5fd !important;
}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────

ALL_DBS = ["sales", "inventory", "analytics", "hr", "finance"]

DB_EXAMPLES = {
    "sales":     ["Total revenue by region", "Top 10 customers by revenue",
                  "Monthly revenue trend last year", "Revenue by product category",
                  "Year over year revenue comparison", "Average order value for delivered orders"],
    "inventory": ["Total stock levels by category", "Products below reorder level",
                  "Reorder history last quarter", "Most reordered products"],
    "analytics": ["Daily revenue trend last 90 days", "Customer cohort retention rates",
                  "Top products by total revenue", "Average conversion rate"],
    "hr":        ["Average salary by department", "Headcount by region",
                  "Top performing employees", "Leave taken by department"],
    "finance":   ["Total expenses by department", "Budget variance by category",
                  "Revenue forecast accuracy", "Expense trends last quarter"],
}

AGENT_META = {
    "intent_parser": {
        "icon": "🧠", "label": "Intent Parser",
        "desc": "Extracts entities, metrics, filters, and temporal specs from raw text using regex patterns.",
        "color": "#3b82f6",
    },
    "ontology_mapper": {
        "icon": "🗺️", "label": "Ontology Mapper",
        "desc": "Grounds extracted elements to the formal business ontology via string similarity scoring.",
        "color": "#8b5cf6",
    },
    "constraint_validator": {
        "icon": "✅", "label": "Constraint Validator",
        "desc": "Checks all business rules — valid regions, date ranges, PII protection, active products only.",
        "color": "#10b981",
    },
    "execution_planner": {
        "icon": "🔧", "label": "Execution Planner",
        "desc": "Assembles the final SQL from intent, constraints, and join configurations.",
        "color": "#f59e0b",
    },
    "result_verifier": {
        "icon": "🔍", "label": "Result Verifier",
        "desc": "Wraps DB rows into typed objects, checks plausibility, computes execution stats.",
        "color": "#ef4444",
    },
}


def _get(path: str, timeout: int = 5) -> Dict[str, Any]:
    try:
        r = requests.get(f"{API_URL}{path}", timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception:
        return {}


def _post(path: str, payload: dict, timeout: int = 60) -> Dict[str, Any]:
    try:
        r = requests.post(f"{API_URL}{path}", json=payload, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot reach API — is the backend running?"}
    except Exception as e:
        return {"error": str(e)}


def _drift_colour(d: float) -> str:
    return "badge-green" if d < 0.10 else ("badge-yellow" if d < 0.15 else "badge-red")


# ── Session state ─────────────────────────────────────────────────────────────

if "manager"        not in st.session_state: st.session_state.manager        = DashboardManager()
if "query_results"  not in st.session_state: st.session_state.query_results  = []
if "api_ok"         not in st.session_state: st.session_state.api_ok         = False
if "ex_query"       not in st.session_state: st.session_state.ex_query       = ""
if "sidebar_panel"  not in st.session_state: st.session_state.sidebar_panel  = None  # ("db","sales") or ("agent","intent_parser")
if "last_resp"      not in st.session_state: st.session_state.last_resp      = None  # last query response for persistent clarification buttons
if "clarif_db"      not in st.session_state: st.session_state.clarif_db      = None  # database to use when running a clarification
if "last_run_q"     not in st.session_state: st.session_state.last_run_q     = ""    # the English question that produced last_resp

DB_ICONS   = {"sales": "💰", "inventory": "📦", "analytics": "📊", "hr": "👥", "finance": "🏦"}
AGENT_KEYS = list(AGENT_META.keys())


# ── Health check (runs every rerender, before any tab code) ───────────────────
_health_data = _get("/health", timeout=10)
if not _health_data.get("status"):
    import time as _time; _time.sleep(1)
    _health_data = _get("/health", timeout=10)  # one retry
if _health_data.get("status") == "healthy":
    st.session_state.api_ok = True
else:
    st.session_state.api_ok = False

# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🔍 NL Query Engine")
    st.markdown('<p style="color:#475569;font-size:.82rem;margin-top:-8px;">Natural Language Retrieval System · FYP 2026</p>', unsafe_allow_html=True)
    st.divider()

    health = _health_data
    if health.get("status") == "healthy":
        st.session_state.api_ok = True
        st.markdown('<span class="badge-green">● API Online</span>', unsafe_allow_html=True)
        entities_n = health.get("ontology_entities", 0)
        metrics_n  = health.get("ontology_metrics", 0)
        rules_n    = health.get("ontology_rules", 0)
        st.caption(f'{len(health.get("databases_available",[]))} databases · {entities_n} entities · {metrics_n} metrics · {rules_n} rules')
        if health.get("ai_powered"):
            st.markdown('<span class="badge-purple">⚡ AI-Powered (Claude)</span>', unsafe_allow_html=True)
        else:
            st.markdown('<span class="badge-blue">📐 Rule-Based</span>', unsafe_allow_html=True)
    else:
        st.session_state.api_ok = False
        st.markdown('<span class="badge-red">● API Offline</span>', unsafe_allow_html=True)
        st.caption("Run: `.venv_mac/bin/python3 main.py api`")

    st.divider()

    # ── Clickable Databases ───────────────────────────────────────────────────
    st.markdown('<p style="color:#475569;font-size:.72rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px;">Databases</p>', unsafe_allow_html=True)
    dbs = health.get("databases_available", ALL_DBS)
    for db in dbs:
        icon = DB_ICONS.get(db, "🗄️")
        active = st.session_state.sidebar_panel == ("db", db)
        label = f"{icon} {'▶ ' if active else ''}{db.title()}"
        if st.button(label, key=f"sb_db_{db}"):
            if active:
                st.session_state.sidebar_panel = None
            else:
                st.session_state.sidebar_panel = ("db", db)
            st.rerun()

    st.divider()

    # ── Clickable Agent Pipeline ──────────────────────────────────────────────
    st.markdown('<p style="color:#475569;font-size:.72rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;margin-bottom:4px;">Agent Pipeline</p>', unsafe_allow_html=True)
    for key, meta in AGENT_META.items():
        active = st.session_state.sidebar_panel == ("agent", key)
        label = f"{meta['icon']} {'▶ ' if active else ''}{meta['label']}"
        if st.button(label, key=f"sb_agent_{key}"):
            if active:
                st.session_state.sidebar_panel = None
            else:
                st.session_state.sidebar_panel = ("agent", key)
            st.rerun()

    st.divider()
    st.caption("v2.0 · FastAPI + Streamlit + SQLite/PostgreSQL")


# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("# 🔍 Natural Language Query Engine")
st.markdown('<p style="color:#94a3b8;margin-top:-12px;">Ask plain-English questions across 5 databases — agents handle SQL, constraints, and confidence scoring.</p>', unsafe_allow_html=True)

(tab_home, tab_query, tab_analytics,
 tab_provenance, tab_monitor, tab_knowledge) = st.tabs([
    "  🏠 Home  ",
    "  📊 Query  ",
    "  📈 Analytics  ",
    "  🔎 Provenance  ",
    "  📡 Live Monitor  ",
    "  🧠 Knowledge Base  ",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 0 — HOME (sidebar panel detail + overview)
# ══════════════════════════════════════════════════════════════════════════════

with tab_home:
    panel = st.session_state.sidebar_panel

    if panel:
        ptype, pkey = panel

        st.markdown('<div class="detail-panel">', unsafe_allow_html=True)

        # ── DATABASE PANEL ────────────────────────────────────────────────────
        if ptype == "db":
            icon = DB_ICONS.get(pkey, "🗄️")
            st.markdown(f'<div class="detail-title">{icon} {pkey.title()} Database</div>', unsafe_allow_html=True)
            st.markdown('<div class="detail-sub">Live schema · row counts · example queries</div>', unsafe_allow_html=True)

            close_col, _ = st.columns([1, 8])
            if close_col.button("✕ Close", key="close_db_panel"):
                st.session_state.sidebar_panel = None
                st.rerun()

            if st.session_state.api_ok:
                cache_key = f"_cache_schema_{pkey}"
                if cache_key not in st.session_state:
                    with st.spinner(f"Loading {pkey} schema…"):
                        st.session_state[cache_key] = _get(f"/schema?database={pkey}")
                schema_data = st.session_state[cache_key]

                schema = schema_data.get("schema", {})
                tables = list(schema.keys())

                col1, col2 = st.columns(2)
                col1.metric("Tables", len(tables))
                col2.metric("Database", pkey.title())

                if tables:
                    st.markdown("**Tables & Columns**")
                    tab_sel = st.selectbox("Select table", tables, key=f"tbl_{pkey}")
                    if tab_sel:
                        cols_info = schema.get(tab_sel, {})
                        if isinstance(cols_info, dict):
                            rows = [{"Column": c, "Type": t} for c, t in cols_info.items()]
                        elif isinstance(cols_info, list):
                            rows = [{"Column": c, "Type": "—"} for c in cols_info]
                        else:
                            rows = []
                        if rows:
                            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, height=200)

                st.markdown("**Quick Stats**")
                stats_key = f"_cache_stats_{pkey}"
                if stats_key not in st.session_state:
                    with st.spinner("Fetching row counts…"):
                        qmap = {
                            "sales":     "total revenue count of orders",
                            "inventory": "total stock inventory count",
                            "analytics": "count of daily metrics",
                            "hr":        "count employees headcount",
                            "finance":   "total expenses count",
                        }
                        r = _post("/query", {"query": qmap.get(pkey, "count rows"), "database": pkey, "max_iterations": 1})
                        st.session_state[stats_key] = r.get("results", [])
                results = st.session_state[stats_key]
                if results:
                    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
                else:
                    st.caption("No data returned.")

                st.markdown("**Example Queries — click to run**")
                examples = DB_EXAMPLES.get(pkey, [])
                for ex in examples[:4]:
                    if st.button(f"▶ {ex}", key=f"panel_ex_{pkey}_{ex[:20]}"):
                        st.session_state.ex_query = ex
                        st.session_state.sidebar_panel = None
                        st.rerun()
            else:
                st.error("API offline — start the backend first.")

        # ── AGENT PANEL ───────────────────────────────────────────────────────
        elif ptype == "agent":
            meta = AGENT_META.get(pkey, {})
            st.markdown(f'<div class="detail-title">{meta.get("icon","")} {meta.get("label","")}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="detail-sub">{meta.get("desc","")}</div>', unsafe_allow_html=True)

            close_col, _ = st.columns([1, 8])
            if close_col.button("✕ Close", key="close_agent_panel"):
                st.session_state.sidebar_panel = None
                st.rerun()

            st.markdown("")

            if st.session_state.api_ok:
                if "_cache_ontology" not in st.session_state:
                    st.session_state["_cache_ontology"] = _get("/ontology")
                ontology = st.session_state["_cache_ontology"]

                if pkey == "intent_parser":
                    st.markdown("**Recognises these entity types:**")
                    entities = list(ontology.get("entities", {}).keys())
                    cols3 = st.columns(3)
                    for i, e in enumerate(entities[:18]):
                        cols3[i % 3].markdown(f'<span class="badge-blue">{e}</span>', unsafe_allow_html=True)
                    st.markdown(f"**+ {max(0, len(entities)-18)} more entities**" if len(entities) > 18 else "")

                    st.markdown("**Recognises these metrics:**")
                    metrics = list(ontology.get("metrics", {}).keys())
                    cols3b = st.columns(3)
                    for i, m in enumerate(metrics[:18]):
                        cols3b[i % 3].markdown(f'<span class="badge-purple">{m}</span>', unsafe_allow_html=True)
                    st.markdown(f"**+ {max(0, len(metrics)-18)} more metrics**" if len(metrics) > 18 else "")

                elif pkey == "ontology_mapper":
                    st.markdown("**Ontology summary:**")
                    entities = ontology.get("entities", {})
                    metrics  = ontology.get("metrics", {})
                    mc1, mc2, mc3, mc4 = st.columns(4)
                    mc1.metric("Entities",    len(entities))
                    mc2.metric("Metrics",     len(metrics))
                    mc3.metric("Constraints", ontology.get("constraints", 0))
                    mc4.metric("Join Rules",  ontology.get("join_rules", 0))

                    st.markdown("**Sample entity → ontology path mappings:**")
                    sample_rows = [
                        {"Term": k, "Maps to": f"ontology.entities.{k}", "Table": v.get("table_name", "—")}
                        for k, v in list(entities.items())[:10]
                    ]
                    st.dataframe(pd.DataFrame(sample_rows), use_container_width=True, hide_index=True, height=220)

                elif pkey == "constraint_validator":
                    st.markdown("**Loaded business rules (live from rules.json):**")
                    if "_cache_rules" not in st.session_state:
                        st.session_state["_cache_rules"] = _get("/rules?limit=200")
                    rules_data = st.session_state["_cache_rules"]
                    rules = rules_data.get("rules", [])
                    total = rules_data.get("total_rules", 0)

                    cat_counts: dict = {}
                    for r in rules:
                        rt = r.get("rule_type", "other")
                        cat_counts[rt] = cat_counts.get(rt, 0) + 1

                    st.metric("Total Rules", total)
                    if cat_counts:
                        cat_df = pd.DataFrame(list(cat_counts.items()), columns=["Category", "Count"]).sort_values("Count", ascending=False)
                        st.bar_chart(cat_df.set_index("Category"), color="#10b981", height=220)

                    sev_filter = st.selectbox("Filter by severity", ["ALL", "REQUIRED", "WARNING", "INFO"], key="agent_sev")
                    filtered = [r for r in rules if sev_filter == "ALL" or r.get("severity") == sev_filter]
                    rule_rows = [{"Rule ID": r["rule_id"], "Name": r["name"], "Severity": r.get("severity",""), "Entities": ", ".join(r.get("entities_affected",[])[:3])} for r in filtered[:20]]
                    if rule_rows:
                        st.dataframe(pd.DataFrame(rule_rows), use_container_width=True, hide_index=True, height=250)

                elif pkey == "execution_planner":
                    st.markdown("**SQL dialect & join configurations:**")
                    mc1, mc2 = st.columns(2)
                    mc1.metric("Dialect",    "SQLite (local) / PostgreSQL (Docker)")
                    mc2.metric("Join Rules", ontology.get("join_rules", 0))

                    st.markdown("**Supported GROUP BY dimensions:**")
                    dims = ["region", "tier", "category", "month", "year", "status", "product", "supplier", "region_and_tier"]
                    cols3 = st.columns(3)
                    for i, d in enumerate(dims):
                        cols3[i % 3].markdown(f'<span class="badge-yellow">{d}</span>', unsafe_allow_html=True)

                    st.markdown("**Available metric SELECT expressions:**")
                    metric_rows = [
                        {"Metric Key": k, "SQL Expression": v.get("formula", "—"), "Unit": v.get("unit", "—")}
                        for k, v in list(ontology.get("metrics", {}).items())[:15]
                    ]
                    if metric_rows:
                        st.dataframe(pd.DataFrame(metric_rows), use_container_width=True, hide_index=True, height=280)

                elif pkey == "result_verifier":
                    st.markdown("**Verifies results against metric validity rules:**")
                    if "_cache_rules_mv" not in st.session_state:
                        st.session_state["_cache_rules_mv"] = _get("/rules?category=metric_validity&limit=50")
                    rules_data = st.session_state["_cache_rules_mv"]
                    mv_rules = rules_data.get("rules", [])
                    if mv_rules:
                        mv_rows = [{"Rule": r["name"], "Condition": r.get("condition","")[:80], "Severity": r.get("severity","")} for r in mv_rules[:15]]
                        st.dataframe(pd.DataFrame(mv_rows), use_container_width=True, hide_index=True, height=260)
                    else:
                        st.caption("No metric validity rules loaded.")

                    last_resp = st.session_state.last_resp
                    if last_resp:
                        trace = last_resp.get("agent_trace", [])
                        verifier_steps = [s for s in trace if s.get("agent") == "result_verifier"]
                        if verifier_steps:
                            st.markdown("**Last verification result:**")
                            details = verifier_steps[-1].get("details", {})
                            vc1, vc2, vc3 = st.columns(3)
                            vc1.metric("Rows Verified", details.get("result_count", 0))
                            vc2.metric("Source",        details.get("source", "—"))
                            vc3.metric("Columns",       len(details.get("columns", [])))

            else:
                st.error("API offline.")

            last_resp = st.session_state.last_resp
            if last_resp and pkey != "result_verifier":
                trace = last_resp.get("agent_trace", [])
                agent_steps = [s for s in trace if s.get("agent") == pkey]
                if agent_steps:
                    st.divider()
                    st.markdown(f"**Last run trace ({len(agent_steps)} step{'s' if len(agent_steps)>1 else ''}):**")
                    for step in agent_steps:
                        with st.expander(f"`{step.get('action','')}`", expanded=False):
                            st.json(step.get("details", {}))

        st.markdown('</div>', unsafe_allow_html=True)

    else:
        # ── Default home screen when no panel is open ─────────────────────────
        health = _health_data
        st.markdown("### Welcome to NL Query Engine")
        st.markdown('<p style="color:#64748b;">Select a database or agent from the left sidebar to explore, or jump straight to the Query tab to run a question.</p>', unsafe_allow_html=True)
        st.markdown("")

        h1, h2, h3, h4, h5 = st.columns(5)
        h1.metric("Databases",  len(health.get("databases_available", [])))
        h2.metric("Entities",   health.get("ontology_entities", 0))
        h3.metric("Metrics",    health.get("ontology_metrics", 0))
        h4.metric("Rules",      health.get("ontology_rules", 0))
        h5.metric("AI Powered", "Yes" if health.get("ai_powered") else "No")

        st.divider()
        st.markdown("#### Databases")
        db_cols = st.columns(5)
        for i, db in enumerate(ALL_DBS):
            icon = DB_ICONS.get(db, "🗄️")
            examples = DB_EXAMPLES.get(db, [])
            with db_cols[i]:
                st.markdown(f"**{icon} {db.title()}**")
                for ex in examples[:3]:
                    if st.button(ex, key=f"home_ex_{db}_{ex[:15]}", use_container_width=True):
                        st.session_state.ex_query = ex
                        st.rerun()

        st.divider()
        st.markdown("#### Agent Pipeline")
        ag_cols = st.columns(len(AGENT_META))
        for i, (key, meta) in enumerate(AGENT_META.items()):
            with ag_cols[i]:
                st.markdown(
                    f'<div style="text-align:center;background:#1e293b;border:1px solid #334155;'
                    f'border-radius:8px;padding:14px 6px;">'
                    f'<div style="font-size:1.8rem;">{meta["icon"]}</div>'
                    f'<div style="font-size:.8rem;font-weight:700;color:#f1f5f9;margin-top:6px;">{meta["label"]}</div>'
                    f'<div style="font-size:.72rem;color:#64748b;margin-top:4px;">{meta["desc"][:60]}…</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — QUERY INTERFACE
# ══════════════════════════════════════════════════════════════════════════════

with tab_query:
    st.markdown("### Run a Natural Language Query")

    with st.form("query_form"):
        q_col, db_col, it_col = st.columns([5, 1.5, 1])
        with q_col:
            query_text = st.text_input("Question", placeholder="e.g. Show total revenue by region for last year",
                                       label_visibility="collapsed")
        with db_col:
            db_choice = st.selectbox("DB", ALL_DBS, label_visibility="collapsed")
        with it_col:
            iter_choice = st.number_input("Iters", 1, 10, 5, label_visibility="collapsed")
        submitted = st.form_submit_button("▶  Run Query", use_container_width=False)

    # Example queries
    st.markdown('<p style="color:#475569;font-size:.75rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;margin-top:4px;">Quick examples</p>', unsafe_allow_html=True)
    examples = DB_EXAMPLES.get(db_choice, DB_EXAMPLES["sales"])
    ecols = st.columns(3)
    for i, ex in enumerate(examples):
        if ecols[i % 3].button(ex, key=f"qex_{i}", use_container_width=True):
            st.session_state.ex_query = ex
            st.rerun()

    run_q = ""
    run_db = db_choice
    if submitted and query_text.strip():
        run_q = query_text.strip()
        st.session_state.clarif_db = None  # reset clarif db on manual submit
    elif st.session_state.ex_query:
        run_q = st.session_state.ex_query
        st.session_state.ex_query = ""
        # use clarif_db if set (from clicking a suggestion), otherwise fall back to dropdown
        if st.session_state.clarif_db:
            run_db = st.session_state.clarif_db
            st.session_state.clarif_db = None

    if run_q:
        if not st.session_state.api_ok:
            st.error("API offline. Start with: `venv/bin/python3 main.py api`")
        else:
            with st.spinner(f'Running "{run_q[:60]}" on **{run_db}** …'):
                resp = _post("/query", {"query": run_q, "database": run_db,
                                        "max_iterations": int(iter_choice)})

            if "error" in resp:
                st.error(f"Query failed: {resp['error']}")
            else:
                st.session_state.last_resp = resp
                st.session_state.last_run_q = run_q
                st.session_state.query_results.append(resp)
                drift = resp.get("confidence", {}).get("composite_drift", 0)
                st.session_state.manager.add_query_to_history({
                    "query_id": resp.get("query_id"),
                    "user_query": resp.get("user_query"),
                    "timestamp": resp.get("timestamp") or datetime.utcnow().isoformat(),
                    "success": resp.get("status") == "success",
                    "confidence": 1.0 - drift,
                    "semantic_drift": drift,
                })

    # Render last result persistently (survives reruns from clarification button clicks)
    if st.session_state.last_resp:
        resp = st.session_state.last_resp
        drift = resp.get("confidence", {}).get("composite_drift", 0)

        st.divider()
        if st.session_state.last_run_q:
            st.markdown(f"**Query:** {st.session_state.last_run_q}")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Rows Returned",   resp.get("result_count", 0))
        k2.metric("Exec Time (ms)",  f"{resp.get('execution_time_ms', 0):.1f}")
        k3.metric("Semantic Drift",  f"{drift:.4f}")
        k4.metric("Status",          resp.get("status", "—").title())

        # Auto-reroute info banner
        if resp.get("auto_rerouted") and resp.get("suggested_database"):
            st.info(f"💡 Auto-routed to **{resp['suggested_database']}** database — that's where this data lives.")

        conf = resp.get("confidence", {})
        st.markdown("**Drift Component Breakdown**")
        d1, d2, d3 = st.columns(3)
        d1.progress(conf.get("intent_alignment", 0),     text=f"Intent Alignment  {conf.get('intent_alignment',0):.3f}")
        d2.progress(conf.get("constraint_adherence", 0), text=f"Constraint Adherence  {conf.get('constraint_adherence',0):.3f}")
        d3.progress(conf.get("result_plausibility", 0),  text=f"Result Plausibility  {conf.get('result_plausibility',0):.3f}")

        sql = resp.get("final_query", "")
        if sql:
            with st.expander("Generated SQL", expanded=True):
                st.code(sql, language="sql")

        results = resp.get("results", [])
        if results:
            import pandas as pd
            st.markdown("**Query Results**")
            df = pd.DataFrame(results)
            st.dataframe(df, use_container_width=True, height=min(420, 40 + 35*len(df)))
            dl, _ = st.columns([1, 5])
            dl.download_button("⬇ CSV", df.to_csv(index=False).encode(),
                               f"results_{datetime.utcnow().strftime('%H%M%S')}.csv", "text/csv")
        else:
            st.info("No rows returned.")

        with st.expander("Why this answer?"):
            st.write(resp.get("explanation", "—"))

        # ── Clarification suggestions (shown whenever drift > 0.15) ──────────
        clarif_opts = resp.get("clarification_options", [])
        has_rows = resp.get("result_count", 0) > 0
        if clarif_opts:
            st.markdown("---")
            if has_rows:
                st.warning(
                    f"⚠️ Semantic drift is **{drift:.4f}** — results were returned but may not fully "
                    f"match your intent. Here are **{len(clarif_opts)} better-matched queries** "
                    f"based on the actual business data — click one to run it:"
                )
            else:
                st.error(
                    f"⚠️ Semantic drift too high ({drift:.4f}) — 0 rows returned. "
                    f"The query could not be matched to the available data."
                )
                _failed_sql = resp.get("final_query", "")
                if _failed_sql:
                    with st.expander("See attempted SQL"):
                        st.code(_failed_sql, language="sql")
                st.markdown(
                    f"**Here are {len(clarif_opts)} queries better matched to the available data — click one to run it:**"
                )

            _orig_q = resp.get("user_query", "q")
            _clarif_target_db = resp.get("suggested_database") or db_choice
            for _ci, _opt in enumerate(clarif_opts):
                if st.button(f"▶  {_opt}", key=f"clarif_{_ci}_{_orig_q[:10]}"):
                    st.session_state.last_resp = None
                    st.session_state.clarif_db = _clarif_target_db
                    st.session_state.ex_query = _opt
                    st.rerun()
            if st.button("✕  Dismiss suggestions", key="clarif_dismiss"):
                st.session_state.last_resp = {**resp, "clarification_options": []}
                st.rerun()
            st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — ANALYTICS DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

with tab_analytics:
    st.markdown("### Analytics Dashboard")
    st.markdown('<p style="color:#64748b;font-size:.88rem;">Pre-built charts powered by live queries to each database.</p>', unsafe_allow_html=True)

    if not st.session_state.api_ok:
        st.error("API offline — start the backend first.")
    else:
        an_db = st.selectbox("Select database to explore", ALL_DBS, key="an_db")

        if st.button("🔄 Load Charts", key="load_charts"):
            st.session_state[f"an_loaded_{an_db}"] = True

        if st.session_state.get(f"an_loaded_{an_db}"):
            import pandas as pd

            def _quick(q: str) -> pd.DataFrame:
                r = _post("/query", {"query": q, "database": an_db, "max_iterations": 3})
                rows = r.get("results", [])
                return pd.DataFrame(rows) if rows else pd.DataFrame()

            if an_db == "sales":
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Revenue by Region**")
                    df = _quick("show total revenue by region")
                    if not df.empty:
                        st.bar_chart(df.set_index(df.columns[0])[df.columns[1]] if len(df.columns) > 1 else df)
                with c2:
                    st.markdown("**Revenue by Customer Tier**")
                    df = _quick("show total revenue by customer tier")
                    if not df.empty:
                        st.bar_chart(df.set_index(df.columns[0])[df.columns[1]] if len(df.columns) > 1 else df)

                st.markdown("**Monthly Revenue Trend**")
                df = _quick("show monthly revenue trend last year")
                if not df.empty:
                    num_cols = df.select_dtypes("number").columns.tolist()
                    if num_cols and len(df.columns) > 1:
                        st.line_chart(df.set_index(df.columns[0])[num_cols[0]])

                c3, c4 = st.columns(2)
                with c3:
                    st.markdown("**Revenue by Product Category**")
                    df = _quick("revenue by product category")
                    if not df.empty and len(df.columns) > 1:
                        st.bar_chart(df.set_index(df.columns[0])[df.columns[1]])
                with c4:
                    st.markdown("**Top 10 Customers**")
                    df = _quick("top 10 customers by revenue")
                    if not df.empty:
                        st.dataframe(df, use_container_width=True, hide_index=True)

            elif an_db == "inventory":
                st.markdown("**Reorder History (last quarter)**")
                df = _quick("reorder history last quarter")
                if not df.empty:
                    st.dataframe(df, use_container_width=True, hide_index=True)

                st.markdown("**Total Stock**")
                df = _quick("total stock inventory count")
                if not df.empty:
                    st.metric("Total Units in Stock", df.iloc[0, 0] if len(df.columns) == 1 else str(df.iloc[0].to_dict()))

            elif an_db == "analytics":
                st.markdown("**Daily Revenue Trend (last 90 days)**")
                df = _quick("daily revenue trend last 90 days")
                if not df.empty and len(df.columns) > 1:
                    num_cols = df.select_dtypes("number").columns.tolist()
                    if num_cols:
                        st.line_chart(df.set_index(df.columns[0])[num_cols[0]])

                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Cohort Retention Rates**")
                    df = _quick("customer cohort retention rates")
                    if not df.empty:
                        st.dataframe(df.head(20), use_container_width=True, hide_index=True)
                with c2:
                    st.markdown("**Top Products by Revenue**")
                    df = _quick("top products by total revenue")
                    if not df.empty:
                        st.dataframe(df.head(20), use_container_width=True, hide_index=True)

            elif an_db == "hr":
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Headcount by Region**")
                    df = _quick("count employees by region")
                    if not df.empty and len(df.columns) > 1:
                        st.bar_chart(df.set_index(df.columns[0])[df.columns[1]])
                with c2:
                    st.markdown("**Headcount by Department**")
                    df = _quick("count employees by department")
                    if not df.empty and len(df.columns) > 1:
                        st.bar_chart(df.set_index(df.columns[0])[df.columns[1]])

                st.markdown("**Average Salary by Department**")
                df = _quick("average salary by department")
                if not df.empty and len(df.columns) > 1:
                    st.bar_chart(df.set_index(df.columns[0])[df.columns[1]])

            elif an_db == "finance":
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("**Expenses by Department**")
                    df = _quick("total expenses by department")
                    if not df.empty and len(df.columns) > 1:
                        st.bar_chart(df.set_index(df.columns[0])[df.columns[1]])
                with c2:
                    st.markdown("**Budget vs Spent by Category**")
                    df = _quick("budget variance by category")
                    if not df.empty:
                        st.dataframe(df.head(20), use_container_width=True, hide_index=True)

                st.markdown("**Forecast Accuracy by Metric**")
                df = _quick("revenue forecast accuracy")
                if not df.empty:
                    st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("Select a database and click **Load Charts** to visualise pre-built analytics.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — PROVENANCE & HISTORY
# ══════════════════════════════════════════════════════════════════════════════

with tab_provenance:
    st.markdown("### Query Provenance & History")

    history = st.session_state.manager.query_history
    if not history:
        st.info("No queries yet — run one in the Query tab.")
    else:
        import pandas as pd
        total = len(history)
        avg_drift = sum(e["semantic_drift"] for e in history) / total
        converged = sum(1 for e in history if e["semantic_drift"] < 0.15)

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Queries", total)
        k2.metric("Avg Drift",     f"{avg_drift:.4f}")
        k3.metric("Converged",     f"{converged}/{total}")
        k4.metric("Success Rate",  f"{100*sum(1 for e in history if e['status']=='success')//total}%")

        if len(history) > 1:
            st.markdown("**Drift Over Time**")
            drift_df = pd.DataFrame({
                "Query #": range(1, len(history)+1),
                "Drift":   [e["semantic_drift"] for e in history],
            }).set_index("Query #")
            st.line_chart(drift_df, color="#3b82f6", height=180)

        st.markdown("**Query Log**")
        rows = [{
            "Query ID":   e["query_id"],
            "Question":   (e.get("user_query") or "")[:70],
            "Timestamp":  (e.get("timestamp") or "")[:19],
            "Status":     e.get("status",""),
            "Drift":      round(e["semantic_drift"],4),
            "Confidence": round(1-e["semantic_drift"],4),
        } for e in reversed(history)]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("**Inspect a query**")
        selected_id = st.selectbox("Query ID", [e["query_id"] for e in reversed(history)], key="prov_sel")
        full = next((r for r in reversed(st.session_state.query_results) if r.get("query_id") == selected_id), None)
        sel  = next((e for e in history if e["query_id"] == selected_id), None)

        if sel and full:
            pa, pb = st.columns(2)
            pa.markdown(f'**Question:** "{sel.get("user_query","")}"')
            pb.markdown(f'**Drift:** {sel["semantic_drift"]:.4f} · **Confidence:** {1-sel["semantic_drift"]:.4f}')

            conf = full.get("confidence", {})
            ia, ca, rp = conf.get("intent_alignment",0), conf.get("constraint_adherence",0), conf.get("result_plausibility",0)
            m1, m2, m3 = st.columns(3)
            m1.metric("Intent Alignment",     f"{ia:.4f}")
            m2.metric("Constraint Adherence", f"{ca:.4f}")
            m3.metric("Result Plausibility",  f"{rp:.4f}")

            if full.get("final_query"):
                with st.expander("SQL"):
                    st.code(full["final_query"], language="sql")
            trace = full.get("agent_trace", [])
            if trace:
                with st.expander(f"Agent trace ({len(trace)} steps)"):
                    for step in trace:
                        st.markdown(f'<span class="badge-blue">{step.get("agent","")}</span> &nbsp; **{step.get("action","")}**', unsafe_allow_html=True)
                        if step.get("details"):
                            st.json(step["details"], expanded=False)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — LIVE MONITOR
# ══════════════════════════════════════════════════════════════════════════════

with tab_monitor:
    st.markdown("### Live Pipeline Monitor")

    _, rc = st.columns([6, 1])
    auto = rc.toggle("Auto 5s", value=False, key="mon_auto")
    if st.button("↺ Refresh now", key="mon_refresh"):
        st.rerun()

    if not st.session_state.api_ok:
        st.error("API offline.")
    else:
        live  = _get("/live")
        stats = _get("/stats")

        uptime = live.get("uptime_seconds", 0)
        hrs, rem = divmod(int(uptime), 3600)
        mins, secs = divmod(rem, 60)

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Total Queries",      live.get("total_queries", 0))
        m2.metric("Avg Drift",          f"{live.get('avg_drift_score',0):.4f}")
        m3.metric("Convergence Rate",   f"{live.get('convergence_rate',0)*100:.1f}%")
        m4.metric("Queries (last hr)",  live.get("queries_last_hour", 0))
        m5.metric("Uptime",             f"{hrs}h {mins}m {secs}s")

        recent = live.get("recent_queries", [])
        if recent:
            import pandas as pd
            st.markdown("**Recent Queries**")
            rows = []
            for q in recent:
                d = q.get("drift", 0)
                rows.append({
                    "●":         "🟢" if d < 0.10 else ("🟡" if d < 0.15 else "🔴"),
                    "Question":  (q.get("user_query",""))[:65],
                    "Drift":     round(d, 4),
                    "Conv.":     "✓" if q.get("converged") else "✗",
                    "Status":    q.get("status",""),
                    "Time (ms)": round(q.get("execution_ms",0),1),
                    "Timestamp": (q.get("timestamp",""))[:19],
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        else:
            st.info("No queries yet — run one in the Query tab.")

        if stats:
            import pandas as pd
            sc1, sc2 = st.columns(2)
            with sc1:
                dd = stats.get("drift_distribution", {})
                if any(dd.values()):
                    st.markdown("**Drift Distribution**")
                    dist_df = pd.DataFrame({
                        "Band":    ["Low (<0.10)", "Medium (0.10–0.20)", "High (>0.20)"],
                        "Queries": [dd.get("low",0), dd.get("medium",0), dd.get("high",0)],
                    }).set_index("Band")
                    st.bar_chart(dist_df, color="#3b82f6", height=220)
            with sc2:
                ec = stats.get("top_entity_types", {})
                if ec:
                    st.markdown("**Top Entity Types**")
                    ent_df = pd.DataFrame(list(ec.items()), columns=["Entity","Count"]).set_index("Entity")
                    st.bar_chart(ent_df, color="#8b5cf6", height=220)

            la1, la2, la3 = st.columns(3)
            la1.metric("Latency P50 (ms)", stats.get("latency_p50_ms",0))
            la2.metric("Latency P95 (ms)", stats.get("latency_p95_ms",0))
            la3.metric("Total Processed",  stats.get("total_queries",0))

        # ── Live Drift Trend Chart ────────────────────────────────────────────
        session_results = st.session_state.query_results
        if session_results:
            st.divider()
            st.markdown("### 📉 Live Drift Trend (This Session)")
            st.caption("Semantic drift score per query — lower is better. Dashed lines mark thresholds.")

            drift_points = [
                {
                    "Q#":   i + 1,
                    "Query": (r.get("user_query", ""))[:40],
                    "Drift": round(r.get("confidence", {}).get("composite_drift", 0), 4),
                    "Status": r.get("status", ""),
                }
                for i, r in enumerate(session_results)
            ]
            drift_df = pd.DataFrame(drift_points)

            fig, ax = plt.subplots(figsize=(10, 3.5))
            fig.patch.set_facecolor("#0f172a")
            ax.set_facecolor("#1e293b")

            xs = drift_df["Q#"].tolist()
            ys = drift_df["Drift"].tolist()

            # Colour each point by drift band
            colors = ["#22c55e" if d < 0.10 else ("#f59e0b" if d < 0.15 else "#ef4444") for d in ys]
            ax.plot(xs, ys, color="#3b82f6", linewidth=2, zorder=1)
            ax.scatter(xs, ys, c=colors, s=60, zorder=2)

            # Threshold lines
            ax.axhline(0.10, color="#22c55e", linewidth=0.8, linestyle="--", alpha=0.7, label="Good (0.10)")
            ax.axhline(0.15, color="#f59e0b", linewidth=0.8, linestyle="--", alpha=0.7, label="Warning (0.15)")

            # Shade the "good" region
            ax.fill_between(xs, 0, 0.10, alpha=0.08, color="#22c55e")

            ax.set_xlabel("Query #", color="#94a3b8", fontsize=9)
            ax.set_ylabel("Semantic Drift", color="#94a3b8", fontsize=9)
            ax.tick_params(colors="#64748b", labelsize=8)
            ax.spines[:].set_color("#334155")
            ax.legend(fontsize=8, framealpha=0.2, labelcolor="#94a3b8",
                      facecolor="#1e293b", edgecolor="#334155")
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

            # Compact table under chart
            st.dataframe(drift_df, use_container_width=True, hide_index=True, height=200)

    if auto:
        time.sleep(5)
        st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — KNOWLEDGE BASE
# ══════════════════════════════════════════════════════════════════════════════

with tab_knowledge:
    st.markdown("### Knowledge Base")
    st.markdown('<p style="color:#64748b;font-size:.88rem;">Browse all databases, entities, metrics and business rules that power the query engine.</p>', unsafe_allow_html=True)

    if not st.session_state.api_ok:
        st.error("API offline — start the backend first.")
    else:
        # ── Summary cards ────────────────────────────────────────────────────
        health = _health_data
        kc1, kc2, kc3, kc4, kc5 = st.columns(5)
        kc1.metric("Databases",  len(health.get("databases_available", [])))
        kc2.metric("Entities",   health.get("ontology_entities", 0))
        kc3.metric("Metrics",    health.get("ontology_metrics", 0))
        kc4.metric("Rules",      health.get("ontology_rules", 0))
        kc5.metric("AI Powered", "Yes" if health.get("ai_powered") else "No")

        st.divider()

        kb_tab1, kb_tab2, kb_tab3, kb_tab4 = st.tabs([
            "🗄️ Databases & Schema",
            "🏷️ Entities",
            "📐 Metrics",
            "📋 Rules",
        ])

        # ── Databases & Schema ────────────────────────────────────────────────
        with kb_tab1:
            import pandas as pd
            dbs = health.get("databases_available", ALL_DBS)
            db_sel = st.selectbox("Select database", dbs, key="kb_db_sel")
            if db_sel:
                cache_key = f"_cache_kb_schema_{db_sel}"
                if cache_key not in st.session_state:
                    st.session_state[cache_key] = _get(f"/schema?database={db_sel}")
                schema_data = st.session_state[cache_key]
                tables = schema_data.get("tables", [])
                st.markdown(f"**{db_sel}** — {len(tables)} tables")
                tbl_sel = st.selectbox("Select table to inspect", tables, key=f"kb_tbl_{db_sel}")
                if tbl_sel:
                    cols = schema_data.get("schema", {}).get(tbl_sel, {})
                    col_df = pd.DataFrame(
                        [{"Column": c, "Type": t} for c, t in cols.items()]
                    )
                    st.dataframe(col_df, use_container_width=True, hide_index=True)

                    # Row count + sample rows
                    sample_cache = f"_cache_kb_sample_{db_sel}_{tbl_sel}"
                    if sample_cache not in st.session_state:
                        sample_resp = _post("/query", {
                            "query": f"show first 10 rows from {tbl_sel}",
                            "database": db_sel,
                            "max_iterations": 1,
                        })
                        st.session_state[sample_cache] = sample_resp
                    sample_resp = st.session_state[sample_cache]
                    sample_rows = sample_resp.get("results", [])
                    if sample_rows:
                        st.markdown(f"**Sample rows** ({len(sample_rows)} shown)")
                        st.dataframe(pd.DataFrame(sample_rows), use_container_width=True,
                                     height=min(350, 40 + 35 * len(sample_rows)), hide_index=True)

        # ── Entities ──────────────────────────────────────────────────────────
        with kb_tab2:
            import pandas as pd
            if "_cache_kb_ontology" not in st.session_state:
                st.session_state["_cache_kb_ontology"] = _get("/ontology")
            ont = st.session_state["_cache_kb_ontology"]
            entities_raw = ont.get("entities", {})

            # Build summary table
            ent_rows = []
            for eid, edef in entities_raw.items():
                ent_rows.append({
                    "Entity ID":   eid,
                    "Name":        edef.get("name", ""),
                    "Database":    edef.get("source_database", "—"),
                    "Table":       edef.get("table_name", ""),
                    "Columns":     len(edef.get("attributes", {})),
                    "Aliases":     len(edef.get("natural_language_aliases", [])),
                })
            ent_df = pd.DataFrame(ent_rows)

            # Filter by database
            db_filter = st.selectbox("Filter by database", ["All"] + ALL_DBS, key="kb_ent_db")
            if db_filter != "All":
                ent_df = ent_df[ent_df["Database"] == db_filter]

            st.markdown(f"**{len(ent_df)} entities**")
            st.dataframe(ent_df, use_container_width=True, hide_index=True, height=400)

            # Detail expander
            sel_eid = st.selectbox("Inspect entity", list(entities_raw.keys()), key="kb_ent_sel")
            if sel_eid and sel_eid in entities_raw:
                edef = entities_raw[sel_eid]
                with st.expander(f"📄 {edef.get('name')} — full definition", expanded=True):
                    col_a, col_b = st.columns(2)
                    with col_a:
                        st.markdown(f"**Description:** {edef.get('description','—')}")
                        st.markdown(f"**Database:** `{edef.get('source_database','—')}`")
                        st.markdown(f"**Table:** `{edef.get('table_name','—')}`")
                        st.markdown(f"**Primary key:** `{edef.get('primary_key','—')}`")
                    with col_b:
                        attrs = edef.get("attributes", {})
                        attr_df = pd.DataFrame([{"Column": c, "Type": t} for c, t in attrs.items()])
                        st.dataframe(attr_df, use_container_width=True, hide_index=True)
                    aliases = edef.get("natural_language_aliases", [])
                    if aliases:
                        st.markdown("**Aliases:** " + " · ".join(f"`{a}`" for a in aliases))

            # ── Entity Relationship Graph ──────────────────────────────────────
            st.divider()
            st.markdown("### 🕸️ Entity Relationship Graph")
            st.caption("Network of all 49 entities across 5 databases. Nodes coloured by database; edges represent join relationships.")
            with st.expander("Show Entity Relationship Graph", expanded=False):
                DB_COLORS = {
                    "sales":     "#3b82f6",
                    "hr":        "#10b981",
                    "finance":   "#f59e0b",
                    "inventory": "#8b5cf6",
                    "analytics": "#ef4444",
                }

                G = nx.Graph()

                # Add entity nodes
                for eid, edef in entities_raw.items():
                    G.add_node(eid, db=edef.get("source_database", "sales"), label=edef.get("name", eid))

                # Get join rules from ontology to build edges
                if "_cache_kb_ontology_full" not in st.session_state:
                    raw_ont = _get("/ontology")
                    st.session_state["_cache_kb_ontology_full"] = raw_ont
                raw_ont = st.session_state["_cache_kb_ontology_full"]

                # Build edges from entity table cross-references in ontology
                # We infer joins from shared attributes (foreign key style)
                seen_pairs = set()
                for eid, edef in entities_raw.items():
                    attrs = edef.get("attributes", {})
                    for attr_name in attrs:
                        if attr_name.endswith("_id") and attr_name != edef.get("primary_key"):
                            ref_entity = attr_name[:-3].upper()
                            if ref_entity in entities_raw:
                                pair = tuple(sorted([eid, ref_entity]))
                                if pair not in seen_pairs:
                                    G.add_edge(eid, ref_entity, weight=1)
                                    seen_pairs.add(pair)

                # Also add co-DB edges (entities in same DB are loosely related)
                db_groups: Dict[str, list] = {}
                for eid, edef in entities_raw.items():
                    db = edef.get("source_database", "sales")
                    db_groups.setdefault(db, []).append(eid)

                # Layout
                pos = nx.spring_layout(G, k=2.5, seed=42)

                node_colors = [DB_COLORS.get(G.nodes[n].get("db", "sales"), "#64748b") for n in G.nodes]
                node_labels = {n: G.nodes[n].get("label", n) for n in G.nodes}

                fig, ax = plt.subplots(figsize=(14, 9))
                fig.patch.set_facecolor("#0f172a")
                ax.set_facecolor("#0f172a")

                # Draw edges
                nx.draw_networkx_edges(G, pos, ax=ax, edge_color="#334155", width=1.0, alpha=0.6)

                # Draw nodes
                nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors,
                                       node_size=500, alpha=0.92)

                # Draw labels (small font)
                nx.draw_networkx_labels(G, pos, labels=node_labels, ax=ax,
                                        font_size=5.5, font_color="#f1f5f9", font_weight="bold")

                # Legend
                patches = [mpatches.Patch(color=c, label=db.title()) for db, c in DB_COLORS.items()]
                ax.legend(handles=patches, loc="lower right", fontsize=8,
                          framealpha=0.3, facecolor="#1e293b", edgecolor="#334155",
                          labelcolor="#f1f5f9")

                ax.set_title(f"{len(G.nodes)} Entities · {len(G.edges)} Relationships",
                             color="#94a3b8", fontsize=10, pad=12)
                ax.axis("off")
                plt.tight_layout()
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)

                # Summary table of edges
                if G.edges:
                    edge_rows = [
                        {"From": u, "To": v,
                         "From DB": entities_raw.get(u, {}).get("source_database", "—"),
                         "To DB":   entities_raw.get(v, {}).get("source_database", "—")}
                        for u, v in list(G.edges)[:30]
                    ]
                    st.dataframe(pd.DataFrame(edge_rows), use_container_width=True, hide_index=True)

        # ── Metrics ───────────────────────────────────────────────────────────
        with kb_tab3:
            import pandas as pd
            if "_cache_kb_ontology" not in st.session_state:
                st.session_state["_cache_kb_ontology"] = _get("/ontology")
            ont = st.session_state["_cache_kb_ontology"]
            metrics_raw = ont.get("metrics", {})

            met_rows = []
            for mid, mdef in metrics_raw.items():
                met_rows.append({
                    "Metric ID":    mid,
                    "Name":         mdef.get("name", ""),
                    "Aggregation":  mdef.get("aggregation_type", ""),
                    "Unit":         mdef.get("unit", ""),
                    "Formula":      (mdef.get("formula", ""))[:60],
                    "Refresh":      mdef.get("refresh_frequency", ""),
                })
            met_df = pd.DataFrame(met_rows)

            # Filter
            agg_filter = st.selectbox("Filter by aggregation", ["All", "SUM", "AVG", "COUNT", "RATIO", "MAX", "MIN"], key="kb_met_agg")
            if agg_filter != "All":
                met_df = met_df[met_df["Aggregation"] == agg_filter]

            st.markdown(f"**{len(met_df)} metrics**")
            st.dataframe(met_df, use_container_width=True, hide_index=True, height=400)

            sel_mid = st.selectbox("Inspect metric", list(metrics_raw.keys()), key="kb_met_sel")
            if sel_mid and sel_mid in metrics_raw:
                mdef = metrics_raw[sel_mid]
                with st.expander(f"📐 {mdef.get('name')} — full definition", expanded=True):
                    st.markdown(f"**Description:** {mdef.get('description','—')}")
                    st.markdown(f"**Formula:** `{mdef.get('formula','—')}`")
                    st.markdown(f"**Valid range:** {mdef.get('valid_range', [0,'∞'])}")
                    st.markdown(f"**Requires entities:** {', '.join(mdef.get('requires_entities', []))}")
                    aliases = mdef.get("natural_language_aliases", [])
                    if aliases:
                        st.markdown("**Aliases:** " + " · ".join(f"`{a}`" for a in aliases))

        # ── Rules ─────────────────────────────────────────────────────────────
        with kb_tab4:
            import pandas as pd
            if "_cache_kb_rules" not in st.session_state:
                st.session_state["_cache_kb_rules"] = _get("/rules?limit=500")
            rules_data = st.session_state["_cache_kb_rules"]
            rules_list = rules_data.get("rules", [])

            rule_rows = []
            for r in rules_list:
                rule_rows.append({
                    "Rule ID":    r.get("rule_id", ""),
                    "Name":       r.get("name", ""),
                    "Type":       r.get("rule_type", ""),
                    "Severity":   r.get("severity", ""),
                    "Description": (r.get("description", ""))[:80],
                    "Entities":   ", ".join(r.get("entities_affected", []))[:40],
                })
            rules_df = pd.DataFrame(rule_rows)

            rc1, rc2 = st.columns(2)
            sev_filter = rc1.selectbox("Filter by severity", ["All", "REQUIRED", "WARNING", "INFO"], key="kb_rule_sev")
            type_filter = rc2.selectbox("Filter by type", ["All"] + sorted(rules_df["Type"].unique().tolist()), key="kb_rule_type")

            if sev_filter != "All":
                rules_df = rules_df[rules_df["Severity"] == sev_filter]
            if type_filter != "All":
                rules_df = rules_df[rules_df["Type"] == type_filter]

            # Colour severity
            def _sev_icon(s):
                return {"REQUIRED": "🔴", "WARNING": "🟡", "INFO": "🔵"}.get(s, "⚪") + " " + s

            rules_df["Severity"] = rules_df["Severity"].apply(_sev_icon)
            st.markdown(f"**{len(rules_df)} rules** (of {rules_data.get('total_rules', 0)} total)")
            st.dataframe(rules_df, use_container_width=True, hide_index=True, height=500)


# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    f'<p style="color:#334155;font-size:.75rem;text-align:center;">'
    f'NL Query Engine · FYP 2026 · FastAPI + Streamlit · API: <code>{API_URL}</code></p>',
    unsafe_allow_html=True,
)
