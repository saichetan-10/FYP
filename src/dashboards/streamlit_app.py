import os
import time
from datetime import datetime
from typing import Any, Dict, List

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


def _post(path: str, payload: dict, timeout: int = 45) -> Dict[str, Any]:
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

if "manager"       not in st.session_state: st.session_state.manager       = DashboardManager()
if "query_results" not in st.session_state: st.session_state.query_results = []
if "api_ok"        not in st.session_state: st.session_state.api_ok        = False
if "ex_query"      not in st.session_state: st.session_state.ex_query      = ""
if "inspector_resp" not in st.session_state: st.session_state.inspector_resp = None


# ── Sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🔍 NL Query Engine")
    st.markdown('<p style="color:#475569;font-size:.82rem;margin-top:-8px;">Natural Language Retrieval System · FYP 2026</p>', unsafe_allow_html=True)
    st.divider()

    health = _get("/health")
    if health.get("status") == "healthy":
        st.session_state.api_ok = True
        st.markdown('<span class="badge-green">● API Online</span>', unsafe_allow_html=True)
        st.caption(f'{len(health.get("databases_available",[]))} databases · {health.get("ontology_entities",0)} ontology entities')
    else:
        st.session_state.api_ok = False
        st.markdown('<span class="badge-red">● API Offline</span>', unsafe_allow_html=True)
        st.caption("Run: `venv/bin/python3 main.py api`")

    st.divider()
    st.markdown('<p style="color:#475569;font-size:.75rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;">Databases</p>', unsafe_allow_html=True)
    dbs = health.get("databases_available", ALL_DBS)
    for db in dbs:
        icons = {"sales": "💰", "inventory": "📦", "analytics": "📊", "hr": "👥", "finance": "🏦"}
        st.markdown(f'{icons.get(db,"🗄️")} **{db.title()}**', unsafe_allow_html=True)

    st.divider()
    st.markdown('<p style="color:#475569;font-size:.75rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;">Agent Pipeline</p>', unsafe_allow_html=True)
    for key, meta in AGENT_META.items():
        st.markdown(f'{meta["icon"]} {meta["label"]}', unsafe_allow_html=True)

    st.divider()
    st.caption("v2.0 · FastAPI + Streamlit + SQLite/PostgreSQL")


# ── Header ────────────────────────────────────────────────────────────────────

st.markdown("# 🔍 Natural Language Query Engine")
st.markdown('<p style="color:#94a3b8;margin-top:-12px;">Ask plain-English questions across 5 databases — agents handle SQL, constraints, and confidence scoring.</p>', unsafe_allow_html=True)

(tab_query, tab_analytics, tab_inspector,
 tab_provenance, tab_monitor) = st.tabs([
    "  📊 Query  ",
    "  📈 Analytics  ",
    "  🤖 Agent Inspector  ",
    "  🔎 Provenance  ",
    "  📡 Live Monitor  ",
])


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
    if submitted and query_text.strip():
        run_q = query_text.strip()
    elif st.session_state.ex_query:
        run_q = st.session_state.ex_query
        st.session_state.ex_query = ""

    if run_q:
        if not st.session_state.api_ok:
            st.error("API offline. Start with: `venv/bin/python3 main.py api`")
        else:
            with st.spinner(f'Running "{run_q[:60]}" …'):
                resp = _post("/query", {"query": run_q, "database": db_choice,
                                        "max_iterations": int(iter_choice)})

            if "error" in resp:
                st.error(f"Query failed: {resp['error']}")
            else:
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

                st.divider()
                k1, k2, k3, k4 = st.columns(4)
                k1.metric("Rows Returned",   resp.get("result_count", 0))
                k2.metric("Exec Time (ms)",  f"{resp.get('execution_time_ms', 0):.1f}")
                k3.metric("Semantic Drift",  f"{drift:.4f}")
                k4.metric("Status",          resp.get("status", "—").title())

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
# TAB 3 — AGENT INSPECTOR
# ══════════════════════════════════════════════════════════════════════════════

with tab_inspector:
    st.markdown("### Agent Inspector")
    st.markdown('<p style="color:#64748b;font-size:.88rem;">Watch each agent in the pipeline process your query step-by-step. See exactly what each agent extracted, mapped, validated, planned, and verified.</p>', unsafe_allow_html=True)

    with st.form("inspector_form"):
        ic1, ic2 = st.columns([5, 1.5])
        with ic1:
            insp_query = st.text_input("Query to inspect", value="Show total revenue by region for last year",
                                       label_visibility="collapsed")
        with ic2:
            insp_db = st.selectbox("Database", ALL_DBS, label_visibility="collapsed")
        insp_submitted = st.form_submit_button("🔬  Inspect Pipeline", use_container_width=False)

    if insp_submitted:
        if not st.session_state.api_ok:
            st.error("API offline.")
        else:
            with st.spinner("Running pipeline…"):
                resp = _post("/query", {"query": insp_query, "database": insp_db, "max_iterations": 5})
            if "error" in resp:
                st.error(resp["error"])
            else:
                st.session_state.inspector_resp = resp

    resp = st.session_state.inspector_resp
    if resp and "error" not in resp:
        import pandas as pd

        st.divider()

        # ── Pipeline overview ──────────────────────────────────────────────────
        st.markdown("#### Pipeline Overview")
        drift = resp.get("confidence", {}).get("composite_drift", 0)
        ov1, ov2, ov3, ov4 = st.columns(4)
        ov1.metric("Final Drift",       f"{drift:.4f}")
        ov2.metric("Result Rows",       resp.get("result_count", 0))
        ov3.metric("Status",            resp.get("status","").title())
        ov4.metric("Exec Time (ms)",    f"{resp.get('execution_time_ms',0):.1f}")

        # Visual pipeline bar
        st.markdown("#### Agent Execution Flow")
        trace = resp.get("agent_trace", [])
        agent_order = ["intent_parser", "ontology_mapper", "constraint_validator",
                       "execution_planner", "result_verifier"]

        # Map trace steps to agents
        trace_by_agent: Dict[str, list] = {a: [] for a in agent_order}
        for step in trace:
            agent_key = step.get("agent", "")
            if agent_key in trace_by_agent:
                trace_by_agent[agent_key].append(step)

        cols = st.columns(len(agent_order))
        for i, agent_key in enumerate(agent_order):
            meta = AGENT_META[agent_key]
            steps = trace_by_agent[agent_key]
            has_data = bool(steps)
            badge_cls = "badge-green" if has_data else "badge-red"
            status_txt = "✓ Ran" if has_data else "✗ Skipped"
            cols[i].markdown(
                f'<div style="text-align:center;background:#1e293b;border:1px solid #334155;border-radius:8px;padding:10px 4px;">'
                f'<div style="font-size:1.5rem;">{meta["icon"]}</div>'
                f'<div style="font-size:.78rem;font-weight:700;color:#f1f5f9;margin:4px 0;">{meta["label"]}</div>'
                f'<span class="{badge_cls}">{status_txt}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        st.markdown("")

        # ── Per-agent detail cards ─────────────────────────────────────────────
        st.markdown("#### Per-Agent Details")

        for agent_key in agent_order:
            meta = AGENT_META[agent_key]
            steps = trace_by_agent[agent_key]

            with st.expander(f'{meta["icon"]}  {meta["label"]}', expanded=(agent_key == "intent_parser")):
                st.markdown(f'<p style="color:#94a3b8;font-size:.85rem;">{meta["desc"]}</p>', unsafe_allow_html=True)

                if not steps:
                    st.warning("This agent did not run (no ontology mappings available for downstream agents).")
                    continue

                for step in steps:
                    details = step.get("details", {})
                    st.markdown(f'**Action:** `{step.get("action","")}`')

                    if agent_key == "intent_parser":
                        c1, c2 = st.columns(2)
                        with c1:
                            entities = details.get("entities", [])
                            st.markdown("**Extracted Entities**")
                            if entities:
                                for e in entities:
                                    st.markdown(f'<span class="badge-blue">{e}</span>&nbsp;', unsafe_allow_html=True)
                            else:
                                st.caption("None detected")
                            metrics = details.get("metrics", [])
                            st.markdown("**Extracted Metrics**")
                            if metrics:
                                for m in metrics:
                                    st.markdown(f'<span class="badge-purple">{m}</span>&nbsp;', unsafe_allow_html=True)
                            else:
                                st.caption("None detected")
                        with c2:
                            filters = details.get("filters", {})
                            st.markdown("**Detected Filters**")
                            if filters:
                                for k, v in filters.items():
                                    st.markdown(f"- `{k}` → **{v}**")
                            else:
                                st.caption("No filters")
                            confs = details.get("confidence_scores", {})
                            if confs:
                                st.markdown("**Confidence Scores**")
                                cdf = pd.DataFrame(list(confs.items()), columns=["Metric", "Score"])
                                st.dataframe(cdf, use_container_width=True, hide_index=True)

                    elif agent_key == "ontology_mapper":
                        paths = details.get("ontology_paths", [])
                        st.markdown(f"**Mapped {details.get('mappings_count',0)} terms to ontology**")
                        for p in paths:
                            st.markdown(f'<span class="badge-purple">→ {p}</span>&nbsp;', unsafe_allow_html=True)

                    elif agent_key == "constraint_validator":
                        total = details.get("total_constraints", 0)
                        satisfied = details.get("satisfied", 0)
                        all_ok = details.get("all_satisfied", True)
                        st.markdown(f"**{satisfied} / {total} constraints satisfied** — {'✅ All clear' if all_ok else '⚠️ Violations found'}")

                    elif agent_key == "execution_planner":
                        sql = details.get("sql_template", "")
                        if sql:
                            st.markdown("**Generated SQL**")
                            st.code(sql, language="sql")
                        st.caption(f"Dialect: {details.get('dialect','sqlite')}  ·  Est. rows: {details.get('estimated_rows','?')}")

                    elif agent_key == "result_verifier":
                        st.markdown(f"**{details.get('result_count',0)} rows verified** from `{details.get('source','?')}`")
                        cols_list = details.get("columns", [])
                        if cols_list:
                            st.markdown("Columns: " + " · ".join(f"`{c}`" for c in cols_list))

        # ── Drift evolution ────────────────────────────────────────────────────
        st.markdown("#### Drift Score Breakdown")
        conf = resp.get("confidence", {})
        comp_df = pd.DataFrame({
            "Component": ["Intent Alignment", "Constraint Adherence", "Result Plausibility", "Composite Drift"],
            "Score":     [conf.get("intent_alignment", 0), conf.get("constraint_adherence", 0),
                          conf.get("result_plausibility", 0), conf.get("composite_drift", 0)],
        }).set_index("Component")
        st.bar_chart(comp_df, color="#3b82f6", height=250)

        # ── Final SQL + results ────────────────────────────────────────────────
        sql = resp.get("final_query", "")
        if sql:
            with st.expander("Final Executed SQL"):
                st.code(sql, language="sql")

        results = resp.get("results", [])
        if results:
            with st.expander(f"Result rows ({len(results)})"):
                st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

        with st.expander("Full explanation"):
            st.write(resp.get("explanation", "—"))
    else:
        st.info("Enter a query above and click **Inspect Pipeline** to see each agent's work.")


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

    if auto:
        time.sleep(5)
        st.rerun()


# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    f'<p style="color:#334155;font-size:.75rem;text-align:center;">'
    f'NL Query Engine · FYP 2026 · FastAPI + Streamlit · API: <code>{API_URL}</code></p>',
    unsafe_allow_html=True,
)
