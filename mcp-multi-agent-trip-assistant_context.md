# Context for Project: mcp-multi-agent-trip-assistant

## File: `.env.example`

```example
# Multi-Agent Trip Planning Assistant — Environment Variables
# Copy this file to `.env` and fill in your keys. `.env` is gitignored.
# Only the variables below are read by the application (see config/settings.py).

# --- Required API keys ---

# Google Gemini — intent analysis, destination generation, final composition
# https://aistudio.google.com/apikey
GEMINI_API_KEY=

# Geoapify — geocoding + places/accommodation lookup (all services)
# https://myprojects.geoapify.com
GEOAPIFY_API_KEY=

# OpenRouteService — driving distance/duration (transport service)
# https://openrouteservice.org/dev/#/signup
OPENROUTESERVICE_API_KEY=

# --- App configuration ---
DEBUG=false

# --- Optional overrides (defaults shown; uncomment to change) ---
# GEMINI_MODEL=gemini-flash-lite-latest
# SSL_VERIFY=true
# VERIFY_SSL=true
# GEOAPIFY_VERIFY_SSL=true
# REQUEST_TIMEOUT=30
# MCP_TIMEOUT=30
# PLACES_MCP_URL=http://127.0.0.1:8001/mcp
# CLIMATE_MCP_URL=http://127.0.0.1:8002/mcp
# TRANSPORT_MCP_URL=http://127.0.0.1:8003/mcp
# HOTEL_MCP_URL=http://127.0.0.1:8004/mcp

```

---

## File: `.gitignore`

```
.env
*__pycache__/
```

---

## File: `app_mcp.py`

```py
import streamlit as st

from orchestrator.trip_orchestrator import TripOrchestrator
from memory.redis_trip_memory import RedisTripMemory


st.set_page_config(
    page_title="MCP Trip Planner",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def inject_styles():
    st.markdown(
        """
        <style>
        html, body, [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at top left, rgba(56, 189, 248, 0.14), transparent 32%),
                radial-gradient(circle at top right, rgba(99, 102, 241, 0.14), transparent 30%),
                linear-gradient(135deg, #020617 0%, #07111f 45%, #0f172a 100%) !important;
            color: #f8fafc !important;
        }

        [data-testid="stSidebar"] {
            display: none !important;
        }

        [data-testid="stHeader"] {
            background: transparent !important;
        }

        [data-testid="stToolbar"],
        [data-testid="stDecoration"],
        .stDeployButton,
        #MainMenu,
        footer {
            visibility: hidden !important;
            display: none !important;
        }

        .block-container {
            max-width: 1220px !important;
            padding-top: 1.4rem !important;
            padding-bottom: 2.4rem !important;
        }

        h1, h2, h3, h4, h5, h6 {
            color: #f8fafc !important;
            letter-spacing: -0.02em;
        }

        p, li, span, label {
            color: #dbeafe !important;
        }

        small {
            color: #94a3b8 !important;
        }

        div[data-testid="stMetric"] {
            background: rgba(2, 6, 23, 0.34);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 18px;
            padding: 16px 18px;
            box-shadow: 0 14px 36px rgba(2, 6, 23, 0.24);
        }

        div[data-testid="stMetric"] label {
            color: #94a3b8 !important;
            font-size: 0.78rem !important;
            font-weight: 800 !important;
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }

        div[data-testid="stMetricValue"] {
            color: #f8fafc !important;
            font-weight: 850 !important;
        }

        div[data-testid="stTabs"] {
            border: 1px solid rgba(148, 163, 184, 0.16);
            background: rgba(2, 6, 23, 0.35);
            border-radius: 24px;
            padding: 10px;
        }

        div[data-testid="stTabs"] button {
            color: #cbd5e1 !important;
            font-weight: 800 !important;
            border-radius: 14px !important;
            padding: 10px 16px !important;
        }

        div[data-testid="stTabs"] button[aria-selected="true"] {
            background: linear-gradient(135deg, rgba(14, 165, 233, 0.30), rgba(99, 102, 241, 0.22)) !important;
            color: #ffffff !important;
            border: 1px solid rgba(125, 211, 252, 0.24) !important;
        }

        div[data-testid="stChatMessage"] {
            background: rgba(2, 6, 23, 0.36);
            border: 1px solid rgba(148, 163, 184, 0.14);
            border-radius: 20px;
            padding: 14px 16px;
            margin-bottom: 12px;
        }

        div[data-testid="stChatMessage"] p,
        div[data-testid="stChatMessage"] li {
            color: #e5e7eb !important;
            line-height: 1.62;
        }

        div[data-testid="stChatMessage"] h1,
        div[data-testid="stChatMessage"] h2,
        div[data-testid="stChatMessage"] h3,
        div[data-testid="stChatMessage"] strong {
            color: #ffffff !important;
        }

        textarea {
            background: rgba(15, 23, 42, 0.96) !important;
            color: #f8fafc !important;
            border: 1px solid rgba(148, 163, 184, 0.30) !important;
            border-radius: 18px !important;
        }

        textarea::placeholder {
            color: #64748b !important;
        }

        .stButton > button {
            border-radius: 14px !important;
            border: 1px solid rgba(56, 189, 248, 0.34) !important;
            background: linear-gradient(135deg, rgba(14, 165, 233, 0.96), rgba(37, 99, 235, 0.96)) !important;
            color: #ffffff !important;
            font-weight: 850 !important;
        }

        details {
            border: 1px solid rgba(148, 163, 184, 0.14) !important;
            background: rgba(2, 6, 23, 0.28) !important;
            border-radius: 16px !important;
            margin-bottom: 10px !important;
        }

        details summary {
            color: #e2e8f0 !important;
            font-weight: 850 !important;
        }

        pre {
            background: rgba(2, 6, 23, 0.84) !important;
            border: 1px solid rgba(148, 163, 184, 0.16) !important;
            border-radius: 16px !important;
        }

        code {
            color: #dbeafe !important;
        }

        div[data-testid="stAlert"] {
            background: rgba(15, 23, 42, 0.74) !important;
            color: #e2e8f0 !important;
            border-radius: 16px !important;
            border: 1px solid rgba(148, 163, 184, 0.16) !important;
        }

        div[data-testid="stForm"] {
            border: 1px solid rgba(251, 191, 36, 0.24);
            background: rgba(120, 53, 15, 0.16);
            border-radius: 20px;
            padding: 18px;
        }

        input,
        div[data-baseweb="select"] > div {
            background: rgba(15, 23, 42, 0.92) !important;
            color: #f8fafc !important;
            border-color: rgba(148, 163, 184, 0.24) !important;
        }

        hr {
            border-color: rgba(148, 163, 184, 0.16) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def init_state():
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = TripOrchestrator()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "last_result" not in st.session_state:
        st.session_state.last_result = None

    if "memory_store" not in st.session_state:
        st.session_state.memory_store = RedisTripMemory()

    if "memory_session_id" not in st.session_state:
        st.session_state.memory_session_id = st.session_state.memory_store.create_session_id()


def reset_app():
    if "memory_store" in st.session_state and "memory_session_id" in st.session_state:
        st.session_state.memory_store.clear(st.session_state.memory_session_id)

    st.session_state.messages = []
    st.session_state.last_result = None
    st.session_state.orchestrator = TripOrchestrator()
    st.session_state.memory_session_id = st.session_state.memory_store.create_session_id()
    st.rerun()


def _clarification_summary_text(clarification: dict) -> str:
    reason = clarification.get("reason") or "I need a bit more information to continue."
    questions = clarification.get("questions") or []

    lines = [reason]

    for question in questions:
        question_text = question.get("question")
        if question_text:
            lines.append(f"- {question_text}")

    return "\n".join(lines)


def _record_result(user_facing_content: str, result: dict):
    st.session_state.last_result = result
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": user_facing_content,
            "result": result,
        }
    )


def run_query(user_query: str):
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_query,
        }
    )

    with st.spinner("Planning with MCP tools and specialist agents..."):
        result = st.session_state.orchestrator.run(
            user_query=user_query,
            debug=False,
            session_id=st.session_state.memory_session_id,
        )

    if result.get("awaiting_clarification"):
        content = _clarification_summary_text(result.get("clarification") or {})
    else:
        content = (
            result.get("response")
            or result.get("error")
            or "I could not generate a final response."
        )

    _record_result(content, result)


def run_answer(answers: dict):
    with st.spinner("Continuing the planning workflow..."):
        result = st.session_state.orchestrator.run(
            answer=answers,
            debug=False,
            session_id=st.session_state.memory_session_id,
        )

    if result.get("awaiting_clarification"):
        content = _clarification_summary_text(result.get("clarification") or {})
    else:
        content = (
            result.get("response")
            or result.get("error")
            or "I could not generate a final response."
        )

    _record_result(content, result)


def _safe_len(value) -> int:
    return len(value or [])


def _short_list(value, max_chars: int = 42) -> str:
    items = value or []

    if not items:
        return "-"

    text = ", ".join(str(item) for item in items)

    if len(text) > max_chars:
        return text[: max_chars - 3] + "..."

    return text


def _get_status_text(last_result: dict) -> str:
    if not last_result:
        return "Ready"

    if last_result.get("awaiting_clarification"):
        return "Needs Input"

    if last_result.get("success"):
        return "Completed"

    return "Attention"


def _compact_value(value, max_len: int = 95) -> str:
    if value is None:
        return "-"

    if isinstance(value, (list, tuple)):
        if not value:
            return "-"

        text = ", ".join(str(item) for item in value[:5])

        if len(value) > 5:
            text += f" +{len(value) - 5} more"

        return text[:max_len] + "..." if len(text) > max_len else text

    if isinstance(value, dict):
        keys = list(value.keys())

        if not keys:
            return "-"

        text = ", ".join(keys[:6])

        if len(keys) > 6:
            text += f" +{len(keys) - 6} more"

        return text[:max_len] + "..." if len(text) > max_len else text

    text = str(value)
    return text[:max_len] + "..." if len(text) > max_len else text



def render_header():
    last_result = st.session_state.last_result or {}
    workflow = last_result.get("workflow") or {}
    summary = last_result.get("summary") or {}

    status = _get_status_text(last_result)
    completed_count = _safe_len(workflow.get("completed_agents"))
    failed_count = _safe_len(workflow.get("failed_agents"))
    replan_count = workflow.get("replan_count", 0)
    selected_cities = summary.get("selected_cities") or []

    st.caption("🧭 MCP TRAVEL INTELLIGENCE")
    st.title("Dynamic Multi-Agent Trip Planner")
    st.write(
        "A planner-led travel assistant powered by MCP tools, specialist agents, "
        "route intelligence, climate checks, lodging signals, budget feasibility "
        "and adaptive replanning."
    )

    metric_cols = st.columns(5)

    with metric_cols[0]:
        st.metric("Status", status)

    with metric_cols[1]:
        st.metric(
            "Completed",
            completed_count,
            help="Actual agents completed",
        )

    with metric_cols[2]:
        st.metric(
            "Failed",
            failed_count,
            help="Failed agents captured safely",
        )

    with metric_cols[3]:
        st.metric(
            "Replans",
            replan_count,
            help="Automatic replanning attempts",
        )

    with metric_cols[4]:
        st.metric(
            "Cities",
            _safe_len(selected_cities),
            help=_short_list(selected_cities),
        )

    st.divider()



def render_action_row():
    col1, col2 = st.columns([0.82, 0.18])

    with col1:
        st.caption(
            "Try: Plan a 4-day Odisha trip from West Bengal for 5 people in May with temples and beaches."
        )

    with col2:
        if st.button("Clear Chat", use_container_width=True):
            reset_app()


def _render_question_input(question: dict):
    kind = question.get("kind", "free_text")
    options = question.get("options") or []
    widget_key = f"clarify_{question.get('id')}_{len(st.session_state.messages)}"
    label = question.get("question") or "Please provide more detail"

    if kind == "single_select" and options:
        labels = [option.get("label") for option in options]
        ids = [option.get("id") for option in options]

        choice = st.radio(
            label,
            labels,
            key=widget_key,
            horizontal=True,
        )

        return ids[labels.index(choice)] if choice in labels else None

    if kind == "multi_select" and options:
        labels = [option.get("label") for option in options]
        ids = [option.get("id") for option in options]

        chosen = st.multiselect(
            label,
            labels,
            key=widget_key,
            placeholder="Select one or more options",
        )

        return [ids[labels.index(item)] for item in chosen]

    return st.text_input(label, key=widget_key)


def render_pending_clarification():
    last_result = st.session_state.last_result

    if not last_result or not last_result.get("awaiting_clarification"):
        return

    clarification = last_result.get("clarification") or {}
    questions = clarification.get("questions") or []

    if not questions:
        return

    st.warning(clarification.get("reason", "A quick question before continuing."))

    with st.form(key=f"clarification_form_{len(st.session_state.messages)}"):
        answers = {}

        for question in questions:
            question_id = question.get("id")
            answers[question_id] = _render_question_input(question)

        submitted = st.form_submit_button(
            "Continue Planning",
            use_container_width=True,
        )

    if submitted:
        run_answer(answers)
        st.rerun()


def _agent_status_label(result: dict) -> str:
    return "Success" if result.get("success") else "Failed"


def _agent_status_icon(result: dict) -> str:
    return "✅" if result.get("success") else "⚠️"


def _summarize_agent_result(agent_name: str, result: dict) -> dict:
    data = result.get("data") or {}

    summary = {
        "Agent": agent_name,
        "Status": _agent_status_label(result),
        "Message": result.get("message") or "-",
        "Error": result.get("error") or "-",
        "Mode": "-",
        "Output": "-",
        "Cities": "-",
    }

    if agent_name == "destination_agent":
        mode = data.get("mode")
        summary["Mode"] = mode or "-"

        if mode == "destination_recommendation":
            recommended = data.get("recommended_destinations") or {}
            recommendations = recommended.get("recommendations") or []
            summary["Output"] = f"{len(recommendations)} destination recommendation(s)"
        elif mode == "city_recommendation":
            recommendations = data.get("city_recommendations") or []
            summary["Output"] = f"{len(recommendations)} city recommendation(s)"
        elif mode == "scope_resolved":
            summary["Output"] = _compact_value(data.get("resolved_cities"))
        elif mode == "city_attractions":
            places = data.get("ranked_places") or data.get("places") or []
            summary["Output"] = f"{len(places)} ranked place(s)"
        else:
            summary["Output"] = _compact_value(data)

    elif agent_name == "climate_agent":
        by_city = data.get("by_city") or {}
        if by_city:
            summary["Output"] = f"Climate data for {len(by_city)} city/cities"
            summary["Cities"] = _compact_value(list(by_city.keys()))
        else:
            summary["Output"] = _compact_value(data)

    elif agent_name == "hotel_agent":
        by_city = data.get("by_city") or {}
        if by_city:
            summary["Output"] = f"Hotel/stay data for {len(by_city)} city/cities"
            summary["Cities"] = _compact_value(list(by_city.keys()))
        else:
            summary["Output"] = _compact_value(data)

    elif agent_name == "transport_agent":
        display_sequence = data.get("display_sequence") or []
        ordered_cities = data.get("ordered_cities") or []
        summary["Output"] = f"{len(display_sequence)} sequence step(s)"
        summary["Cities"] = _compact_value(ordered_cities)

    elif agent_name == "itinerary_agent":
        city_plans = data.get("city_plans") or []
        total_days = data.get("total_days")
        summary["Output"] = f"{total_days or '-'} day(s), {len(city_plans)} city plan(s)"
        summary["Cities"] = _compact_value(
            [plan.get("city") for plan in city_plans if plan.get("city")]
        )

    elif agent_name == "budget_agent":
        feasible = data.get("feasible")
        estimated_cost = data.get("estimated_cost_inr")
        summary["Output"] = f"Feasible: {feasible}, Estimated: INR {estimated_cost}"

    else:
        summary["Output"] = _compact_value(data)

    return summary


def _render_agent_summary(selected_agent: str, selected_result: dict):
    summary = _summarize_agent_result(selected_agent, selected_result)
    icon = _agent_status_icon(selected_result)

    if selected_result.get("success"):
        st.success(f"{icon} **{selected_agent}** completed successfully")
    else:
        st.error(f"{icon} **{selected_agent}** failed")

    c1, c2, c3 = st.columns([0.25, 0.35, 0.40])

    with c1:
        st.write("**Status**")
        st.write(summary.get("Status"))

        st.write("**Mode**")
        st.write(summary.get("Mode") or "-")

    with c2:
        st.write("**Output**")
        st.write(summary.get("Output") or "-")

        st.write("**Cities**")
        st.write(summary.get("Cities") or "-")

    with c3:
        st.write("**Message**")
        st.write(summary.get("Message") or "-")

        if summary.get("Error") and summary.get("Error") != "-":
            st.write("**Error**")
            st.warning(summary.get("Error"))


def render_assistant_tab():
    st.subheader("Assistant")
    st.caption("Clean user-facing conversation. Internal workflow logs and raw tool outputs stay separate.")

    if not st.session_state.messages:
        st.info(
            "Start with a natural trip request. The assistant will resolve destinations, "
            "fetch climate details, sequence transport, evaluate feasibility and generate a polished itinerary."
        )
    else:
        for message in st.session_state.messages:
            role = message.get("role")
            content = message.get("content")

            with st.chat_message(role):
                st.markdown(content)

    render_pending_clarification()


def render_workflow_tab():
    st.subheader("Workflow")
    st.caption("High-level orchestration summary for evaluation and debugging.")

    last_result = st.session_state.last_result or {}

    if not last_result:
        st.info("Workflow summary will appear after you submit a request.")
        return

    request = last_result.get("request") or {}
    workflow = last_result.get("workflow") or {}
    summary = last_result.get("summary") or {}

    completed_agents = workflow.get("completed_agents") or []
    failed_agents = workflow.get("failed_agents") or []
    selected_cities = summary.get("selected_cities") or []
    feasible = summary.get("feasible")

    feasible_text = "Yes" if feasible is True else "No" if feasible is False else "Unknown"

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Completed Agents", len(completed_agents))

    with c2:
        st.metric("Failed Agents", len(failed_agents))

    with c3:
        st.metric("Selected Cities", len(selected_cities), help=_short_list(selected_cities))

    with c4:
        st.metric("Feasible", feasible_text)

    with st.expander("Request Summary", expanded=True):
        req_col1, req_col2, req_col3 = st.columns(3)

        with req_col1:
            st.write("**Source**")
            st.write(request.get("source") or "-")
            st.write("**Destination**")
            st.write(request.get("destination") or "-")

        with req_col2:
            st.write("**Month**")
            st.write(request.get("month") or "-")
            st.write("**Days**")
            st.write(request.get("days") or "-")

        with req_col3:
            st.write("**Budget**")
            st.write(request.get("budget") or "-")
            st.write("**Travelers**")
            st.write(request.get("travelers") or "-")

        st.write("**Interests**")
        st.write(", ".join(request.get("interests") or []) or "-")

    with st.expander("Agent Execution", expanded=True):
        st.write("**Planned agents**")
        st.write(workflow.get("planned_agents") or [])

        st.write("**Completed agents**")
        st.write(completed_agents)

        if failed_agents:
            st.write("**Failed agents**")
            st.json(failed_agents)
        else:
            st.success("No failed agents in this run.")

    with st.expander("Replanning", expanded=bool(workflow.get("replan_directives"))):
        st.write("**Replan count**")
        st.write(workflow.get("replan_count", 0))

        st.write("**Directives**")
        st.write(workflow.get("replan_directives") or [])

    with st.expander("Travel Sequence", expanded=True):
        st.json(summary.get("travel_sequence"))

    if summary.get("errors"):
        with st.expander("Captured Errors", expanded=True):
            st.json(summary.get("errors"))


def render_data_tab():
    st.subheader("Data")
    st.caption(
        "Structured agent outputs are summarized first. Expand raw payloads only when debugging is needed."
    )

    last_result = st.session_state.last_result or {}

    if not last_result:
        st.info("Agent data will appear after a plan is generated.")
        return

    agent_results = last_result.get("agent_results") or {}

    if not agent_results:
        st.info("No agent outputs are available for this turn.")
        return

    overview_rows = []

    for agent_name, result in agent_results.items():
        summary = _summarize_agent_result(agent_name, result)
        overview_rows.append(
            {
                "Agent": summary.get("Agent"),
                "Status": summary.get("Status"),
                "Output": summary.get("Output"),
                "Cities": summary.get("Cities"),
            }
        )

    st.markdown("### Agent Output Overview")
    st.dataframe(
        overview_rows,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    st.markdown("### Inspect Agent Output")

    agent_names = list(agent_results.keys())

    selected_agent = st.selectbox(
        "Choose an agent to inspect",
        agent_names,
        index=0,
    )

    selected_result = agent_results.get(selected_agent) or {}

    _render_agent_summary(selected_agent, selected_result)

    with st.expander("Structured Data", expanded=True):
        st.json(selected_result.get("data") or {})

    with st.expander("Full Raw Agent Payload", expanded=False):
        st.json(selected_result)

    st.divider()

    st.markdown("### Raw Run Payloads")

    payload_col1, payload_col2, payload_col3 = st.columns(3)

    with payload_col1:
        with st.expander("Request", expanded=False):
            st.json(last_result.get("request", {}))

    with payload_col2:
        with st.expander("Workflow", expanded=False):
            st.json(last_result.get("workflow", {}))

    with payload_col3:
        with st.expander("Summary", expanded=False):
            st.json(last_result.get("summary", {}))

    if last_result.get("debug_state"):
        with st.expander("Debug State", expanded=False):
            st.json(last_result.get("debug_state"))


def main():
    inject_styles()
    init_state()

    render_header()
    render_action_row()

    assistant_tab, workflow_tab, data_tab = st.tabs(
        [
            "Assistant",
            "Workflow",
            "Data",
        ]
    )

    with assistant_tab:
        render_assistant_tab()

    with workflow_tab:
        render_workflow_tab()

    with data_tab:
        render_data_tab()

    awaiting_clarification = bool(
        st.session_state.last_result
        and st.session_state.last_result.get("awaiting_clarification")
    )

    placeholder = (
        "Answer the clarification here, or use the form above..."
        if awaiting_clarification
        else "Ask for a trip plan..."
    )

    user_query = st.chat_input(placeholder)

    if user_query:
        run_query(user_query)
        st.rerun()


if __name__ == "__main__":
    main()
```

---

## File: `requirements.txt`

```txt
# Web UI
streamlit>=1.56

# Orchestration graph — planner-led routing, interrupt/resume for clarification
langgraph>=1.1

# MCP protocol (servers + streamable-http clients)
mcp>=1.26

# LLM used for intent analysis, destination generation and final composition
google-generativeai>=0.8

# NLP entity extraction in the intent analyzer
spacy>=3.8
# Also run once after install:  python -m spacy download en_core_web_sm

# HTTP calls to Geoapify / Open-Meteo / OpenRouteService in the services layer
requests>=2.32

# Loads API keys from .env
python-dotenv>=1.0

```

---

## File: `start_mcp_servers.py`

```py
import subprocess
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent

SERVERS = [
    {
        "name": "Places MCP Server",
        "module": "mcp_servers.places_mcp_server",
        "port": 8001,
    },
    {
        "name": "Climate MCP Server",
        "module": "mcp_servers.climate_mcp_server",
        "port": 8002,
    },
    {
        "name": "Transport MCP Server",
        "module": "mcp_servers.transport_mcp_server",
        "port": 8003,
    },
    {
        "name": "Hotel MCP Server",
        "module": "mcp_servers.hotel_mcp_server",
        "port": 8004,
    },
]


def start_servers():
    processes = []

    print("Starting MCP servers...\n")

    for server in SERVERS:
        print(f"Starting {server['name']} on port {server['port']}...")

        process = subprocess.Popen(
            [sys.executable, "-m", server["module"]],
            cwd=PROJECT_ROOT,
        )

        processes.append(
            {
                "name": server["name"],
                "port": server["port"],
                "process": process,
            }
        )

        time.sleep(1)

    print("\nAll MCP servers started.")
    print("Press CTRL + C to stop all servers.\n")

    try:
        while True:
            time.sleep(2)

            for item in processes:
                process = item["process"]

                if process.poll() is not None:
                    print(f"{item['name']} stopped unexpectedly on port {item['port']}.")

    except KeyboardInterrupt:
        print("\nStopping MCP servers...")

        for item in processes:
            process = item["process"]

            if process.poll() is None:
                print(f"Stopping {item['name']}...")
                process.terminate()

        time.sleep(2)

        for item in processes:
            process = item["process"]

            if process.poll() is None:
                process.kill()

        print("All MCP servers stopped.")


if __name__ == "__main__":
    start_servers()
```

---

## File: `test_redis_connection.py`

```py
from memory.redis_trip_memory import RedisTripMemory

store = RedisTripMemory()

session_id = store.create_session_id()

memory = store.default_memory()
memory["request_memory"]["source"] = "West Bengal"
memory["request_memory"]["destination"] = "Odisha"
memory["request_memory"]["days"] = 4
memory["request_memory"]["travelers"] = 5

store.save(session_id, memory)

loaded = store.load(session_id)

print("SESSION:", session_id)
print("LOADED REQUEST MEMORY:", loaded["request_memory"])
```

---

## File: `agents_mcp/base_agent.py`

```py
from abc import ABC, abstractmethod
from schemas.agent_schema import AgentInput, AgentOutput, AgentMetadata


class BaseAgent(ABC):
    def __init__(self, metadata: AgentMetadata):
        self.metadata = metadata
        self.name = metadata.name

    @abstractmethod
    def run(self, agent_input: AgentInput) -> AgentOutput:
        pass

    def success_response(self, data: dict, message: str = None) -> AgentOutput:
        return AgentOutput(
            agent_name=self.name,
            success=True,
            data=data,
            message=message
        )

    def error_response(self, error: str, data: dict = None) -> AgentOutput:
        return AgentOutput(
            agent_name=self.name,
            success=False,
            data=data or {},
            error=error
        )
```

---

## File: `agents_mcp/budget_agent.py`

```py
import math
from typing import Any, Dict, List

from config.constants import AGENT_BUDGET
from schemas.agent_schema import AgentInput, AgentOutput, AgentMetadata
from agents_mcp.base_agent import BaseAgent


class BudgetAgent(BaseAgent):
    """Evaluates whether the requested trip is feasible — it does not build
    the plan itself.

    Feasibility has two independent checks:
      1. Time: does the requested number of days cover the selected cities
         plus the inter-city travel it takes to visit them?
      2. Cost: what would the trip roughly cost at the requested budget band,
         for context (not a hard pass/fail signal on its own).

    ``Replanning`` (a separate node) decides what to do when this agent
    reports ``feasible: False`` — this agent only judges, it never mutates
    the plan.
    """

    PER_DAY_ESTIMATES = {
        "low": 2500,
        "medium": 5000,
        "high": 10000,
    }

    MIN_DAYS_PER_CITY = 1.5
    TRAVEL_DAY_DISTANCE_THRESHOLD_KM = 250

    def __init__(self):
        metadata = AgentMetadata(
            name=AGENT_BUDGET,
            description="Evaluates trip feasibility (time and cost) without producing the plan itself.",
            depends_on=[],
            output_key="budget_result",
        )
        super().__init__(metadata)

    def run(self, agent_input: AgentInput) -> AgentOutput:
        available_days = agent_input.days or 3
        travelers = agent_input.travelers or 1
        budget_type = agent_input.budget or "medium"

        selected_cities = agent_input.context.get("selected_cities") or (
            [agent_input.destination] if agent_input.destination else []
        )
        inter_city_legs = agent_input.context.get("inter_city_legs") or []

        num_cities = max(len(selected_cities), 1)
        required_city_days = math.ceil(num_cities * self.MIN_DAYS_PER_CITY)
        travel_days = sum(
            1 for leg in inter_city_legs if self._leg_distance_km(leg) > self.TRAVEL_DAY_DISTANCE_THRESHOLD_KM
        )
        required_days = required_city_days + travel_days

        per_day = self.PER_DAY_ESTIMATES.get(budget_type, 5000)
        estimated_cost = per_day * max(required_days, available_days) * travelers

        feasible = required_days <= available_days

        suggested_adjustments: List[str] = []

        if not feasible:
            shortfall_days = required_days - available_days

            if num_cities > 1:
                suggested_adjustments.append(
                    f"Drop the lowest-priority city to reduce required days by roughly "
                    f"{math.ceil(self.MIN_DAYS_PER_CITY)}."
                )

            suggested_adjustments.append(
                f"Extend the trip by {shortfall_days} day(s) to comfortably cover {num_cities} "
                f"{'city' if num_cities == 1 else 'cities'}."
            )

        return self.success_response(
            data={
                "feasible": feasible,
                "available_days": available_days,
                "required_days": required_days,
                "num_cities": num_cities,
                "travel_days": travel_days,
                "budget_type": budget_type,
                "travelers": travelers,
                "estimated_cost_inr": estimated_cost,
                "breakdown": {
                    "stay": int(estimated_cost * 0.35),
                    "food": int(estimated_cost * 0.20),
                    "local_transport": int(estimated_cost * 0.20),
                    "activities": int(estimated_cost * 0.15),
                    "miscellaneous": int(estimated_cost * 0.10),
                },
                "suggested_adjustments": suggested_adjustments,
                "note": (
                    "This is a heuristic feasibility check, not a live pricing lookup. "
                    "Actual cost may vary by accommodation, transport mode, activity choices, and season."
                ),
            },
            message="Feasibility evaluated successfully." if feasible else "Trip is not feasible as requested.",
        )

    @staticmethod
    def _leg_distance_km(leg: Dict[str, Any]) -> float:
        transport_data = leg.get("transport_data") or {}

        for key in ("distance_km", "distance"):
            value = transport_data.get(key)

            if isinstance(value, (int, float)):
                return float(value)

        return 0.0

```

---

## File: `agents_mcp/climate_agent.py`

```py
from config.constants import AGENT_CLIMATE
from schemas.agent_schema import AgentInput, AgentOutput, AgentMetadata
from agents_mcp.base_agent import BaseAgent
from mcp_clients.climate_mcp_client import ClimateMCPClient


class ClimateAgent(BaseAgent):
    def __init__(self):
        metadata = AgentMetadata(
            name=AGENT_CLIMATE,
            description="Fetches raw structured climate data for a destination.",
            depends_on=[],
            output_key="climate_result",
        )
        super().__init__(metadata)
        self.client = ClimateMCPClient()

    def run(self, agent_input: AgentInput) -> AgentOutput:
        if not agent_input.destination:
            return self.error_response("Destination is required for climate agent.")

        response = self.client.get_climate(
            destination=agent_input.destination,
            month=agent_input.month,
            travel_dates=agent_input.context.get("travel_dates"),
        )

        if not response.success:
            return self.error_response(
                error=response.error or "Failed to fetch climate data.",
                data={
                    "raw_mcp_response": response.raw_response,
                },
            )

        return self.success_response(
            data={
                "destination": agent_input.destination,
                "month": agent_input.month,
                "raw_climate_data": response.data,
                "raw_mcp_response": response.raw_response,
            },
            message="Raw climate data fetched successfully.",
        )
```

---

## File: `agents_mcp/destination_agent.py`

```py
from config.constants import AGENT_DESTINATION, SCOPE_CITY, BROAD_SCOPES, SCOPE_UNKNOWN
from schemas.agent_schema import AgentInput, AgentOutput, AgentMetadata
from agents_mcp.base_agent import BaseAgent
from mcp_clients.places_mcp_client import PlacesMCPClient


class DestinationAgent(BaseAgent):
    """Owns all destination/places business logic: recommending a destination
    when none is given, classifying a given destination's scope (city vs
    state/region/country), recommending cities inside a broad scope, and
    fetching + ranking attractions for one resolved city at a time.

    Attractions are always fetched per city, never for an entire region — the
    ``attractions`` graph node calls ``run`` once per selected city with
    ``agent_input.context["destination_mode"] = "fetch_attractions"``.
    """

    def __init__(self):
        metadata = AgentMetadata(
            name=AGENT_DESTINATION,
            description=(
                "Recommends destinations, classifies destination scope, recommends "
                "cities within a broad region, and fetches/ranks per-city attractions."
            ),
            depends_on=[],
            output_key="destination_result",
        )
        super().__init__(metadata)
        self.client = PlacesMCPClient()

    def run(self, agent_input: AgentInput) -> AgentOutput:
        destination_mode = agent_input.context.get("destination_mode")

        if destination_mode == "fetch_attractions":
            return self._fetch_and_rank_attractions_for_city(agent_input)

        if not agent_input.destination:
            return self._recommend_destinations(agent_input)

        return self._resolve_scope(agent_input)

    def _resolve_scope(self, agent_input: AgentInput) -> AgentOutput:
        classify_response = self.client.classify_destination(agent_input.destination)

        if not classify_response.success:
            return self.error_response(
                error=classify_response.error or "Failed to classify destination.",
                data={
                    "mode": "scope_classification",
                    "destination": agent_input.destination,
                    "raw_mcp_response": classify_response.raw_response,
                },
            )

        scope = classify_response.data.get("scope", SCOPE_UNKNOWN)
        canonical_name = classify_response.data.get("canonical_name") or agent_input.destination

        if scope == SCOPE_UNKNOWN:
            return self.error_response(
                error=(
                    f"Could not determine whether '{agent_input.destination}' is a city "
                    "or a broader state/region/country."
                ),
                data={
                    "mode": "scope_classification",
                    "destination": agent_input.destination,
                    "scope": scope,
                },
            )

        if scope == SCOPE_CITY:
            return self.success_response(
                data={
                    "mode": "scope_resolved",
                    "scope": scope,
                    "destination": agent_input.destination,
                    "resolved_cities": [canonical_name],
                },
                message=f"'{canonical_name}' resolved as a single city.",
            )

        if scope in BROAD_SCOPES:
            return self._recommend_cities_in_region(agent_input, region=canonical_name, scope=scope)

        return self.error_response(
            error=f"Unsupported destination scope '{scope}'.",
            data={"mode": "scope_classification", "destination": agent_input.destination, "scope": scope},
        )

    def _recommend_cities_in_region(self, agent_input: AgentInput, region: str, scope: str) -> AgentOutput:
        response = self.client.recommend_cities_in_region(
            region=region,
            interests=agent_input.interests,
            days=agent_input.days,
            budget=agent_input.budget,
            travelers=agent_input.travelers,
            travel_style=agent_input.context.get("travel_style"),
            limit=6,
        )

        if not response.success:
            return self.error_response(
                error=response.error or f"Failed to recommend cities within '{region}'.",
                data={
                    "mode": "city_recommendation",
                    "scope": scope,
                    "region": region,
                    "raw_mcp_response": response.raw_response,
                },
            )

        return self.success_response(
            data={
                "mode": "city_recommendation",
                "scope": scope,
                "region": region,
                "city_recommendations": response.data.get("recommendations", []),
            },
            message=f"Candidate cities recommended for '{region}'.",
        )

    def _fetch_and_rank_attractions_for_city(self, agent_input: AgentInput) -> AgentOutput:
        city = agent_input.context.get("target_city") or agent_input.destination

        if not city:
            return self.error_response(
                error="A target city is required to fetch attractions.",
                data={"mode": "city_attractions"},
            )

        places_response = self.client.get_popular_places(
            destination=city,
            interests=agent_input.interests,
            limit=10,
        )

        if not places_response.success:
            return self.error_response(
                error=places_response.error or f"Failed to fetch places for '{city}'.",
                data={
                    "mode": "city_attractions",
                    "city": city,
                    "raw_mcp_response": places_response.raw_response,
                },
            )

        places = places_response.data.get("places", [])

        rank_response = self.client.rank_places(
            city=city,
            places=places,
            interests=agent_input.interests,
            days=agent_input.days,
        )

        ranked_places = places

        if rank_response.success:
            ranked_places = rank_response.data.get("ranked_places", places)

        return self.success_response(
            data={
                "mode": "city_attractions",
                "city": city,
                "interests": agent_input.interests,
                "places": places,
                "ranked_places": ranked_places,
            },
            message=f"Attractions fetched and ranked for '{city}'.",
        )

    def _recommend_destinations(self, agent_input: AgentInput) -> AgentOutput:
        response = self.client.recommend_destinations(
            source=agent_input.source,
            interests=agent_input.interests,
            month=agent_input.month,
            budget=agent_input.budget,
            days=agent_input.days,
            travelers=agent_input.travelers,
            limit=8,
        )

        if not response.success:
            return self.error_response(
                error=response.error or "Failed to recommend destinations.",
                data={
                    "mode": "destination_recommendation",
                    "source": agent_input.source,
                    "interests": agent_input.interests,
                    "month": agent_input.month,
                    "budget": agent_input.budget,
                    "days": agent_input.days,
                    "travelers": agent_input.travelers,
                    "raw_mcp_response": response.raw_response,
                },
            )

        return self.success_response(
            data={
                "mode": "destination_recommendation",
                "source": agent_input.source,
                "interests": agent_input.interests,
                "month": agent_input.month,
                "budget": agent_input.budget,
                "days": agent_input.days,
                "travelers": agent_input.travelers,
                "recommended_destinations": response.data,
                "raw_mcp_response": response.raw_response,
            },
            message="Destination recommendations generated successfully.",
        )

```

---

## File: `agents_mcp/hotel_agent.py`

```py
from config.constants import AGENT_HOTEL
from schemas.agent_schema import AgentInput, AgentOutput, AgentMetadata
from agents_mcp.base_agent import BaseAgent
from mcp_clients.hotel_mcp_client import HotelMCPClient


class HotelAgent(BaseAgent):
    def __init__(self):
        metadata = AgentMetadata(
            name=AGENT_HOTEL,
            description="Fetches raw accommodation and stay-area data for a destination.",
            depends_on=[],
            output_key="hotel_result",
        )
        super().__init__(metadata)
        self.client = HotelMCPClient()

    def run(self, agent_input: AgentInput) -> AgentOutput:
        if not agent_input.destination:
            return self.error_response("Destination is required for hotel agent.")

        response = self.client.search_hotels(
            destination=agent_input.destination,
            budget=agent_input.budget,
            travelers=agent_input.travelers,
            limit=10,
        )

        if not response.success:
            return self.error_response(
                error=response.error or "Failed to fetch hotel data.",
                data={
                    "raw_mcp_response": response.raw_response,
                },
            )

        return self.success_response(
            data={
                "destination": agent_input.destination,
                "budget": agent_input.budget,
                "travelers": agent_input.travelers,
                "raw_hotel_data": response.data,
                "raw_mcp_response": response.raw_response,
            },
            message="Raw hotel data fetched successfully.",
        )
```

---

## File: `agents_mcp/itinerary_agent.py`

```py
from typing import Any, Dict, List

from config.constants import AGENT_ITINERARY
from schemas.agent_schema import AgentInput, AgentOutput, AgentMetadata
from agents_mcp.base_agent import BaseAgent


class ItineraryAgent(BaseAgent):
    """Builds a deterministic day-wise itinerary skeleton, grouped by city.

    The skeleton is intentionally content-free: the final response composer
    fills each slot using the raw outputs of the other agents (ranked
    per-city attractions, climate, transport, hotel, budget). This keeps
    itinerary business logic (day allocation across cities) inside an agent
    rather than in the orchestrator, while leaving actual content generation
    to the composer.
    """

    def __init__(self):
        metadata = AgentMetadata(
            name=AGENT_ITINERARY,
            description="Generates a day-wise itinerary skeleton grouped by city.",
            depends_on=[],
            output_key="itinerary_result",
        )
        super().__init__(metadata)

    def run(self, agent_input: AgentInput) -> AgentOutput:
        selected_cities = agent_input.context.get("selected_cities") or (
            [agent_input.destination] if agent_input.destination else []
        )

        if not selected_cities:
            return self.error_response(
                error="At least one resolved city is required to generate an itinerary.",
                data={"missing_fields": ["destination"]},
            )

        total_days = agent_input.days or 3
        city_attractions = agent_input.context.get("city_attractions") or {}

        days_per_city = self._allocate_days(selected_cities, total_days, city_attractions)

        city_plans: List[Dict[str, Any]] = []
        day_counter = 1

        for city in selected_cities:
            days_for_city = days_per_city.get(city, 0)

            day_plans = [
                {
                    "day": day_counter + offset,
                    "city": city,
                    "structure": ["morning_activity", "afternoon_activity", "evening_activity"],
                    "context_required": [
                        "ranked_city_attractions",
                        "climate_data",
                        "transport_data",
                        "hotel_signals",
                        "user_interests",
                    ],
                }
                for offset in range(days_for_city)
            ]

            city_plans.append({
                "city": city,
                "days": days_for_city,
                "day_plans": day_plans,
                "notes": (
                    "This is an itinerary skeleton only. The final response composer should "
                    "generate actual day content using this city's ranked attractions."
                ),
            })

            day_counter += days_for_city

        return self.success_response(
            data={
                "selected_cities": selected_cities,
                "total_days": total_days,
                "itinerary_type": "multi_city_skeleton",
                "city_plans": city_plans,
            },
            message="Multi-city itinerary skeleton generated successfully.",
        )

    @staticmethod
    def _allocate_days(
        selected_cities: List[str],
        total_days: int,
        city_attractions: Dict[str, Any],
    ) -> Dict[str, int]:
        num_cities = len(selected_cities)

        if num_cities == 0:
            return {}

        base_days = max(total_days // num_cities, 1)
        allocation = {city: base_days for city in selected_cities}

        remaining_days = total_days - (base_days * num_cities)

        for city in selected_cities:
            if remaining_days <= 0:
                break

            allocation[city] += 1
            remaining_days -= 1

        return allocation

```

---

## File: `agents_mcp/transport_agent.py`

```py
from typing import Any, Dict, List, Optional

from config.constants import AGENT_TRANSPORT
from schemas.agent_schema import AgentInput, AgentOutput, AgentMetadata
from agents_mcp.base_agent import BaseAgent
from mcp_clients.transport_mcp_client import TransportMCPClient


class TransportAgent(BaseAgent):
    """
    Builds the trip's structured travel sequence.

    Responsibility:
    - Use TransportMCPClient / transport MCP tools for route data.
    - Order attractions inside each city when coordinates are available.
    - Order cities when coordinates are available.
    - Fetch real transfer legs between source/cities.
    - Produce a rich display_sequence that the final composer can render.

    FinalResponseComposer must not build routing logic itself. It should only
    describe the sequence prepared here.
    """

    def __init__(self):
        metadata = AgentMetadata(
            name=AGENT_TRANSPORT,
            description="Builds inter-city transfer sequence and intra-city POI movement flow.",
            depends_on=[],
            output_key="transport_result",
        )
        super().__init__(metadata)
        self.client = TransportMCPClient()

    def run(self, agent_input: AgentInput) -> AgentOutput:
        city_attractions = agent_input.context.get("city_attractions") or {}

        if city_attractions:
            return self._build_multi_city_sequence(agent_input, city_attractions)

        return self._fetch_single_leg(agent_input)

    # ------------------------------------------------------------------ #
    # Multi-city / hierarchical destination flow
    # ------------------------------------------------------------------ #

    def _build_multi_city_sequence(
        self,
        agent_input: AgentInput,
        city_attractions: Dict[str, Any],
    ) -> AgentOutput:
        selected_cities = agent_input.context.get("selected_cities") or list(city_attractions.keys())
        selected_cities = [city for city in selected_cities if city in city_attractions]

        if not selected_cities:
            return self.error_response(
                error="No valid selected cities found in city_attractions context.",
                data={"mode": "multi_city_sequence"},
            )

        city_blocks: List[Dict[str, Any]] = []
        city_points: List[Dict[str, Any]] = []

        for city in selected_cities:
            places = city_attractions.get(city, {}).get("ranked_places") or []
            usable_places = [
                place for place in places
                if isinstance(place, dict)
                and place.get("latitude") is not None
                and place.get("longitude") is not None
                and place.get("name")
            ]

            ordered_attractions = usable_places
            intra_city_distance_km = 0.0
            intra_city_route_success = False

            if len(usable_places) > 1:
                route_response = self.client.optimize_route(points=usable_places, start_index=0)

                if route_response.success and route_response.data.get("success"):
                    ordered_attractions = route_response.data.get("ordered_points", usable_places)
                    intra_city_distance_km = route_response.data.get("total_distance_km", 0.0)
                    intra_city_route_success = True

            city_blocks.append(
                {
                    "city": city,
                    "ordered_attractions": self._compact_pois(ordered_attractions),
                    "intra_city_distance_km": intra_city_distance_km,
                    "intra_city_route_success": intra_city_route_success,
                    "poi_count": len(ordered_attractions),
                }
            )

            centroid = self._centroid(usable_places)

            if centroid is not None:
                city_points.append(
                    {
                        "name": city,
                        "latitude": centroid[0],
                        "longitude": centroid[1],
                    }
                )

        ordered_city_names = selected_cities

        if len(city_points) == len(selected_cities) and len(city_points) > 1:
            city_route_response = self.client.optimize_route(points=city_points, start_index=0)

            if city_route_response.success and city_route_response.data.get("success"):
                ordered_city_names = [
                    point.get("name")
                    for point in city_route_response.data.get("ordered_points", city_points)
                    if point.get("name")
                ]

        city_blocks_by_name = {block["city"]: block for block in city_blocks}
        ordered_city_blocks = [
            city_blocks_by_name[name]
            for name in ordered_city_names
            if name in city_blocks_by_name
        ]

        inter_city_legs = self._fetch_inter_city_legs(agent_input, ordered_city_names)
        travel_sequence = self._assemble_sequence(ordered_city_blocks, inter_city_legs)
        display_sequence = self._build_display_sequence(ordered_city_blocks, inter_city_legs)

        return self.success_response(
            data={
                "mode": "multi_city_sequence",
                "source": agent_input.source,
                "ordered_cities": ordered_city_names,
                "city_blocks": ordered_city_blocks,
                "inter_city_legs": inter_city_legs,
                "travel_sequence": travel_sequence,
                "display_sequence": display_sequence,
                "sequence_note": (
                    "display_sequence is the prepared user-facing travel flow. "
                    "Final composer should render this sequence, not rebuild routing logic."
                ),
            },
            message="Multi-city travel sequence built successfully.",
        )

    def _fetch_inter_city_legs(
        self,
        agent_input: AgentInput,
        ordered_city_names: List[str],
    ) -> List[Dict[str, Any]]:
        legs: List[Dict[str, Any]] = []

        waypoints = list(ordered_city_names)

        if agent_input.source:
            waypoints = [agent_input.source] + waypoints

        for from_city, to_city in zip(waypoints, waypoints[1:]):
            response = self.client.get_transport_options(
                source=from_city,
                destination=to_city,
                mode="driving-car",
            )

            transport_data = response.data if response.success else None
            compact_transport_data = self._compact_transport_data(transport_data)

            legs.append(
                {
                    "from": from_city,
                    "to": to_city,
                    "success": response.success,
                    "transport_data": compact_transport_data,
                    "error": response.error if not response.success else None,
                }
            )

        return legs

    def _assemble_sequence(
        self,
        ordered_city_blocks: List[Dict[str, Any]],
        inter_city_legs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        sequence: List[Dict[str, Any]] = []
        used_leg_indexes = set()

        for block in ordered_city_blocks:
            city = block["city"]

            matching_leg_index = None
            matching_leg = None

            for index, leg in enumerate(inter_city_legs):
                if index in used_leg_indexes:
                    continue

                if leg.get("to") == city:
                    matching_leg_index = index
                    matching_leg = leg
                    break

            if matching_leg is not None:
                sequence.append({"type": "transfer", **matching_leg})
                used_leg_indexes.add(matching_leg_index)

            sequence.append(
                {
                    "type": "city_visit",
                    "city": city,
                    "ordered_attractions": block.get("ordered_attractions", []),
                    "intra_city_distance_km": block.get("intra_city_distance_km", 0.0),
                    "intra_city_route_success": block.get("intra_city_route_success", False),
                }
            )

        return sequence

    def _build_display_sequence(
        self,
        ordered_city_blocks: List[Dict[str, Any]],
        inter_city_legs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        This is the final structured sequence that the composer should render.

        Example:
        [
          {"type": "transfer", "from": "Delhi", "to": "Puri", ...},
          {"type": "city_flow", "city": "Puri", "pois": [...]},
          {"type": "transfer", "from": "Puri", "to": "Konark", ...},
          {"type": "city_flow", "city": "Konark", "pois": [...]}
        ]
        """
        display_sequence: List[Dict[str, Any]] = []
        used_leg_indexes = set()

        for block in ordered_city_blocks:
            city = block.get("city")

            matching_leg_index = None
            matching_leg = None

            for index, leg in enumerate(inter_city_legs):
                if index in used_leg_indexes:
                    continue

                if leg.get("to") == city:
                    matching_leg_index = index
                    matching_leg = leg
                    break

            if matching_leg is not None:
                transport_data = matching_leg.get("transport_data") or {}

                display_sequence.append(
                    {
                        "type": "transfer",
                        "from": matching_leg.get("from"),
                        "to": matching_leg.get("to"),
                        "success": matching_leg.get("success"),
                        "mode": transport_data.get("mode") or "driving-car",
                        "distance_km": transport_data.get("distance_km"),
                        "duration_hours": transport_data.get("duration_hours"),
                        "duration_minutes": transport_data.get("duration_minutes"),
                        "route_source": transport_data.get("route_source"),
                        "note": self._transfer_note(
                            from_city=matching_leg.get("from"),
                            to_city=matching_leg.get("to"),
                            transport_data=transport_data,
                            success=matching_leg.get("success"),
                            error=matching_leg.get("error"),
                        ),
                    }
                )

                used_leg_indexes.add(matching_leg_index)

            pois = block.get("ordered_attractions") or []

            display_sequence.append(
                {
                    "type": "city_flow",
                    "city": city,
                    "pois": pois,
                    "poi_names": [poi.get("name") for poi in pois if poi.get("name")],
                    "intra_city_distance_km": block.get("intra_city_distance_km", 0.0),
                    "intra_city_route_success": block.get("intra_city_route_success", False),
                    "note": self._city_flow_note(block),
                }
            )

        return display_sequence

    def _transfer_note(
        self,
        from_city: Optional[str],
        to_city: Optional[str],
        transport_data: Dict[str, Any],
        success: bool,
        error: Optional[str],
    ) -> str:
        if not success:
            return (
                f"Could not fetch a reliable road route from {from_city} to {to_city}. "
                f"Reason: {error or 'unknown error'}."
            )

        distance_km = transport_data.get("distance_km")
        duration_hours = transport_data.get("duration_hours")

        if isinstance(distance_km, (int, float)) and distance_km >= 700:
            return "Long-distance transfer. Consider flight or train instead of a full road journey."

        if isinstance(duration_hours, (int, float)) and duration_hours >= 8:
            return "Long road transfer. Keep this as a dedicated travel block."

        if isinstance(duration_hours, (int, float)) and duration_hours >= 4:
            return "Moderate-to-long road transfer. Start early and keep buffer time."

        return "Local or short inter-city transfer."

    def _city_flow_note(self, block: Dict[str, Any]) -> str:
        poi_count = block.get("poi_count", 0)
        route_success = block.get("intra_city_route_success", False)

        if poi_count == 0:
            return "No reliable POI coordinates were available for local ordering."

        if route_success:
            return "POIs are ordered using route optimization where coordinate data was available."

        return "POIs are listed in available ranked order; route optimization was not fully available."

    # ------------------------------------------------------------------ #
    # Single-city / legacy flow
    # ------------------------------------------------------------------ #

    def _fetch_single_leg(self, agent_input: AgentInput) -> AgentOutput:
        if not agent_input.source:
            return self.error_response("Source is required for transport agent.")

        if not agent_input.destination:
            return self.error_response("Destination is required for transport agent.")

        response = self.client.get_transport_options(
            source=agent_input.source,
            destination=agent_input.destination,
            mode="driving-car",
        )

        if not response.success:
            return self.error_response(
                error=response.error or "Failed to fetch transport data.",
                data={
                    "mode": "single_leg",
                    "raw_mcp_response": response.raw_response,
                },
            )

        compact_transport_data = self._compact_transport_data(response.data)

        display_sequence = [
            {
                "type": "transfer",
                "from": agent_input.source,
                "to": agent_input.destination,
                "success": True,
                "mode": compact_transport_data.get("mode") or "driving-car",
                "distance_km": compact_transport_data.get("distance_km"),
                "duration_hours": compact_transport_data.get("duration_hours"),
                "duration_minutes": compact_transport_data.get("duration_minutes"),
                "route_source": compact_transport_data.get("route_source"),
                "note": self._transfer_note(
                    from_city=agent_input.source,
                    to_city=agent_input.destination,
                    transport_data=compact_transport_data,
                    success=True,
                    error=None,
                ),
            }
        ]

        return self.success_response(
            data={
                "mode": "single_leg",
                "source": agent_input.source,
                "destination": agent_input.destination,
                "raw_transport_data": compact_transport_data,
                "display_sequence": display_sequence,
                "raw_mcp_response": response.raw_response,
            },
            message="Transport data fetched successfully.",
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _compact_transport_data(self, transport_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(transport_data, dict):
            return {}

        distance_km = (
            transport_data.get("distance_km")
            or transport_data.get("distance")
            or transport_data.get("estimated_distance_km")
        )

        duration_hours = (
            transport_data.get("duration_hours")
            or transport_data.get("duration")
            or transport_data.get("estimated_duration_hours")
        )

        duration_minutes = transport_data.get("duration_minutes")

        if duration_minutes is None and isinstance(duration_hours, (int, float)):
            duration_minutes = round(duration_hours * 60)

        return {
            "source": transport_data.get("source"),
            "destination": transport_data.get("destination"),
            "mode": transport_data.get("mode") or "driving-car",
            "distance_km": self._round_number(distance_km),
            "duration_hours": self._round_number(duration_hours),
            "duration_minutes": self._round_number(duration_minutes),
            "route_source": (
                transport_data.get("route_source")
                or transport_data.get("source_api")
                or transport_data.get("provider")
                or "transport_service"
            ),
            "note": transport_data.get("note"),
            "raw_summary": transport_data.get("summary"),
        }

    def _compact_pois(self, pois: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        compact = []

        for poi in pois:
            if not isinstance(poi, dict):
                continue

            name = poi.get("name")

            if not name:
                continue

            compact.append(
                {
                    "name": name,
                    "categories": poi.get("categories") or poi.get("category") or [],
                    "formatted_address": poi.get("formatted_address"),
                    "latitude": poi.get("latitude"),
                    "longitude": poi.get("longitude"),
                    "distance_meters": poi.get("distance_meters") or poi.get("distance"),
                    "source": poi.get("source"),
                }
            )

        return compact

    @staticmethod
    def _centroid(places: List[Dict[str, Any]]):
        coords = [
            (place["latitude"], place["longitude"])
            for place in places
            if place.get("latitude") is not None and place.get("longitude") is not None
        ]

        if not coords:
            return None

        avg_lat = sum(lat for lat, _ in coords) / len(coords)
        avg_lon = sum(lon for _, lon in coords) / len(coords)

        return avg_lat, avg_lon

    @staticmethod
    def _round_number(value: Any):
        if isinstance(value, float):
            return round(value, 2)

        return value
```

---

## File: `agents_mcp/__init__.py`

```py

```

---

## File: `config/constants.py`

```py
AGENT_DESTINATION = "destination_agent"
AGENT_CLIMATE = "climate_agent"
AGENT_TRANSPORT = "transport_agent"
AGENT_HOTEL = "hotel_agent"
AGENT_ITINERARY = "itinerary_agent"
AGENT_BUDGET = "budget_agent"

# Canonical execution order. Every layer that selects or orders agents
# (intent analysis, workflow planning) must reuse this single list so the
# pipeline order can never drift between components.
AGENT_ORDER = [
    AGENT_DESTINATION,
    AGENT_CLIMATE,
    AGENT_TRANSPORT,
    AGENT_HOTEL,
    AGENT_ITINERARY,
    AGENT_BUDGET,
]

ALL_AGENTS = list(AGENT_ORDER)


# --- LangGraph node names ---
# Agent nodes reuse the AGENT_* ids above so a node maps 1:1 to an agent.
# These are the control/coordination nodes that surround them.
NODE_INTAKE = "intake"
NODE_PLANNER = "planner"
NODE_CLARIFY = "clarify"
NODE_CITY_SELECTION = "city_selection"
NODE_ATTRACTIONS = "attractions"
NODE_REPLAN = "replan"
NODE_COMPOSE = "compose"
NODE_END = "end"

# --- Planning phases (human-readable, stored in TripState["phase"]) ---
PHASE_INTAKE = "intake"
PHASE_CLARIFY = "clarify"
PHASE_RESOLVE_DESTINATION = "resolve_destination"
PHASE_SELECT_CITIES = "select_cities"
PHASE_PLAN = "plan"
PHASE_EVALUATE = "evaluate"
PHASE_REPLAN = "replan"
PHASE_COMPOSE = "compose"
PHASE_DONE = "done"

# --- Destination scope values ---
SCOPE_CITY = "city"
SCOPE_STATE = "state"
SCOPE_REGION = "region"
SCOPE_COUNTRY = "country"
SCOPE_UNKNOWN = "unknown"

# Scopes that must be narrowed to specific cities before detailed planning.
BROAD_SCOPES = {SCOPE_STATE, SCOPE_REGION, SCOPE_COUNTRY}

# Maximum number of automatic replanning iterations before the planner gives up
# and composes the best-effort plan it has.
MAX_AUTO_REPLANS = 3

```

---

## File: `config/settings.py`

```py
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()
from typing import Optional
from pydantic_settings import BaseSettings

def str_to_bool(value: str, default: bool = True) -> bool:
    if value is None:
        return default

    return value.strip().lower() in ["true", "1", "yes", "y"]


def normalize_mcp_url(url: str, use_mcp_path: bool = True) -> str:
    url = url.rstrip("/")

    if use_mcp_path and not url.endswith("/mcp"):
        url = f"{url}/mcp"

    return url


@dataclass
class AppSettings:
    app_name: str = "Dynamic MCP Multi-Agent Trip Planner"
    app_version: str = "1.0.0"
    debug: bool = str_to_bool(os.getenv("DEBUG", "false"), default=False)


@dataclass
class MCPSettings:
    places_mcp_url: str = normalize_mcp_url(
        os.getenv("PLACES_MCP_URL", "http://127.0.0.1:8001/mcp")
    )

    climate_mcp_url: str = normalize_mcp_url(
        os.getenv("CLIMATE_MCP_URL", "http://127.0.0.1:8002/mcp")
    )

    transport_mcp_url: str = normalize_mcp_url(
        os.getenv("TRANSPORT_MCP_URL", "http://127.0.0.1:8003/mcp")
    )

    hotel_mcp_url: str = normalize_mcp_url(
        os.getenv("HOTEL_MCP_URL", "http://127.0.0.1:8004/mcp")
    )

    timeout: int = int(os.getenv("MCP_TIMEOUT", "30"))


@dataclass
class APISettings:
    geoapify_api_key: str = os.getenv("GEOAPIFY_API_KEY", "")
    openrouteservice_api_key: str = os.getenv("OPENROUTESERVICE_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")


@dataclass
class NetworkSettings:
    ssl_verify: bool = str_to_bool(
        os.getenv("SSL_VERIFY", os.getenv("VERIFY_SSL", "true")),
        default=True,
    )
    geoapify_ssl_verify: bool = str_to_bool(
        os.getenv(
            "GEOAPIFY_VERIFY_SSL",
            os.getenv("GEOAPIFY_SSL_VERIFY", os.getenv("SSL_VERIFY", os.getenv("VERIFY_SSL", "true"))),
        ),
        default=True,
    )
    request_timeout: int = int(os.getenv("REQUEST_TIMEOUT", "30"))

class RedisSettings(BaseSettings):
    redis_enabled: bool = False
    redis_url: Optional[str] = None

    redis_ttl_seconds: int = 86400
    redis_namespace: str = "trip_memory"

    redis_socket_timeout: int = 10
    redis_socket_connect_timeout: int = 10

    class Config:
        env_file = ".env"
        extra = "ignore"


redis_settings = RedisSettings()

app_settings = AppSettings()
mcp_settings = MCPSettings()
api_settings = APISettings()
network_settings = NetworkSettings()
```

---

## File: `config/__init__.py`

```py

```

---

## File: `mcp_clients/base_mcp_client.py`

```py
import asyncio
import json
import threading
from typing import Any, Dict, List, Optional

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from config.settings import network_settings
from schemas.mcp_schema import MCPToolResponse


class BaseMCPClient:
    """Shared Streamable-HTTP MCP client plumbing.

    Concrete clients (places, climate, transport, hotel) only declare their
    server URL/name and expose thin tool wrappers that delegate to
    ``call_tool``. All transport, async bridging and result parsing lives here
    so it is defined exactly once.
    """

    def __init__(self, server_url: str, server_name: str):
        self.server_url = self._ensure_mcp_suffix(server_url)
        self.server_name = server_name

    @staticmethod
    def _ensure_mcp_suffix(url: str) -> str:
        url = url.rstrip("/")

        if not url.endswith("/mcp"):
            url = f"{url}/mcp"

        return url

    def call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> MCPToolResponse:
        try:
            return self._run_async(
                self._call_tool(
                    tool_name=tool_name,
                    arguments=arguments,
                )
            )

        except Exception as e:
            return MCPToolResponse(
                tool_name=tool_name,
                success=False,
                data={},
                error=f"Streamable HTTP MCP {self.server_name} client failed: {str(e)}",
                raw_response=str(e),
            )

    def health_check(self) -> Dict[str, Any]:
        try:
            tools = self._run_async(self._list_tools())

            return {
                "server_name": self.server_name,
                "server_url": self.server_url,
                "status": "healthy",
                "tools": tools,
            }

        except Exception as e:
            return {
                "server_name": self.server_name,
                "server_url": self.server_url,
                "status": "unhealthy",
                "error": str(e),
            }

    async def _call_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> MCPToolResponse:
        async with streamablehttp_client(
            self.server_url,
            httpx_client_factory=lambda headers, timeout, auth: httpx.AsyncClient(
                follow_redirects=True,
                verify=network_settings.ssl_verify,
                headers=headers,
                timeout=timeout,
                auth=auth,
            ),
        ) as transport:
            read_stream, write_stream, _ = transport

            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                result = await session.call_tool(
                    tool_name,
                    arguments=arguments,
                )

                parsed = self._parse_tool_result(result)
                success = bool(parsed.get("success", True))

                return MCPToolResponse(
                    tool_name=tool_name,
                    success=success,
                    data=parsed,
                    error=parsed.get("error"),
                    raw_response=parsed,
                )

    async def _list_tools(self) -> List[Dict[str, Any]]:
        async with streamablehttp_client(
            self.server_url,
            httpx_client_factory=lambda headers, timeout, auth: httpx.AsyncClient(
                follow_redirects=True,
                verify=network_settings.ssl_verify,
                headers=headers,
                timeout=timeout,
                auth=auth,
            ),
        ) as transport:
            read_stream, write_stream, _ = transport

            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                tools_result = await session.list_tools()

                return [
                    {
                        "name": tool.name,
                        "description": tool.description,
                    }
                    for tool in tools_result.tools
                ]

    def _parse_tool_result(self, result: Any) -> Dict[str, Any]:
        if hasattr(result, "content") and result.content:
            for item in result.content:
                text = getattr(item, "text", None)

                if text:
                    try:
                        return json.loads(text)
                    except Exception:
                        return {
                            "success": True,
                            "result": text,
                        }

        return {
            "success": True,
            "raw_result": str(result),
        }

    def _run_async(self, coro):
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        # A loop is already running on this thread (e.g. Streamlit). Run the
        # coroutine to completion on a dedicated thread to avoid nesting loops.
        output = {}
        error = {}

        def runner():
            try:
                output["value"] = asyncio.run(coro)
            except Exception as e:
                error["value"] = e

        thread = threading.Thread(target=runner)
        thread.start()
        thread.join()

        if "value" in error:
            raise error["value"]

        return output.get("value")

```

---

## File: `mcp_clients/climate_mcp_client.py`

```py
from typing import Dict, Optional

from config.settings import mcp_settings
from mcp_clients.base_mcp_client import BaseMCPClient
from schemas.mcp_schema import MCPToolResponse


class ClimateMCPClient(BaseMCPClient):
    def __init__(self):
        super().__init__(
            server_url=mcp_settings.climate_mcp_url,
            server_name="climate_mcp_server",
        )

    def get_climate(
        self,
        destination: str,
        month: Optional[str] = None,
        travel_dates: Optional[Dict[str, str]] = None,
    ) -> MCPToolResponse:
        return self.call_tool(
            tool_name="get_climate",
            arguments={
                "destination": destination,
                "month": month,
                "travel_dates": travel_dates,
            },
        )

```

---

## File: `mcp_clients/hotel_mcp_client.py`

```py
from typing import Optional

from config.settings import mcp_settings
from mcp_clients.base_mcp_client import BaseMCPClient
from schemas.mcp_schema import MCPToolResponse


class HotelMCPClient(BaseMCPClient):
    def __init__(self):
        super().__init__(
            server_url=mcp_settings.hotel_mcp_url,
            server_name="hotel_mcp_server",
        )

    def search_hotels(
        self,
        destination: str,
        budget: Optional[str] = None,
        travelers: Optional[int] = None,
        limit: int = 10,
    ) -> MCPToolResponse:
        return self.call_tool(
            tool_name="search_hotels",
            arguments={
                "destination": destination,
                "budget": budget,
                "travelers": travelers,
                "limit": limit,
            },
        )

```

---

## File: `mcp_clients/places_mcp_client.py`

```py
from typing import Any, Dict, List, Optional

from config.settings import mcp_settings
from mcp_clients.base_mcp_client import BaseMCPClient
from schemas.mcp_schema import MCPToolResponse


class PlacesMCPClient(BaseMCPClient):
    def __init__(self):
        super().__init__(
            server_url=mcp_settings.places_mcp_url,
            server_name="places_mcp_server",
        )

    def get_popular_places(
        self,
        destination: str,
        interests: Optional[List[str]] = None,
        limit: int = 10,
    ) -> MCPToolResponse:
        return self.call_tool(
            tool_name="get_popular_places",
            arguments={
                "destination": destination,
                "interests": interests or [],
                "limit": limit,
            },
        )

    def recommend_destinations(
        self,
        source: Optional[str] = None,
        interests: Optional[List[str]] = None,
        month: Optional[str] = None,
        budget: Optional[str] = None,
        days: Optional[int] = None,
        travelers: Optional[int] = None,
        limit: int = 8,
    ) -> MCPToolResponse:
        return self.call_tool(
            tool_name="recommend_destinations",
            arguments={
                "source": source,
                "interests": interests or [],
                "month": month,
                "budget": budget,
                "days": days,
                "travelers": travelers,
                "limit": limit,
            },
        )

    def classify_destination(self, name: str) -> MCPToolResponse:
        return self.call_tool(
            tool_name="classify_destination",
            arguments={"name": name},
        )

    def recommend_cities_in_region(
        self,
        region: str,
        interests: Optional[List[str]] = None,
        days: Optional[int] = None,
        budget: Optional[str] = None,
        travelers: Optional[int] = None,
        travel_style: Optional[str] = None,
        limit: int = 6,
    ) -> MCPToolResponse:
        return self.call_tool(
            tool_name="recommend_cities_in_region",
            arguments={
                "region": region,
                "interests": interests or [],
                "days": days,
                "budget": budget,
                "travelers": travelers,
                "travel_style": travel_style,
                "limit": limit,
            },
        )

    def rank_places(
        self,
        city: str,
        places: List[Dict[str, Any]],
        interests: Optional[List[str]] = None,
        days: Optional[int] = None,
    ) -> MCPToolResponse:
        return self.call_tool(
            tool_name="rank_places",
            arguments={
                "city": city,
                "places": places or [],
                "interests": interests or [],
                "days": days,
            },
        )

```

---

## File: `mcp_clients/transport_mcp_client.py`

```py
from typing import Any, Dict, List, Optional

from config.settings import mcp_settings
from mcp_clients.base_mcp_client import BaseMCPClient
from schemas.mcp_schema import MCPToolResponse


class TransportMCPClient(BaseMCPClient):
    def __init__(self):
        super().__init__(
            server_url=mcp_settings.transport_mcp_url,
            server_name="transport_mcp_server",
        )

    def get_transport_options(
        self,
        source: str,
        destination: str,
        mode: Optional[str] = "driving-car",
    ) -> MCPToolResponse:
        return self.call_tool(
            tool_name="get_transport_options",
            arguments={
                "source": source,
                "destination": destination,
                "mode": mode or "driving-car",
            },
        )

    def optimize_route(
        self,
        points: List[Dict[str, Any]],
        start_index: int = 0,
    ) -> MCPToolResponse:
        return self.call_tool(
            tool_name="optimize_route",
            arguments={
                "points": points or [],
                "start_index": start_index,
            },
        )

```

---

## File: `mcp_clients/__init__.py`

```py

```

---

## File: `mcp_servers/climate_mcp_server.py`

```py
import json
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from services.weather_service import WeatherService


mcp = FastMCP(
    "climate_mcp_server",
    host="127.0.0.1",
    port=8002,
    json_response=True,
)

weather_service = WeatherService()


@mcp.tool()
def get_climate(
    destination: str,
    month: Optional[str] = None,
    travel_dates: Optional[Dict[str, str]] = None,
) -> str:
    result: Dict[str, Any] = weather_service.get_climate(
        destination=destination,
        month=month,
        travel_dates=travel_dates,
    )

    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

---

## File: `mcp_servers/hotel_mcp_server.py`

```py
import json
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP

from services.hotel_service import HotelService


mcp = FastMCP(
    "hotel_mcp_server",
    host="127.0.0.1",
    port=8004,
    json_response=True,
)

hotel_service = HotelService()


@mcp.tool()
def search_hotels(
    destination: str,
    budget: Optional[str] = None,
    travelers: Optional[int] = None,
    limit: int = 10,
) -> str:
    result: Dict[str, Any] = hotel_service.search_hotels(
        destination=destination,
        budget=budget,
        travelers=travelers,
        limit=limit,
    )

    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

---

## File: `mcp_servers/places_mcp_server.py`

```py
import json
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from services.places_service import PlacesService


mcp = FastMCP(
    "places_mcp_server",
    host="127.0.0.1",
    port=8001,
    json_response=True,
)

places_service = PlacesService()


@mcp.tool()
def recommend_destinations(
    source: Optional[str] = None,
    interests: Optional[List[str]] = None,
    month: Optional[str] = None,
    budget: Optional[str] = None,
    days: Optional[int] = None,
    travelers: Optional[int] = None,
    limit: int = 8,
) -> str:
    result: Dict[str, Any] = places_service.recommend_destinations(
        source=source,
        interests=interests or [],
        month=month,
        budget=budget,
        days=days,
        travelers=travelers,
        limit=limit,
    )

    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def get_popular_places(
    destination: str,
    interests: Optional[List[str]] = None,
    limit: int = 10,
) -> str:
    result: Dict[str, Any] = places_service.get_popular_places(
        destination=destination,
        interests=interests or [],
        limit=limit,
    )

    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def classify_destination(name: str) -> str:
    result: Dict[str, Any] = places_service.classify_destination(name=name)

    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def recommend_cities_in_region(
    region: str,
    interests: Optional[List[str]] = None,
    days: Optional[int] = None,
    budget: Optional[str] = None,
    travelers: Optional[int] = None,
    travel_style: Optional[str] = None,
    limit: int = 6,
) -> str:
    result: Dict[str, Any] = places_service.recommend_cities_in_region(
        region=region,
        interests=interests or [],
        days=days,
        budget=budget,
        travelers=travelers,
        travel_style=travel_style,
        limit=limit,
    )

    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def rank_places(
    city: str,
    places: List[Dict[str, Any]],
    interests: Optional[List[str]] = None,
    days: Optional[int] = None,
) -> str:
    result: Dict[str, Any] = places_service.rank_places(
        city=city,
        places=places or [],
        interests=interests or [],
        days=days,
    )

    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

---

## File: `mcp_servers/transport_mcp_server.py`

```py
import json
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

from services.transport_service import TransportService


mcp = FastMCP(
    "transport_mcp_server",
    host="127.0.0.1",
    port=8003,
    json_response=True,
)

transport_service = TransportService()


@mcp.tool()
def get_transport_options(
    source: str,
    destination: str,
    mode: str = "driving-car",
) -> str:
    result: Dict[str, Any] = transport_service.get_transport_options(
        source=source,
        destination=destination,
        mode=mode,
    )

    return json.dumps(result, ensure_ascii=False)


@mcp.tool()
def optimize_route(
    points: List[Dict[str, Any]],
    start_index: int = 0,
) -> str:
    result: Dict[str, Any] = transport_service.optimize_route(
        points=points or [],
        start_index=start_index,
    )

    return json.dumps(result, ensure_ascii=False)


if __name__ == "__main__":
    mcp.run(transport="streamable-http")
```

---

## File: `mcp_servers/__init__.py`

```py

```

---

## File: `memory/redis_trip_memory.py`

```py
import copy
import json
import uuid
from typing import Any, Dict, Optional

import redis

from config.settings import redis_settings


DEFAULT_TRIP_MEMORY = {
    "request_memory": {
        "source": None,
        "destination": None,
        "days": None,
        "month": None,
        "budget": None,
        "travelers": None,
        "interests": [],
    },
    "planning_memory": {
        "selected_cities": [],
        "dropped_cities": [],
        "replan_count": 0,
        "last_feasible": None,
    },
    "response_memory": {
        "last_final_response": None,
        "last_summary": None,
    },
    "conversation_history": [],
}


class RedisTripMemory:
    """
    Redis-backed short-term trip memory.

    Redis is only used by app/orchestrator layer.
    Agents should not directly read/write Redis.
    """

    def __init__(self):
        self.enabled = redis_settings.redis_enabled
        self.redis_url = redis_settings.redis_url
        self.ttl_seconds = redis_settings.redis_ttl_seconds
        self.namespace = redis_settings.redis_namespace
        self.client = None

        if not self.enabled:
            print("[RedisTripMemory] Disabled by settings.")
            return

        if not self.redis_url:
            print("[RedisTripMemory] REDIS_URL missing. Memory disabled.")
            self.enabled = False
            return

        try:
            self.client = redis.Redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_timeout=redis_settings.redis_socket_timeout,
                socket_connect_timeout=redis_settings.redis_socket_connect_timeout,
                protocol=2,
            )
            self.client.ping()
            print("[RedisTripMemory] Connected to Redis successfully.")
        except Exception as e:
            print("[RedisTripMemory] Redis unavailable. Memory disabled.")
            print(type(e).__name__, str(e))
            self.client = None
            self.enabled = False

    def create_session_id(self) -> str:
        return str(uuid.uuid4())

    def default_memory(self) -> Dict[str, Any]:
        return copy.deepcopy(DEFAULT_TRIP_MEMORY)

    def _key(self, session_id: str) -> str:
        return f"{self.namespace}:{session_id}"

    def load(self, session_id: Optional[str]) -> Dict[str, Any]:
        if not session_id:
            return self.default_memory()

        if not self.enabled or not self.client:
            return self.default_memory()

        raw = self.client.get(self._key(session_id))

        if not raw:
            return self.default_memory()

        try:
            return self._normalize_memory(json.loads(raw))
        except Exception:
            return self.default_memory()

    def save(self, session_id: Optional[str], memory: Dict[str, Any]) -> None:
        if not session_id:
            return

        if not self.enabled or not self.client:
            return

        normalized = self._normalize_memory(memory)

        self.client.setex(
            self._key(session_id),
            self.ttl_seconds,
            json.dumps(normalized, ensure_ascii=False),
        )

    def clear(self, session_id: Optional[str]) -> None:
        if not session_id:
            return

        if not self.enabled or not self.client:
            return

        self.client.delete(self._key(session_id))

    def append_turn(
        self,
        session_id: Optional[str],
        role: str,
        content: str,
        max_turns: int = 8,
    ) -> Dict[str, Any]:
        memory = self.load(session_id)

        history = memory.get("conversation_history") or []
        history.append(
            {
                "role": role,
                "content": content,
            }
        )

        memory["conversation_history"] = history[-max_turns:]
        self.save(session_id, memory)

        return memory

    def merge_memory_into_request(
        self,
        memory: Dict[str, Any],
        current_request: Dict[str, Any],
    ) -> Dict[str, Any]:
        request_memory = memory.get("request_memory") or {}
        merged = copy.deepcopy(request_memory)

        for key, value in (current_request or {}).items():
            if self._is_meaningful(value):
                merged[key] = value

        return merged

    def update_from_state(
        self,
        session_id: Optional[str],
        state: Dict[str, Any],
        final_response: Optional[str] = None,
    ) -> Dict[str, Any]:
        memory = self.load(session_id)

        request = state.get("request") or {}

        memory["request_memory"] = self._merge_request_memory(
            old_memory=memory.get("request_memory") or {},
            current_request=request,
        )

        memory["planning_memory"] = {
            "selected_cities": state.get("selected_cities") or [],
            "dropped_cities": self._extract_dropped_cities(state),
            "replan_count": state.get("replan_count", 0),
            "last_feasible": state.get("feasible"),
        }

        memory["response_memory"] = {
            "last_final_response": final_response or state.get("final_response"),
            "last_summary": {
                "selected_cities": state.get("selected_cities") or [],
                "feasible": state.get("feasible"),
                "travel_sequence": state.get("travel_sequence"),
            },
        }

        self.save(session_id, memory)
        return memory

    def _merge_request_memory(
        self,
        old_memory: Dict[str, Any],
        current_request: Dict[str, Any],
    ) -> Dict[str, Any]:
        merged = copy.deepcopy(old_memory or {})

        fields = [
            "source",
            "destination",
            "days",
            "month",
            "budget",
            "travelers",
            "interests",
        ]

        for field in fields:
            if field not in current_request:
                continue

            value = current_request.get(field)

            if self._is_meaningful(value):
                merged[field] = value

        return merged

    def _normalize_memory(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        default = self.default_memory()

        if not isinstance(memory, dict):
            return default

        for key, value in default.items():
            if key not in memory:
                memory[key] = copy.deepcopy(value)

        request_memory = memory.get("request_memory") or {}

        # Remove old unsupported keys saved in Redis, such as travel_style.
        allowed_request_fields = set(default["request_memory"].keys())
        request_memory = {
            key: value
            for key, value in request_memory.items()
            if key in allowed_request_fields
        }

        memory["request_memory"] = {
            **default["request_memory"],
            **request_memory,
        }

        memory["planning_memory"] = {
            **default["planning_memory"],
            **(memory.get("planning_memory") or {}),
        }

        memory["response_memory"] = {
            **default["response_memory"],
            **(memory.get("response_memory") or {}),
        }

        if not isinstance(memory.get("conversation_history"), list):
            memory["conversation_history"] = []

        memory["conversation_history"] = memory["conversation_history"][-8:]

        return memory

    def _extract_dropped_cities(self, state: Dict[str, Any]):
        directives = state.get("replan_directives") or []
        dropped = []

        for directive in directives:
            if not isinstance(directive, dict):
                continue

            city = directive.get("drop_city") or directive.get("city")

            if city:
                dropped.append(city)

        return dropped

    def _is_meaningful(self, value: Any) -> bool:
        if value is None:
            return False

        if isinstance(value, str) and not value.strip():
            return False

        if isinstance(value, list) and len(value) == 0:
            return False

        if isinstance(value, dict) and len(value) == 0:
            return False

        return True
```

---

## File: `memory/__init__.py`

```py

```

---

## File: `orchestrator/final_response_composer.py`

```py
import html
import json
import re
from typing import Any, Dict, List

import google.generativeai as genai

from config.settings import api_settings
from schemas.trip_schema import TripState


class FinalResponseComposer:
    """
    Turns a completed TripState into the final user-facing Markdown response.

    Important:
    - TransportAgent owns route/sequence construction.
    - Composer only renders the prepared travel_sequence/display_sequence.
    """

    STRONG_ATTRACTION_TERMS = [
        "tourism",
        "tourism.attraction",
        "tourism.sights",
        "tourism.information",
        "entertainment.museum",
        "museum",
        "heritage",
        "historic",
        "historical",
        "monument",
        "memorial",
        "castle",
        "fort",
        "palace",
        "archaeological",
        "religion",
        "temple",
        "church",
        "mosque",
        "natural",
        "natural.water",
        "natural.mountain",
        "natural.forest",
        "natural.beach",
        "beach",
        "lake",
        "waterfall",
        "park",
        "garden",
        "viewpoint",
        "zoo",
        "aquarium",
        "leisure.park",
        "validated_landmark",
    ]

    WEAK_OR_NON_ATTRACTION_TERMS = [
        "catering",
        "restaurant",
        "cafe",
        "coffee",
        "bar",
        "pub",
        "fast_food",
        "food_court",
        "accommodation",
        "hotel",
        "hostel",
        "guest_house",
        "apartment",
        "resort",
        "commercial",
        "shop",
        "shopping",
        "marketplace",
        "supermarket",
        "mall",
        "book",
        "books",
        "bookstore",
        "office",
        "bank",
        "atm",
        "street",
        "road",
        "highway",
        "residential",
        "building",
        "service",
        "healthcare",
        "hospital",
        "pharmacy",
        "education",
        "school",
        "college",
        "university",
        "parking",
        "fuel",
        "transport",
        "bus",
        "railway",
        "airport",
    ]

    WEAK_NAME_HINTS = [
        "road",
        "street",
        "rasta",
        "marg",
        "path",
        "lane",
        "hotel",
        "restaurant",
        "cafe",
        "coffee",
        "bhojnalaya",
        "dhaba",
        "bar",
        "pub",
        "book",
        "pustak",
        "store",
        "shop",
        "bank",
        "atm",
    ]

    def __init__(self):
        self.model = None

        if api_settings.gemini_api_key:
            genai.configure(api_key=api_settings.gemini_api_key)
            self.model = genai.GenerativeModel(api_settings.gemini_model)

    def compose(self, state: TripState) -> Dict[str, Any]:
        if not self.model:
            return {
                "success": False,
                "error": "Gemini API key is missing. Final response composition skipped.",
                "response": None,
            }

        payload = self._build_payload(state)
        compact_payload = self._compact_payload(payload)
        prompt = self._build_prompt(compact_payload)

        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.18,
                    "top_p": 0.8,
                    "top_k": 40,
                },
            )

            text = getattr(response, "text", "").strip()

            if not text:
                return {
                    "success": False,
                    "error": "Gemini returned empty final response.",
                    "response": None,
                    "input_payload": compact_payload,
                }

            return {
                "success": True,
                "response": self._clean_final_response(text),
                "input_payload": compact_payload,
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Final response composition failed: {type(e).__name__}: {str(e)}",
                "response": None,
                "input_payload": compact_payload,
            }

    def _build_payload(self, state: TripState) -> Dict[str, Any]:
        return {
            "request": state.get("request", {}),
            "selected_cities": state.get("selected_cities", []),
            "city_attractions": state.get("city_attractions", {}),
            "agent_results": state.get("agent_results", {}),
            "travel_sequence": state.get("travel_sequence"),
            "feasible": state.get("feasible"),
            "replan_directives": state.get("replan_directives", []),
            "errors": state.get("errors", []),
        }

    def _compact_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        request = payload.get("request", {})
        agent_results = payload.get("agent_results", {})
        city_attractions = payload.get("city_attractions", {})

        compact_cities = {}

        for city, data in city_attractions.items():
            places = (data or {}).get("ranked_places") or (data or {}).get("places") or []
            filtered_places = self._filter_high_quality_places(places)

            compact_cities[city] = {
                "places_available": len(filtered_places) > 0,
                "poi_quality": "usable" if len(filtered_places) >= 3 else "weak",
                "usable_place_count": len(filtered_places),
                "places": filtered_places[:8],
            }

        climate_by_city = self._safe_get(agent_results, ["climate_agent", "data", "by_city"]) or {}
        hotel_by_city = self._safe_get(agent_results, ["hotel_agent", "data", "by_city"]) or {}
        itinerary_result = self._safe_get(agent_results, ["itinerary_agent", "data"]) or {}
        budget_result = self._safe_get(agent_results, ["budget_agent", "data"]) or {}
        transport_result = self._safe_get(agent_results, ["transport_agent", "data"]) or {}

        compact_climate = {
            city: self._safe_get(result, ["data", "raw_climate_data"])
            for city, result in climate_by_city.items()
        }

        compact_hotel = {
            city: self._safe_get(result, ["data", "raw_hotel_data"])
            for city, result in hotel_by_city.items()
        }

        prepared_travel_sequence = payload.get("travel_sequence") or transport_result

        return {
            "request": request,
            "selected_cities": payload.get("selected_cities", []),
            "city_attractions": compact_cities,
            "climate_by_city": compact_climate,
            "hotel_by_city": compact_hotel,
            "travel_sequence": prepared_travel_sequence,
            "itinerary_skeleton": itinerary_result,
            "budget_result": budget_result,
            "feasible": payload.get("feasible"),
            "replan_directives": payload.get("replan_directives", []),
            "errors": payload.get("errors", []),
            "composer_instruction": (
                "Render travel_sequence.display_sequence exactly as the prepared route flow. "
                "Do not build route sequence yourself. Do not invent distances or local POI order."
            ),
        }

    def _filter_high_quality_places(self, places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not places:
            return []

        filtered = []
        seen_names = set()

        for item in places:
            if not isinstance(item, dict):
                continue

            name = self._clean_text(item.get("name"))

            if not name:
                continue

            normalized_name = name.lower().strip()

            if normalized_name in seen_names:
                continue

            if self._looks_like_weak_name(normalized_name):
                continue

            categories = (
                item.get("categories")
                or item.get("category")
                or item.get("kinds")
                or []
            )

            if isinstance(categories, str):
                categories = [categories]

            category_text = " ".join(str(category).lower() for category in categories)

            if self._has_weak_category(category_text):
                continue

            if not self._has_strong_attraction_category(category_text):
                continue

            seen_names.add(normalized_name)

            filtered.append(
                {
                    "name": name,
                    "categories": categories,
                    "formatted_address": self._clean_text(
                        item.get("formatted_address")
                        or item.get("address")
                        or item.get("formatted")
                    ),
                    "distance_meters": item.get("distance_meters") or item.get("distance"),
                    "latitude": item.get("latitude"),
                    "longitude": item.get("longitude"),
                    "source": item.get("source") or "places_service",
                }
            )

        return filtered

    def _has_strong_attraction_category(self, category_text: str) -> bool:
        if not category_text:
            return False

        return any(term in category_text for term in self.STRONG_ATTRACTION_TERMS)

    def _has_weak_category(self, category_text: str) -> bool:
        if not category_text:
            return False

        return any(term in category_text for term in self.WEAK_OR_NON_ATTRACTION_TERMS)

    def _looks_like_weak_name(self, normalized_name: str) -> bool:
        if not normalized_name:
            return True

        return any(hint in normalized_name for hint in self.WEAK_NAME_HINTS)

    def _safe_get(self, data: Dict[str, Any], path: list, default=None):
        current = data

        for key in path:
            if not isinstance(current, dict):
                return default

            current = current.get(key)

            if current is None:
                return default

        return current

    def _clean_text(self, value):
        if value is None:
            return None

        if not isinstance(value, str):
            return value

        value = html.unescape(value)
        value = re.sub(r"\s+", " ", value)
        return value.strip()

    def _clean_final_response(self, text: str) -> str:
        text = html.unescape(text)
        text = text.replace("\u00a0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        text = re.sub(r"([a-z])It ", r"\1. It ", text)
        text = re.sub(r"([a-z])This ", r"\1. This ", text)
        text = re.sub(r"([a-z])Please ", r"\1. Please ", text)

        return text.strip()

    def _build_prompt(self, payload: Dict[str, Any]) -> str:
        return f"""
You are a professional AI trip planning assistant.

Your job:
Compose the final user-facing travel response using structured outputs from trip-planning components.

Architecture rules:
- Components provide raw facts.
- You generate the final written response.
- Do not expose internal JSON.
- Do not mention internal component names.
- Do not invent exact transport distances, hotel names, or attraction names.

CRITICAL TRAVEL SEQUENCE RULES:
1. Use travel_sequence.display_sequence as the source of truth.
2. Do not construct or infer route sequence yourself.
3. Do not invent missing distances or durations.
4. Render each transfer in display_sequence.
5. Render each city_flow in display_sequence.
6. If city_flow has poi_names, include those POIs as the local movement order.
7. If city_flow has no POIs, write a high-level local flow only.
8. For long transfers, mention that they should be treated as dedicated travel blocks.
9. Do not list only city-to-city transfers if city_flow data is available.

ATTRACTION RULES:
10. Use named attractions only from structured city_attractions or travel_sequence city_flow.
11. Never use restaurants, cafes, hotels, roads, streets, bookstores, shops, banks, offices, or random commercial POIs as attractions.
12. Do not invent famous attractions missing from the structured context.

CLIMATE RULES:
13. Use climate_by_city for practical advice.
14. Day-wise itinerary must reflect climate advice.
15. For hot or humid months, schedule outdoor visits early morning/evening and midday rest/indoor activities.

HOTEL RULES:
16. Use hotel_by_city for stay-area guidance.
17. Do not invent specific hotel names.
18. If hotel data is limited, suggest areas and stay types.

BUDGET RULES:
19. Budget is a rough estimate. Say that clearly.
20. If feasible is false, include a short feasibility warning.
21. If replan_directives exist, explain the adjustment naturally.

STYLE RULES:
22. Keep the answer polished, professional, concise, and useful.
23. Use Markdown.
24. Day numbers must continue across cities.
25. Do not output HTML entities like &amp;.
26. Do not include internal field names like poi_quality, raw_climate_data, or agent_results.

Structured planning context:
{json.dumps(payload, indent=2, ensure_ascii=False)}

Output format:

## Trip Summary

## Climate-Aware Advice

## Travel Sequence

## Stay Suggestions

## Day-Wise Itinerary

## Budget Snapshot

## Notes
"""
```

---

## File: `orchestrator/intent_analyzer.py`

```py
import json
from typing import Any, Dict, List, Optional

import spacy
import google.generativeai as genai

from config.settings import api_settings
from config.constants import (
    AGENT_DESTINATION,
    AGENT_CLIMATE,
    AGENT_TRANSPORT,
    AGENT_HOTEL,
    AGENT_ITINERARY,
    AGENT_BUDGET,
    AGENT_ORDER,
    SCOPE_CITY,
    SCOPE_REGION,
    SCOPE_UNKNOWN,
)
from schemas.trip_schema import TripRequest


class IntentAnalyzer:
    def __init__(self, confidence_threshold: float = 0.70):
        self.confidence_threshold = confidence_threshold

        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            self.nlp = spacy.blank("en")
            self.nlp.add_pipe("sentencizer")

        self.model = None

        if api_settings.gemini_api_key:
            genai.configure(api_key=api_settings.gemini_api_key)
            self.model = genai.GenerativeModel(api_settings.gemini_model)

    def analyze(self, user_query: str) -> TripRequest:
        spacy_request = self._analyze_with_spacy(user_query)

        if self._is_spacy_result_good_enough(spacy_request):
            return spacy_request

        gemini_request = self._analyze_with_gemini(user_query, spacy_request)

        if gemini_request:
            return gemini_request

        return spacy_request

    def _analyze_with_spacy(self, user_query: str) -> TripRequest:
        doc = self.nlp(user_query)

        source = self._extract_source_from_dependency(doc)
        destination = self._extract_destination_from_dependency(doc, source)

        entities = self._extract_entities(doc)

        if not source:
            source = entities.get("source")

        if not destination:
            destination = entities.get("destination")

        month = entities.get("month")
        days = entities.get("days")
        travelers = entities.get("travelers")

        interests = self._extract_interest_candidates(doc)
        budget = self._extract_budget_candidate(doc)

        request = TripRequest(
            user_query=user_query,
            source=source,
            destination=destination,
            month=month,
            days=days,
            budget=budget,
            travelers=travelers,
            interests=interests,
            parser_used="spacy",
        )

        request.suggested_agents = self._infer_agents(request)
        request.missing_fields = self._find_missing_fields(request)
        request.confidence = self._score_spacy_result(request)

        return request

    def _extract_source_from_dependency(self, doc) -> Optional:
        for token in doc:
            if token.text.lower() == "from":
                location = self._collect_prepositional_object(token)

                if location:
                    return location

        return None

    def _extract_destination_from_dependency(self, doc, source: Optional[str]) -> Optional:
        for token in doc:
            if token.text.lower() == "to":
                location = self._collect_prepositional_object(token)

                if location and location != source:
                    return location

        query = doc.text.lower()

        vague_destination_query = any(
            phrase in query
            for phrase in [
                "getaway from",
                "vacation from",
                "holiday from",
                "somewhere",
                "near the coast",
                "near coast",
                "coastal",
                "preferably near",
            ]
        )

        if vague_destination_query:
            return None

        if source:
            return None

        for ent in doc.ents:
            if ent.label_ in {"GPE", "LOC"}:
                value = ent.text.strip().title()

                if value and value != source:
                    return value

        return None

    def _collect_prepositional_object(self, prep_token) -> Optional:
        words = []

        for child in prep_token.children:
            if child.dep_ in {"pobj", "pcomp", "compound"} or child.ent_type_ in {"GPE", "LOC"}:
                subtree_words = [token.text for token in child.subtree]
                words.extend(subtree_words)

        if not words:
            return None

        value = " ".join(words).strip(" ,.")
        value = value.title()

        blocked = {
            "The Coast",
            "Coast",
            "Beach",
            "Beaches",
            "Somewhere",
            "Nearby",
        }

        if value in blocked:
            return None

        return value

    def _extract_entities(self, doc) -> Dict[str, Any]:
        result = {
            "source": None,
            "destination": None,
            "month": None,
            "days": None,
            "travelers": None,
        }

        for ent in doc.ents:
            if ent.label_ == "DATE":
                date_value = self._normalize_date_entity(ent.text)

                if date_value.get("month"):
                    result["month"] = date_value["month"]

                if date_value.get("days"):
                    result["days"] = date_value["days"]

            if ent.label_ == "CARDINAL":
                number = self._safe_int(ent.text)

                if number:
                    nearby_text = self._get_nearby_text(doc, ent.start, ent.end)

                    if any(word in nearby_text for word in ["friend", "friends", "people", "person", "traveler", "travellers", "travelers"]):
                        result["travelers"] = number

                    if any(word in nearby_text for word in ["day", "days", "night", "nights"]):
                        result["days"] = number

        return result

    def _normalize_date_entity(self, text: str) -> Dict[str, Any]:
        value = text.lower()

        month_map = {
            "january": "January",
            "february": "February",
            "march": "March",
            "april": "April",
            "may": "May",
            "june": "June",
            "july": "July",
            "august": "August",
            "september": "September",
            "october": "October",
            "november": "November",
            "december": "December",
            "christmas": "December",
            "new year": "January",
        }

        for key, month in month_map.items():
            if key in value:
                return {"month": month, "days": None}

        if "long weekend" in value:
            return {"month": None, "days": 3}

        if "weekend" in value:
            return {"month": None, "days": 2}

        if "week" in value:
            return {"month": None, "days": 7}

        return {"month": None, "days": None}

    def _extract_interest_candidates(self, doc) -> List:
        interest_labels = {
            "beach": {"beach", "beaches", "coast", "coastal", "sea"},
            "nature": {"nature", "hill", "hills", "mountain", "mountains", "forest", "wildlife", "lake"},
            "food": {"food", "cuisine", "restaurant", "restaurants"},
            "nightlife": {"nightlife", "club", "clubs", "party", "pub", "bar"},
            "relaxation": {"peaceful", "relaxing", "relaxed", "calm", "quiet"},
            "romantic": {"romantic", "couple"},
            "heritage": {"heritage", "history", "historical", "fort", "palace", "museum"},
            "religious": {"temple", "temples", "church", "mosque", "spiritual"},
            "adventure": {"adventure", "trek", "trekking", "rafting", "scuba"},
            "shopping": {"shopping", "market", "markets"},
        }

        found = set()

        lemmas = {token.lemma_.lower() for token in doc if not token.is_stop}
        texts = {token.text.lower() for token in doc if not token.is_stop}
        words = lemmas.union(texts)

        for label, keywords in interest_labels.items():
            if words.intersection(keywords):
                found.add(label)

        return sorted(found)

    def _extract_budget_candidate(self, doc) -> Optional:
        words = [token.text.lower() for token in doc]
        joined = " ".join(words)

        low_phrases = [
            "not too expensive",
            "not expensive",
            "not costly",
            "not too costly",
            "not very expensive",
            "not very costly",
            "affordable",
            "cheap",
            "budget friendly",
            "budget-friendly",
            "pocket friendly",
            "pocket-friendly",
        ]

        for phrase in low_phrases:
            if phrase in joined:
                return "low"

        medium_phrases = [
            "moderate",
            "comfortable",
            "standard",
            "decent",
            "mid range",
            "mid-range",
        ]

        for phrase in medium_phrases:
            if phrase in joined:
                return "medium"

        high_phrases = [
            "luxury",
            "premium",
            "high budget",
            "5 star",
            "five star",
            "lavish",
        ]

        for phrase in high_phrases:
            if phrase in joined:
                return "high"

        if "expensive" in words or "costly" in words:
            return "high"

        return None

    def _is_spacy_result_good_enough(self, request: TripRequest) -> bool:
        query = request.user_query.lower()
    
        if request.source and request.destination:
            if request.source.strip().lower() == request.destination.strip().lower():
                return False
    
        vague_destination_signals = [
            "somewhere",
            "near",
            "nearby",
            "preferably",
            "coastal",
            "near the coast",
            "getaway from",
            "vacation from",
            "holiday from",
            "peaceful",
            "relaxing",
            "romantic",
            "not too",
            "around",
            "new year",
            "christmas",
            "long weekend",
        ]
    
        if any(signal in query for signal in vague_destination_signals):
            return False
    
        if request.confidence < self.confidence_threshold:
            return False
    
        if request.missing_fields:
            return False
    
        return True

    def _analyze_with_gemini(
    self,
    user_query: str,
    spacy_request: TripRequest
) -> Optional:
        if not self.model:
            print("[IntentAnalyzer] Gemini model not initialized. Check GEMINI_API_KEY in .env")
            return None

        prompt = self._build_gemini_prompt(user_query, spacy_request)

        try:
            response = self.model.generate_content(
    prompt,
    generation_config={
        "temperature": 0.1,
        "top_p": 0.8,
        "top_k": 40,
    }
)
            text = response.text.strip()


            json_text = self._extract_json(text)
            data = json.loads(json_text)

            destination_scope = data.get("destination_scope") or SCOPE_UNKNOWN

            if destination_scope not in {SCOPE_CITY, SCOPE_REGION, SCOPE_UNKNOWN}:
                destination_scope = SCOPE_UNKNOWN

            request = TripRequest(
                user_query=user_query,
                source=data.get("source"),
                destination=data.get("destination"),
                month=data.get("month"),
                days=data.get("days"),
                budget=data.get("budget"),
                travelers=data.get("travelers"),
                interests=data.get("interests") or [],
                travel_dates=data.get("travel_dates"),
                suggested_agents=data.get("required_agents") or [],
                missing_fields=data.get("missing_fields") or [],
                confidence=float(data.get("confidence", 0.85)),
                parser_used="gemini",
                destination_scope=destination_scope,
            )

            request.suggested_agents = self._validate_agents(
                request.suggested_agents,
                request
            )

            return request

        except Exception as e:
            print("[IntentAnalyzer] Gemini intent analysis failed:")
            print(type(e).__name__, str(e))
            return None

    def _build_gemini_prompt(self, user_query: str, spacy_request: TripRequest) -> str:
        spacy_json = {
        "source": spacy_request.source,
        "destination": spacy_request.destination,
        "month": spacy_request.month,
        "days": spacy_request.days,
        "budget": spacy_request.budget,
        "travelers": spacy_request.travelers,
        "interests": spacy_request.interests,
        "suggested_agents": spacy_request.suggested_agents,
        "missing_fields": spacy_request.missing_fields,
        "confidence": spacy_request.confidence,
    }

        return f"""
You are a strict JSON intent analyzer for a dynamic multi-agent trip planning system.

Return only valid JSON.
Do not include markdown.
Do not explain anything.
Do not add comments.

Allowed agents:
- destination_agent
- climate_agent
- transport_agent
- hotel_agent
- itinerary_agent
- budget_agent

Your task:
Extract the user's travel intent.

Important interpretation rules:
1. Do not invent a destination if the user has not explicitly provided one.
2. If the user says "somewhere", "near the coast", "mountains", "nature", "peaceful place", "romantic place", or similar preference-based wording, keep destination as null.
3. If destination is null, include destination_agent.
4. Do not include transport_agent unless both source and destination are available.
5. If this is a full trip, vacation, holiday, getaway, or itinerary request, include:
   destination_agent, climate_agent, hotel_agent, itinerary_agent, budget_agent.
6. If both source and destination are available, include transport_agent.
7. If the user gives a date range like "6-7 day trip", set days to the lower number, e.g. 6.
8. If the user says "long weekend", set days to 3.
9. If the user says "weekend", set days to 2.
10. If the user says "week", set days to 7.
11. If the user says "parents and I", set travelers to 3.
12. If the user says "my wife and I", "my husband and I", or "couple", set travelers to 2.
13. If the user says "family" but no number is given, set travelers to 4.
14. If the user says "friends" with a number, use that number.
15. Map Christmas to December.
16. Map New Year to January unless the user clearly says New Year's Eve, then use December.
17. If the user says "after Diwali" and no exact date/year is provided, keep month as null.
18. Budget mapping:
    - "cheap", "budget", "affordable", "not too expensive", "not costly" -> low
    - "luxury", "premium", "5 star", "lavish" -> high
    - "comfortable", "decent", "moderate", "not luxury but not too cheap", "not too cheap", "mid range" -> medium
19. Interests must be simple labels only:
    beach, nature, food, nightlife, heritage, religious, adventure, shopping, relaxation, romantic
20. If a field cannot be inferred confidently, use null.
21. confidence should reflect the final extracted intent, between 0 and 1.
destination_scope is only a rough hint — the destination agent will classify it precisely.
If destination is a broad state/region/country like Rajasthan, Kerala, Himachal, Odisha, South India, North East, India, set destination_scope = "region".
If destination is a specific city/town like Jaipur, Ooty, Goa, Munnar, Udaipur, set destination_scope = "city".
If no destination is provided, set destination_scope = "unknown".
If destination_scope is "region", do not include transport_agent, hotel_agent, or itinerary_agent yet — cities must be chosen first. Include destination_agent and budget_agent.

Example 1:
User: We are 3 friends looking for a relaxing but fun long weekend getaway from Pune sometime around New Year, preferably near the coast, with good food, some nightlife, and not too costly.
Output:
{{
  "source": "Pune",
  "destination": null,
  "month": "January",
  "days": 3,
  "budget": "low",
  "travelers": 3,
  "interests": ["beach", "food", "nightlife", "relaxation"],
  "travel_dates": null,
  "required_agents": ["destination_agent", "climate_agent", "hotel_agent", "itinerary_agent", "budget_agent"],
  "missing_fields": ["destination"],
  "confidence": 0.85,
  "destination_scope": "unknown"
}}

Example 2:
User: My parents and I want a calm 6-7 day trip sometime after Diwali from Hyderabad, preferably somewhere with mountains or nature, comfortable stays, easy travel, not luxury but not too cheap either.
Output:
{{
  "source": "Hyderabad",
  "destination": null,
  "month": null,
  "days": 6,
  "budget": "medium",
  "travelers": 3,
  "interests": ["nature", "relaxation"],
  "travel_dates": null,
  "required_agents": ["destination_agent", "climate_agent", "hotel_agent", "itinerary_agent", "budget_agent"],
  "missing_fields": ["destination", "month"],
  "confidence": 0.85,
  "destination_scope": "unknown"
}}

Now analyze this user query:
{user_query}

spaCy result:
{json.dumps(spacy_json, indent=2)}

Return JSON exactly in this structure:
{{
  "source": null,
  "destination": null,
  "month": null,
  "days": null,
  "budget": null,
  "travelers": null,
  "interests": [],
  "travel_dates": null,
  "required_agents": [],
  "missing_fields": [],
  "confidence": 0.0,
  "destination_scope": "unknown"
}}
"""

    def _extract_json(self, text: str) -> str:
        text = text.strip()

        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()

        elif text.startswith("```"):
            text = text.replace("```", "").strip()

        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1:
            return text[start:end + 1]

        return text

    def _infer_agents(self, request: TripRequest) -> List:
        agents = []

        # Destination agent always runs: it either recommends destinations
        # (when none is given) or fetches attractions for the chosen one.
        agents.append(AGENT_DESTINATION)

        if request.month:
            agents.append(AGENT_CLIMATE)

        if request.source and request.destination:
            agents.append(AGENT_TRANSPORT)

        if request.destination or request.budget:
            agents.append(AGENT_HOTEL)

        if request.destination or request.days:
            agents.append(AGENT_ITINERARY)

        if request.budget or request.days or request.travelers:
            agents.append(AGENT_BUDGET)

        return self._validate_agents(agents, request)

    def _validate_agents(self, agents: List[str], request: TripRequest) -> List:
        requested = set(agents)
        ordered = [agent for agent in AGENT_ORDER if agent in requested]

        if AGENT_TRANSPORT in ordered:
            if not request.source or not request.destination:
                ordered.remove(AGENT_TRANSPORT)

        return ordered

    def _find_missing_fields(self, request: TripRequest) -> List:
        missing = []

        if not request.destination:
            missing.append("destination")

        return missing

    def _score_spacy_result(self, request: TripRequest) -> float:
        score = 0.0

        if request.source:
            score += 0.15

        if request.destination:
            score += 0.25

        if request.month:
            score += 0.15

        if request.days:
            score += 0.10

        if request.travelers:
            score += 0.10

        if request.budget:
            score += 0.10

        if request.interests:
            score += 0.10

        if request.suggested_agents:
            score += 0.05

        return round(min(score, 1.0), 2)

    def _safe_int(self, value: str) -> Optional:
        try:
            return int(value)
        except Exception:
            return None

    def _get_nearby_text(self, doc, start: int, end: int, window: int = 3) -> str:
        left = max(0, start - window)
        right = min(len(doc), end + window)

        return " ".join(token.text.lower() for token in doc[left:right])
```

---

## File: `orchestrator/nodes.py`

```py
from dataclasses import asdict, fields
from typing import Any, Dict

from langgraph.types import interrupt

from config.constants import (
    AGENT_DESTINATION,
    AGENT_CLIMATE,
    AGENT_TRANSPORT,
    AGENT_HOTEL,
    AGENT_ITINERARY,
    AGENT_BUDGET,
    PHASE_INTAKE,
    PHASE_DONE,
)
from schemas.agent_schema import AgentInput, AgentOutput
from schemas.trip_schema import TripRequest, TripState

from orchestrator.intent_analyzer import IntentAnalyzer
from orchestrator.planner_agent import PlannerAgent
from orchestrator.final_response_composer import FinalResponseComposer

from agents_mcp.destination_agent import DestinationAgent
from agents_mcp.climate_agent import ClimateAgent
from agents_mcp.transport_agent import TransportAgent
from agents_mcp.hotel_agent import HotelAgent
from agents_mcp.itinerary_agent import ItineraryAgent
from agents_mcp.budget_agent import BudgetAgent


intent_analyzer = IntentAnalyzer()
planner_agent = PlannerAgent()
final_response_composer = FinalResponseComposer()

AGENT_REGISTRY = {
    AGENT_DESTINATION: DestinationAgent(),
    AGENT_CLIMATE: ClimateAgent(),
    AGENT_TRANSPORT: TransportAgent(),
    AGENT_HOTEL: HotelAgent(),
    AGENT_ITINERARY: ItineraryAgent(),
    AGENT_BUDGET: BudgetAgent(),
}


def _record_result(state: TripState, agent_name: str, result: AgentOutput) -> None:
    agent_results = dict(state.get("agent_results") or {})
    agent_results[agent_name] = asdict(result)
    state["agent_results"] = agent_results

    if not result.success:
        errors = list(state.get("errors") or [])
        errors.append(f"{agent_name}: {result.error}")
        state["errors"] = errors


def _sanitize_request_dict(request_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Remove fields not accepted by TripRequest.

    This prevents Redis memory keys or future extra fields from breaking:
    TripRequest(**request_dict)
    """

    allowed_fields = {field.name for field in fields(TripRequest)}

    return {
        key: value
        for key, value in (request_dict or {}).items()
        if key in allowed_fields
    }


def _request_from_state(state: TripState) -> TripRequest:
    request_dict = dict(state.get("request") or {})
    sanitized_request = _sanitize_request_dict(request_dict)
    state["request"] = sanitized_request

    return TripRequest(**sanitized_request)


def _base_agent_input(
    request: TripRequest,
    destination: Any = None,
    context: Dict[str, Any] = None,
) -> AgentInput:
    return AgentInput(
        query=request.user_query,
        source=request.source,
        destination=destination if destination is not None else request.destination,
        month=request.month,
        days=request.days,
        budget=request.budget,
        travelers=request.travelers,
        interests=request.interests,
        context=context or {},
    )


# ---------------------------------------------------------------------- #
# Intake
# ---------------------------------------------------------------------- #

def intake_node(state: TripState) -> TripState:
    """
    Parse raw query only when request was not already seeded by TripOrchestrator.

    Important for Redis memory:
    - TripOrchestrator loads Redis memory.
    - TripOrchestrator merges memory into request.
    - This node must not overwrite state["request"] when it already exists.
    """

    if not state.get("request"):
        parsed_request = asdict(
            intent_analyzer.analyze(state.get("raw_user_query", ""))
        )
        state["request"] = _sanitize_request_dict(parsed_request)
    else:
        state["request"] = _sanitize_request_dict(state.get("request") or {})

    state["trip_memory"] = state.get("trip_memory") or {}
    state["conversation_history"] = state.get("conversation_history") or []

    state["agent_results"] = {}
    state["errors"] = []

    state["phase"] = PHASE_INTAKE
    state["pending_clarification"] = None
    state["clarification_answers"] = {}
    state["asked_clarifications"] = []
    state["planned_agents"] = []

    state["destination_resolved"] = False
    state["selected_cities"] = []
    state["city_recommendations"] = []
    state["city_attractions"] = {}

    state["travel_sequence"] = None
    state["feasible"] = None

    state["replan_count"] = 0
    state["replan_directives"] = []

    state["final_response"] = None
    state["done"] = False

    return state


# ---------------------------------------------------------------------- #
# Planner
# ---------------------------------------------------------------------- #

def planner_node(state: TripState) -> TripState:
    next_node = planner_agent.decide_next(state)
    state["next_node"] = next_node
    state["phase"] = planner_agent.phase_for_node(next_node)

    return state


# ---------------------------------------------------------------------- #
# Clarification
# ---------------------------------------------------------------------- #

def clarify_node(state: TripState) -> TripState:
    clarification = planner_agent.build_clarification(state)
    state["pending_clarification"] = asdict(clarification)

    answer = interrupt(state["pending_clarification"])

    planner_agent.merge_clarification_answer(state, clarification, answer)

    if not state.get("destination_resolved"):
        _reparse_request_after_clarification(state)

    return state


def city_selection_node(state: TripState) -> TripState:
    clarification = planner_agent.build_city_selection(state)
    state["pending_clarification"] = asdict(clarification)

    answer = interrupt(state["pending_clarification"])

    planner_agent.merge_clarification_answer(state, clarification, answer)

    return state


def _reparse_request_after_clarification(state: TripState) -> None:
    """
    Free-text clarification answers may append raw text to the query.
    Re-run parser and fill only missing structured fields.

    This function does not erase Redis-merged fields.
    It only fills missing values from the reparsed query.
    """

    request_dict = dict(state.get("request") or {})
    query = request_dict.get("user_query") or state.get("raw_user_query", "")

    reparsed = asdict(intent_analyzer.analyze(query))
    reparsed = _sanitize_request_dict(reparsed)

    for field_name in (
        "source",
        "destination",
        "month",
        "days",
        "budget",
        "travelers",
        "interests",
        "destination_scope",
    ):
        if not request_dict.get(field_name) and reparsed.get(field_name):
            request_dict[field_name] = reparsed[field_name]

    state["request"] = _sanitize_request_dict(request_dict)

    agent_results = dict(state.get("agent_results") or {})

    if (
        AGENT_DESTINATION in agent_results
        and not agent_results[AGENT_DESTINATION].get("success")
    ):
        agent_results.pop(AGENT_DESTINATION, None)
        state["agent_results"] = agent_results


# ---------------------------------------------------------------------- #
# Destination
# ---------------------------------------------------------------------- #

def destination_node(state: TripState) -> TripState:
    request = _request_from_state(state)
    agent_input = _base_agent_input(request)

    result = AGENT_REGISTRY[AGENT_DESTINATION].run(agent_input)
    _record_result(state, AGENT_DESTINATION, result)

    if not result.success:
        return state

    mode = result.data.get("mode")

    if mode == "scope_resolved":
        state["selected_cities"] = result.data.get("resolved_cities", [])
        state["destination_resolved"] = True

    elif mode == "city_recommendation":
        state["city_recommendations"] = result.data.get("city_recommendations", [])
        state["destination_resolved"] = True

    elif mode == "destination_recommendation":
        recommended = result.data.get("recommended_destinations") or {}
        state["city_recommendations"] = recommended.get("recommendations", [])
        state["destination_resolved"] = True

    return state


# ---------------------------------------------------------------------- #
# Attractions
# ---------------------------------------------------------------------- #

def attractions_node(state: TripState) -> TripState:
    request = _request_from_state(state)
    city_attractions = dict(state.get("city_attractions") or {})
    selected_cities = state.get("selected_cities") or []

    for city in selected_cities:
        if city in city_attractions:
            continue

        agent_input = _base_agent_input(
            request,
            destination=city,
            context={
                "destination_mode": "fetch_attractions",
                "target_city": city,
            },
        )

        result = AGENT_REGISTRY[AGENT_DESTINATION].run(agent_input)

        if result.success:
            city_attractions[city] = result.data
        else:
            city_attractions[city] = {
                "ranked_places": [],
                "places": [],
                "error": result.error,
            }

            errors = list(state.get("errors") or [])
            errors.append(f"attractions:{city}: {result.error}")
            state["errors"] = errors

    state["city_attractions"] = city_attractions

    return state


# ---------------------------------------------------------------------- #
# Climate / Hotel helper
# ---------------------------------------------------------------------- #

def _run_per_city(state: TripState, agent_name: str, extra_context_fn) -> TripState:
    request = _request_from_state(state)

    selected_cities = state.get("selected_cities") or (
        [request.destination] if request.destination else []
    )

    per_city: Dict[str, Any] = {}
    overall_success = True

    for city in selected_cities:
        agent_input = _base_agent_input(
            request,
            destination=city,
            context=extra_context_fn(request),
        )

        result = AGENT_REGISTRY[agent_name].run(agent_input)
        per_city[city] = asdict(result)

        if not result.success:
            overall_success = False

    output = AgentOutput(
        agent_name=agent_name,
        success=overall_success,
        data={"by_city": per_city},
        message=(
            f"{agent_name} data fetched for all cities."
            if overall_success
            else f"{agent_name} failed for one or more cities."
        ),
        error=None if overall_success else "One or more cities failed.",
    )

    _record_result(state, agent_name, output)

    return state


def climate_node(state: TripState) -> TripState:
    return _run_per_city(
        state,
        AGENT_CLIMATE,
        lambda request: {"travel_dates": request.travel_dates},
    )


def hotel_node(state: TripState) -> TripState:
    return _run_per_city(
        state,
        AGENT_HOTEL,
        lambda request: {},
    )


# ---------------------------------------------------------------------- #
# Transport
# ---------------------------------------------------------------------- #

def transport_node(state: TripState) -> TripState:
    request = _request_from_state(state)

    agent_input = _base_agent_input(
        request,
        context={
            "city_attractions": state.get("city_attractions") or {},
            "selected_cities": state.get("selected_cities") or [],
        },
    )

    result = AGENT_REGISTRY[AGENT_TRANSPORT].run(agent_input)
    _record_result(state, AGENT_TRANSPORT, result)

    if result.success:
        state["travel_sequence"] = result.data

    return state


# ---------------------------------------------------------------------- #
# Budget
# ---------------------------------------------------------------------- #

def budget_node(state: TripState) -> TripState:
    request = _request_from_state(state)

    transport_result = (state.get("agent_results") or {}).get(AGENT_TRANSPORT) or {}
    inter_city_legs = (transport_result.get("data") or {}).get("inter_city_legs") or []

    agent_input = _base_agent_input(
        request,
        context={
            "selected_cities": state.get("selected_cities") or [],
            "inter_city_legs": inter_city_legs,
        },
    )

    result = AGENT_REGISTRY[AGENT_BUDGET].run(agent_input)
    _record_result(state, AGENT_BUDGET, result)

    if result.success:
        state["feasible"] = result.data.get("feasible")

    return state


# ---------------------------------------------------------------------- #
# Itinerary
# ---------------------------------------------------------------------- #

def itinerary_node(state: TripState) -> TripState:
    request = _request_from_state(state)

    agent_input = _base_agent_input(
        request,
        context={
            "selected_cities": state.get("selected_cities") or [],
            "city_attractions": state.get("city_attractions") or {},
        },
    )

    result = AGENT_REGISTRY[AGENT_ITINERARY].run(agent_input)
    _record_result(state, AGENT_ITINERARY, result)

    return state


# ---------------------------------------------------------------------- #
# Replan
# ---------------------------------------------------------------------- #

def replan_node(state: TripState) -> TripState:
    planner_agent.apply_replan_directive(state)
    return state


# ---------------------------------------------------------------------- #
# Compose
# ---------------------------------------------------------------------- #

def compose_node(state: TripState) -> TripState:
    state["final_response"] = final_response_composer.compose(state)
    state["done"] = True
    state["phase"] = PHASE_DONE

    return state


NODE_FUNCTIONS = {
    AGENT_DESTINATION: destination_node,
    AGENT_CLIMATE: climate_node,
    AGENT_TRANSPORT: transport_node,
    AGENT_HOTEL: hotel_node,
    AGENT_ITINERARY: itinerary_node,
    AGENT_BUDGET: budget_node,
}
```

---

## File: `orchestrator/planner_agent.py`

```py
from typing import Any, Callable, Dict, List, Optional

from config.constants import (
    AGENT_DESTINATION,
    AGENT_BUDGET,
    NODE_CLARIFY,
    NODE_CITY_SELECTION,
    NODE_ATTRACTIONS,
    NODE_REPLAN,
    NODE_COMPOSE,
    PHASE_CLARIFY,
    PHASE_RESOLVE_DESTINATION,
    PHASE_SELECT_CITIES,
    PHASE_PLAN,
    PHASE_REPLAN,
    PHASE_COMPOSE,
    MAX_AUTO_REPLANS,
)
from schemas.clarification_schema import (
    ClarificationOption,
    ClarificationQuestion,
    ClarificationRequest,
    KIND_FREE_TEXT,
    KIND_MULTI_SELECT,
    KIND_SINGLE_SELECT,
)
from schemas.trip_schema import TripRequest, TripState
from orchestrator.workflow_planner import WorkflowPlanner


class ClarificationRule:
    """One extensible clarification case.

    ``applies(state)`` decides whether this case is currently relevant;
    ``build(state)`` produces the question to ask. Register new cases by
    appending a ``ClarificationRule`` to ``PlannerAgent.clarification_rules``
    — no other part of the workflow needs to change.
    """

    def __init__(
        self,
        rule_id: str,
        applies: Callable[[TripState], bool],
        build: Callable[[TripState], ClarificationQuestion],
    ):
        self.rule_id = rule_id
        self.applies = applies
        self.build = build


class PlannerAgent:
    """The single orchestrator brain.

    Every workflow decision — what to run next, whether clarification is
    needed, how to recover from an infeasible plan — is made here.
    LangGraph's nodes only carry out what this class decides; the graph's
    conditional edge just reads ``state["next_node"]``, a value this class
    computed.

    Agents never communicate with each other directly: everything this class
    reads comes from ``TripState``, and everything it decides is written
    back into ``TripState`` for the next node to read.
    """

    def __init__(self):
        self.workflow_planner = WorkflowPlanner()
        self.clarification_rules: List[ClarificationRule] = self._default_clarification_rules()

    # ------------------------------------------------------------------ #
    # Routing — the only place next-step workflow decisions are made
    # ------------------------------------------------------------------ #

    def decide_next(self, state: TripState) -> str:
        if not state.get("destination_resolved"):
            if self._destination_failed(state):
                return NODE_CLARIFY

            return AGENT_DESTINATION

        if state.get("city_recommendations") and not state.get("selected_cities"):
            return NODE_CITY_SELECTION

        if self._next_clarification_rule(state) is not None:
            return NODE_CLARIFY

        if self._missing_attraction_cities(state):
            return NODE_ATTRACTIONS

        # Only lock in the agent set once every clarification rule (including
        # ``missing_source_for_transport``) has already been resolved — doing
        # this any earlier would permanently exclude an agent (e.g. transport)
        # whose eligibility depends on a field the user hasn't supplied yet.
        self.ensure_planned_agents(state)

        planned_agents = state.get("planned_agents") or []
        agent_results = state.get("agent_results") or {}

        for agent_name in planned_agents:
            if agent_name == AGENT_DESTINATION:
                continue

            if agent_name not in agent_results:
                return agent_name

        if (
            state.get("feasible") is False
            and state.get("replan_count", 0) < MAX_AUTO_REPLANS
        ):
            return NODE_REPLAN

        return NODE_COMPOSE

    def phase_for_node(self, node_name: str) -> str:
        return {
            NODE_CLARIFY: PHASE_CLARIFY,
            NODE_CITY_SELECTION: PHASE_SELECT_CITIES,
            AGENT_DESTINATION: PHASE_RESOLVE_DESTINATION,
            NODE_REPLAN: PHASE_REPLAN,
            NODE_COMPOSE: PHASE_COMPOSE,
        }.get(node_name, PHASE_PLAN)

    def _destination_failed(self, state: TripState) -> bool:
        result = (state.get("agent_results") or {}).get(AGENT_DESTINATION)
        return bool(result and not result.get("success"))

    def _missing_attraction_cities(self, state: TripState) -> List[str]:
        selected_cities = state.get("selected_cities") or []
        city_attractions = state.get("city_attractions") or {}

        return [city for city in selected_cities if city not in city_attractions]

    # ------------------------------------------------------------------ #
    # Agent-set planning (invoked once, right after destination resolves)
    # ------------------------------------------------------------------ #

    def ensure_planned_agents(self, state: TripState) -> None:
        if state.get("planned_agents"):
            return

        request = self._request_from_state(state)
        state["planned_agents"] = self.workflow_planner.plan(request)

    # ------------------------------------------------------------------ #
    # Clarification — generic, rule-driven, extensible
    # ------------------------------------------------------------------ #

    def build_clarification(self, state: TripState) -> ClarificationRequest:
        rule = self._next_clarification_rule(state)

        if rule is None:
            return ClarificationRequest(
                reason="More information is needed before planning can continue.",
                questions=[
                    ClarificationQuestion(
                        id="general",
                        question="Could you share a bit more about what you're looking for in this trip?",
                        kind=KIND_FREE_TEXT,
                    )
                ],
                origin="clarify",
            )

        return ClarificationRequest(
            reason=f"Clarification needed: {rule.rule_id}",
            questions=[rule.build(state)],
            origin="clarify",
        )

    def build_city_selection(self, state: TripState) -> ClarificationRequest:
        recommendations = state.get("city_recommendations") or []

        options = [
            ClarificationOption(
                id=item.get("destination"),
                label=item.get("destination") or "Unknown",
                description=item.get("reason"),
                data=item,
            )
            for item in recommendations
            if item.get("destination")
        ]

        return ClarificationRequest(
            reason="Choose one or more destinations/cities to continue planning.",
            questions=[
                ClarificationQuestion(
                    id="select_cities",
                    question="Which of these would you like to visit?",
                    kind=KIND_MULTI_SELECT,
                    options=options,
                    fills_field=None,
                )
            ],
            origin="city_selection",
        )

    def merge_clarification_answer(
        self,
        state: TripState,
        clarification: ClarificationRequest,
        answer: Any,
    ) -> None:
        for question in clarification.questions:
            value = answer.get(question.id) if isinstance(answer, dict) else answer

            if clarification.origin == "city_selection" and question.id == "select_cities":
                cities = self._resolve_selected_cities(question, value)

                if cities:
                    state["selected_cities"] = cities

                continue

            coerced = self._coerce_answer(question, value)

            if question.fills_field:
                request = state.get("request") or {}
                request[question.fills_field] = coerced
                state["request"] = request
            else:
                self._apply_free_text_answer(state, coerced)

        asked = state.get("asked_clarifications") or []

        for question in clarification.questions:
            rule_id = question.id

            if rule_id not in asked:
                asked.append(rule_id)

        state["asked_clarifications"] = asked
        state["pending_clarification"] = None

    def _resolve_selected_cities(self, question: ClarificationQuestion, value: Any) -> List[str]:
        if isinstance(value, list):
            valid_ids = {option.id for option in question.options}
            cities = [item for item in value if item in valid_ids]

            if cities:
                return cities

        if isinstance(value, str) and value.strip():
            return self._match_options_from_text(value, question.options)

        return []

    def _match_options_from_text(self, text: str, options: List[ClarificationOption]) -> List[str]:
        lowered = text.lower()

        if lowered.strip() in {"all", "all of them", "both", "everything"}:
            return [option.id for option in options]

        matched = [
            option.id
            for option in options
            if option.label and option.label.lower() in lowered
        ]

        return matched

    def _coerce_answer(self, question: ClarificationQuestion, value: Any) -> Any:
        if value is None:
            return None

        if question.kind == KIND_MULTI_SELECT:
            if isinstance(value, list):
                return value

            return self._match_options_from_text(str(value), question.options)

        if question.kind == KIND_SINGLE_SELECT:
            if isinstance(value, str):
                for option in question.options:
                    if option.label.lower() == value.strip().lower() or option.id == value:
                        return option.id

            return value

        if question.fills_field == "days" or question.fills_field == "travelers":
            return self._safe_int(value)

        return value

    def _apply_free_text_answer(self, state: TripState, text: Any) -> None:
        if not text:
            return

        request = state.get("request") or {}
        combined_query = f"{request.get('user_query', '')}. {text}".strip(". ")
        request["user_query"] = combined_query
        state["request"] = request
        state["raw_user_query"] = combined_query

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        if isinstance(value, int):
            return value

        try:
            digits = "".join(char for char in str(value) if char.isdigit())
            return int(digits) if digits else None
        except (TypeError, ValueError):
            return None

    def _next_clarification_rule(self, state: TripState) -> Optional[ClarificationRule]:
        asked = set(state.get("asked_clarifications") or [])

        for rule in self.clarification_rules:
            if rule.rule_id in asked:
                continue

            if rule.applies(state):
                return rule

        return None

    def _default_clarification_rules(self) -> List[ClarificationRule]:
        def request_of(state: TripState) -> Dict[str, Any]:
            return state.get("request") or {}

        return [
            ClarificationRule(
                rule_id="missing_days",
                applies=lambda state: not request_of(state).get("days"),
                build=lambda state: ClarificationQuestion(
                    id="missing_days",
                    question="How many days do you have for this trip?",
                    kind=KIND_FREE_TEXT,
                    fills_field="days",
                ),
            ),
            ClarificationRule(
                rule_id="missing_budget",
                applies=lambda state: bool(state.get("destination_resolved")) and not request_of(state).get("budget"),
                build=lambda state: ClarificationQuestion(
                    id="missing_budget",
                    question="What budget range do you prefer?",
                    kind=KIND_SINGLE_SELECT,
                    options=[
                        ClarificationOption(id="low", label="low"),
                        ClarificationOption(id="medium", label="medium"),
                        ClarificationOption(id="high", label="high"),
                    ],
                    fills_field="budget",
                ),
            ),
            ClarificationRule(
                rule_id="missing_source_for_transport",
                applies=lambda state: (
                    len(state.get("selected_cities") or []) >= 1
                    and not request_of(state).get("source")
                ),
                build=lambda state: ClarificationQuestion(
                    id="missing_source_for_transport",
                    question="Which city will you be traveling from?",
                    kind=KIND_FREE_TEXT,
                    fills_field="source",
                ),
            ),
            ClarificationRule(
                rule_id="destination_city",
                applies=lambda state: (
                    not state.get("destination_resolved")
                    and request_of(state).get("destination")
                    and bool(
                        (state.get("agent_results") or {}).get(AGENT_DESTINATION)
                        and not (state.get("agent_results") or {}).get(AGENT_DESTINATION, {}).get("success")
                    )
                ),
                build=lambda state: ClarificationQuestion(
                    id="destination_city",
                    question=(
                        f"I couldn't resolve '{request_of(state).get('destination')}' into a valid destination. "
                        "Which city would you like to visit instead?"
                    ),
                    kind=KIND_FREE_TEXT,
                    fills_field="destination",
                ),
            ),
            ClarificationRule(
                rule_id="ambiguous_request",
                applies=lambda state: float(request_of(state).get("confidence") or 1.0) < 0.45,
                build=lambda state: ClarificationQuestion(
                    id="ambiguous_request",
                    question=(
                        "I want to get this right — could you tell me a bit more about your trip "
                        "(where from, roughly how long, and what you're looking for)?"
                    ),
                    kind=KIND_FREE_TEXT,
                    fills_field=None,
                ),
            ),
        ]

    # ------------------------------------------------------------------ #
    # Replanning
    # ------------------------------------------------------------------ #

    def apply_replan_directive(self, state: TripState) -> str:
        selected_cities = state.get("selected_cities") or []
        agent_results = dict(state.get("agent_results") or {})
        city_attractions = dict(state.get("city_attractions") or {})

        if len(selected_cities) > 1:
            directive = f"dropped_lowest_priority_city:{selected_cities[-1]}"
            dropped_city = selected_cities[-1]

            state["selected_cities"] = selected_cities[:-1]
            city_attractions.pop(dropped_city, None)
            state["city_attractions"] = city_attractions

            for agent_name in ("transport_agent", "itinerary_agent", "budget_agent"):
                agent_results.pop(agent_name, None)
        else:
            request = state.get("request") or {}
            current_days = request.get("days") or 3
            request["days"] = current_days + 2
            state["request"] = request
            directive = f"extended_days_to:{request['days']}"

            for agent_name in ("itinerary_agent", "budget_agent"):
                agent_results.pop(agent_name, None)

        state["agent_results"] = agent_results
        state["feasible"] = None
        state["replan_count"] = state.get("replan_count", 0) + 1

        directives = state.get("replan_directives") or []
        directives.append(directive)
        state["replan_directives"] = directives

        return directive

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _request_from_state(self, state: TripState) -> TripRequest:
        return TripRequest(**(state.get("request") or {"user_query": state.get("raw_user_query", "")}))

```

---

## File: `orchestrator/state_manager.py`

```py
from typing import List, Optional

from schemas.trip_schema import TripRequest


class StateManager:
    """Detects cross-turn changes between a previous, completed trip request
    and a newly parsed one, and merges them into a single request for the
    planner to act on.

    This is turn-to-turn continuity (e.g. "actually make it 5 days instead")
    across separate planning runs — distinct from same-run automatic
    replanning, which ``PlannerAgent.apply_replan_directive`` handles when
    ``BudgetAgent`` reports infeasibility mid-plan.
    """

    COMPARABLE_FIELDS = [
        "source",
        "destination",
        "month",
        "days",
        "budget",
        "travelers",
        "travel_dates",
    ]

    def is_replan_candidate(
        self,
        current_request: TripRequest,
        previous_request: Optional[TripRequest],
    ) -> bool:
        if not previous_request:
            return False

        return bool(self.detect_modified_fields(previous_request, current_request))

    def detect_modified_fields(
        self,
        previous_request: TripRequest,
        current_request: TripRequest,
    ) -> List[str]:
        modified_fields = []

        for field_name in self.COMPARABLE_FIELDS:
            current_value = getattr(current_request, field_name)
            previous_value = getattr(previous_request, field_name)

            if current_value is not None and current_value != previous_value:
                modified_fields.append(field_name)

        if current_request.interests:
            previous_interests = sorted(previous_request.interests or [])
            current_interests = sorted(current_request.interests or [])

            if current_interests != previous_interests:
                modified_fields.append("interests")

        return modified_fields

    def merge_replan_request(
        self,
        previous_request: TripRequest,
        current_request: TripRequest,
    ) -> TripRequest:
        modified_fields = self.detect_modified_fields(previous_request, current_request)

        return TripRequest(
            user_query=current_request.user_query,
            source=current_request.source or previous_request.source,
            destination=current_request.destination or previous_request.destination,
            month=current_request.month or previous_request.month,
            days=current_request.days or previous_request.days,
            budget=current_request.budget or previous_request.budget,
            travelers=current_request.travelers or previous_request.travelers,
            interests=current_request.interests or previous_request.interests,
            travel_dates=current_request.travel_dates or previous_request.travel_dates,
            suggested_agents=[],
            missing_fields=[],
            confidence=max(current_request.confidence, previous_request.confidence),
            parser_used=f"replan_from_{current_request.parser_used}",
            turn_type="continuation",
            modified_fields=modified_fields,
            destination_scope=(
                current_request.destination_scope
                if "destination" in modified_fields
                else previous_request.destination_scope
            ),
        )

```

---

## File: `orchestrator/trip_graph.py`

```py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from config.constants import (
    AGENT_DESTINATION,
    AGENT_CLIMATE,
    AGENT_TRANSPORT,
    AGENT_HOTEL,
    AGENT_ITINERARY,
    AGENT_BUDGET,
    NODE_INTAKE,
    NODE_PLANNER,
    NODE_CLARIFY,
    NODE_CITY_SELECTION,
    NODE_ATTRACTIONS,
    NODE_REPLAN,
    NODE_COMPOSE,
)
from schemas.trip_schema import TripState
from orchestrator import nodes


# Every node LangGraph can route to from ``planner`` — the conditional edge
# map is the identity function because ``PlannerAgent.decide_next`` returns
# the literal node name it wants executed next. LangGraph only coordinates
# execution here; the planner made the actual decision.
_ROUTABLE_NODES = [
    NODE_CLARIFY,
    NODE_CITY_SELECTION,
    NODE_ATTRACTIONS,
    AGENT_DESTINATION,
    AGENT_CLIMATE,
    AGENT_TRANSPORT,
    AGENT_HOTEL,
    AGENT_ITINERARY,
    AGENT_BUDGET,
    NODE_REPLAN,
    NODE_COMPOSE,
]


def build_trip_graph():
    graph = StateGraph(TripState)

    graph.add_node(NODE_INTAKE, nodes.intake_node)
    graph.add_node(NODE_PLANNER, nodes.planner_node)
    graph.add_node(NODE_CLARIFY, nodes.clarify_node)
    graph.add_node(NODE_CITY_SELECTION, nodes.city_selection_node)
    graph.add_node(NODE_ATTRACTIONS, nodes.attractions_node)
    graph.add_node(AGENT_DESTINATION, nodes.destination_node)
    graph.add_node(AGENT_CLIMATE, nodes.climate_node)
    graph.add_node(AGENT_TRANSPORT, nodes.transport_node)
    graph.add_node(AGENT_HOTEL, nodes.hotel_node)
    graph.add_node(AGENT_ITINERARY, nodes.itinerary_node)
    graph.add_node(AGENT_BUDGET, nodes.budget_node)
    graph.add_node(NODE_REPLAN, nodes.replan_node)
    graph.add_node(NODE_COMPOSE, nodes.compose_node)

    graph.set_entry_point(NODE_INTAKE)
    graph.add_edge(NODE_INTAKE, NODE_PLANNER)

    graph.add_conditional_edges(
        NODE_PLANNER,
        lambda state: state["next_node"],
        {name: name for name in _ROUTABLE_NODES},
    )

    for worker_node in (
        NODE_CLARIFY,
        NODE_CITY_SELECTION,
        NODE_ATTRACTIONS,
        AGENT_DESTINATION,
        AGENT_CLIMATE,
        AGENT_TRANSPORT,
        AGENT_HOTEL,
        AGENT_ITINERARY,
        AGENT_BUDGET,
        NODE_REPLAN,
    ):
        graph.add_edge(worker_node, NODE_PLANNER)

    graph.add_edge(NODE_COMPOSE, END)

    return graph.compile(checkpointer=MemorySaver())


trip_graph = build_trip_graph()

```

---

## File: `orchestrator/trip_orchestrator.py`

```py
import uuid
from dataclasses import asdict, fields
from typing import Any, Dict, Optional

from langgraph.types import Command

from memory.redis_trip_memory import RedisTripMemory
from orchestrator.intent_analyzer import IntentAnalyzer
from orchestrator.state_manager import StateManager
from orchestrator.trip_graph import trip_graph
from schemas.trip_schema import TripRequest


class TripOrchestrator:
    """
    Public facade over the compiled trip-planning graph.

    app_mcp.py only calls run() on this class; it never touches LangGraph directly.

    Memory design:
    - Redis is used only at orchestrator level.
    - Agents do not directly read/write Redis.
    - Redis memory is loaded into TripState as trip_memory.
    - Current parsed request overrides Redis memory.
    - Redis memory fills missing fields for follow-up queries.
    """

    def __init__(self):
        self.graph = trip_graph
        self.intent_analyzer = IntentAnalyzer()
        self.state_manager = StateManager()
        self.memory_store = RedisTripMemory()

        self.thread_id = str(uuid.uuid4())
        self.last_completed_request: Optional[TripRequest] = None
        self.pending_clarification: Optional[Dict[str, Any]] = None

    def run(
        self,
        user_query: Optional[str] = None,
        answer: Any = None,
        debug: bool = False,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Advance the workflow by one turn.

        Pass user_query for a normal chat message.
        Pass answer for structured clarification replies.

        session_id is used for Redis short-term memory.
        """

        trip_memory = self.memory_store.load(session_id)

        if self._is_paused():
            resume_value = answer if answer is not None else user_query
            result = self._invoke(Command(resume=resume_value))
        else:
            result = self._start_new_plan(
                user_query=user_query or "",
                trip_memory=trip_memory,
            )

        response = self._build_response(result, debug=debug)

        self._persist_memory_if_needed(
            session_id=session_id,
            result=result,
            response=response,
            user_query=user_query,
            answer=answer,
        )

        return response

    # ------------------------------------------------------------------ #
    # Graph invocation
    # ------------------------------------------------------------------ #

    def _config(self) -> Dict[str, Any]:
        return {"configurable": {"thread_id": self.thread_id}}

    def _is_paused(self) -> bool:
        snapshot = self.graph.get_state(self._config())
        return bool(snapshot.next)

    def _sanitize_request_dict(self, request_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove fields not accepted by TripRequest.

        This prevents Redis memory keys like travel_style from breaking:
        TripRequest(**request_dict)
        """

        allowed_fields = {field.name for field in fields(TripRequest)}

        return {
            key: value
            for key, value in (request_dict or {}).items()
            if key in allowed_fields
        }

    def _start_new_plan(
        self,
        user_query: str,
        trip_memory: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Start a new planning turn.

        Steps:
        1. Parse current query.
        2. Apply existing in-process replan merge.
        3. Merge Redis memory into request.
        4. Sanitize request for TripRequest schema.
        5. Start LangGraph from a fresh thread.
        """

        self.thread_id = str(uuid.uuid4())
        self.pending_clarification = None

        parsed_request = self.intent_analyzer.analyze(user_query)

        if self.state_manager.is_replan_candidate(
            current_request=parsed_request,
            previous_request=self.last_completed_request,
        ):
            parsed_request = self.state_manager.merge_replan_request(
                previous_request=self.last_completed_request,
                current_request=parsed_request,
            )

        current_request_dict = self._sanitize_request_dict(asdict(parsed_request))

        merged_request_dict = self.memory_store.merge_memory_into_request(
            memory=trip_memory,
            current_request=current_request_dict,
        )

        merged_request_dict = self._sanitize_request_dict(merged_request_dict)

        initial_state = {
            "raw_user_query": user_query,
            "request": merged_request_dict,
            "trip_memory": trip_memory,
            "conversation_history": trip_memory.get("conversation_history", []),
        }

        return self._invoke(initial_state)

    def _invoke(self, payload: Any) -> Dict[str, Any]:
        result = self.graph.invoke(payload, self._config())
        interrupts = result.get("__interrupt__")

        # A node's writes just before interrupt() are not visible in result.
        # Clarification payload must be read from Interrupt.value.
        self.pending_clarification = interrupts[0].value if interrupts else None

        return result

    # ------------------------------------------------------------------ #
    # Memory persistence
    # ------------------------------------------------------------------ #

    def _persist_memory_if_needed(
        self,
        session_id: Optional[str],
        result: Dict[str, Any],
        response: Dict[str, Any],
        user_query: Optional[str],
        answer: Any,
    ) -> None:
        """
        Save Redis short-term memory only when a turn reaches a final response.

        Do not update final trip memory during clarification pause,
        because the graph state is not complete yet.
        """

        if not session_id:
            return

        if response.get("awaiting_clarification"):
            if user_query:
                self.memory_store.append_turn(
                    session_id=session_id,
                    role="user",
                    content=user_query,
                )
            return

        final_response_text = response.get("response")

        self.memory_store.update_from_state(
            session_id=session_id,
            state=result,
            final_response=final_response_text,
        )

        if user_query:
            self.memory_store.append_turn(
                session_id=session_id,
                role="user",
                content=user_query,
            )

        if answer is not None and not user_query:
            self.memory_store.append_turn(
                session_id=session_id,
                role="user",
                content=str(answer),
            )

        if final_response_text:
            self.memory_store.append_turn(
                session_id=session_id,
                role="assistant",
                content=final_response_text,
            )

    # ------------------------------------------------------------------ #
    # Response shaping
    # ------------------------------------------------------------------ #

    def _build_response(self, result: Dict[str, Any], debug: bool) -> Dict[str, Any]:
        if self.pending_clarification is not None:
            return self._build_clarification_response(debug=debug)

        return self._build_final_response(result, debug=debug)

    def _build_clarification_response(self, debug: bool) -> Dict[str, Any]:
        snapshot_values = self.graph.get_state(self._config()).values

        response = {
            "success": True,
            "awaiting_clarification": True,
            "clarification": self.pending_clarification,
            "request": snapshot_values.get("request"),
        }

        if debug:
            response["debug_state"] = snapshot_values

        return response

    def _build_final_response(self, result: Dict[str, Any], debug: bool) -> Dict[str, Any]:
        request = self._sanitize_request_dict(result.get("request") or {})
        final_response = result.get("final_response") or {}

        if result.get("done") and request:
            self.last_completed_request = TripRequest(**request)

        response = {
            "success": final_response.get("success", False),
            "response": final_response.get("response"),
            "error": final_response.get("error"),
            "awaiting_clarification": False,
            "request": {
                "source": request.get("source"),
                "destination": request.get("destination"),
                "month": request.get("month"),
                "days": request.get("days"),
                "budget": request.get("budget"),
                "travelers": request.get("travelers"),
                "interests": request.get("interests"),
                "parser_used": request.get("parser_used"),
                "turn_type": request.get("turn_type"),
                "modified_fields": request.get("modified_fields"),
            },
            "workflow": {
                "planned_agents": result.get("planned_agents", []),
                "completed_agents": self._completed_agents(result),
                "failed_agents": self._failed_agents(result),
                "replan_count": result.get("replan_count", 0),
                "replan_directives": result.get("replan_directives", []),
            },
            "agent_results": result.get("agent_results", {}),
            "summary": {
                "selected_cities": result.get("selected_cities", []),
                "city_recommendations": result.get("city_recommendations", []),
                "travel_sequence": result.get("travel_sequence"),
                "feasible": result.get("feasible"),
                "errors": result.get("errors", []),
            },
        }

        if debug:
            response["debug_state"] = result

        return response

    def _completed_agents(self, result: Dict[str, Any]) -> list:
        agent_results = result.get("agent_results") or {}

        return [
            name
            for name, agent_result in agent_results.items()
            if agent_result.get("success")
        ]

    def _failed_agents(self, result: Dict[str, Any]) -> list:
        agent_results = result.get("agent_results") or {}

        return [
            {
                "agent": name,
                "error": agent_result.get("error"),
            }
            for name, agent_result in agent_results.items()
            if not agent_result.get("success")
        ]
```

---

## File: `orchestrator/workflow_planner.py`

```py
from typing import List

from config.constants import (
    AGENT_DESTINATION,
    AGENT_CLIMATE,
    AGENT_TRANSPORT,
    AGENT_HOTEL,
    AGENT_ITINERARY,
    AGENT_BUDGET,
    AGENT_ORDER,
)
from schemas.trip_schema import TripRequest


class WorkflowPlanner:
    """Decides which agents (beyond destination resolution, which the graph
    always runs first) are needed for a resolved trip request.

    Destination scope/hierarchy is handled structurally by the graph
    (destination -> city_selection -> attractions nodes), so this planner no
    longer branches on ``destination_scope`` — by the time it runs, the
    destination has already been resolved to one or more concrete cities.
    """

    def plan(self, request: TripRequest) -> List[str]:
        if request.suggested_agents:
            return self._validate_and_order_agents(request.suggested_agents, request)

        return self._fallback_workflow(request)

    def _validate_and_order_agents(
        self,
        agents: List[str],
        request: TripRequest,
    ) -> List[str]:
        requested = set(agents)

        # ``request.source`` is authoritative for transport eligibility, even
        # though ``agents`` (e.g. Gemini's ``suggested_agents``) may have been
        # computed before a clarification answer supplied the source — this
        # planning step only ever runs once the missing_source_for_transport
        # clarification rule has already been resolved, so trust the field.
        if request.source:
            requested.add(AGENT_TRANSPORT)
        else:
            requested.discard(AGENT_TRANSPORT)

        ordered = [agent for agent in AGENT_ORDER if agent in requested]

        if AGENT_DESTINATION not in ordered:
            ordered.insert(0, AGENT_DESTINATION)

        return ordered

    def _fallback_workflow(self, request: TripRequest) -> List[str]:
        agents = [AGENT_DESTINATION]

        if request.month:
            agents.append(AGENT_CLIMATE)

        if request.source:
            agents.append(AGENT_TRANSPORT)

        agents.append(AGENT_HOTEL)
        agents.append(AGENT_ITINERARY)
        agents.append(AGENT_BUDGET)

        return self._validate_and_order_agents(agents, request)

```

---

## File: `orchestrator/__init__.py`

```py

```

---

## File: `schemas/agent_schema.py`

```py
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class AgentInput:
    query: str
    source: Optional[str] = None
    destination: Optional[str] = None
    month: Optional[str] = None
    days: Optional[int] = None
    budget: Optional[str] = None
    travelers: Optional[int] = None
    interests: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentOutput:
    agent_name: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    message: Optional[str] = None
    error: Optional[str] = None


@dataclass
class AgentMetadata:
    name: str
    description: str
    depends_on: List[str] = field(default_factory=list)
    output_key: Optional[str] = None
```

---

## File: `schemas/clarification_schema.py`

```py
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Clarification "kind" values. Kept as module constants so the UI and planner
# agree on the vocabulary without magic strings scattered around.
KIND_FREE_TEXT = "free_text"
KIND_SINGLE_SELECT = "single_select"
KIND_MULTI_SELECT = "multi_select"


@dataclass
class ClarificationOption:
    """One selectable answer for a select-style question."""

    id: str
    label: str
    description: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClarificationQuestion:
    """A single question posed to the user.

    ``fills_field`` names the ``TripRequest`` field (or a well-known control
    field like ``selected_cities``) that the answer should populate. This lets
    the planner merge answers back generically without per-question code.
    """

    id: str
    question: str
    kind: str = KIND_FREE_TEXT
    options: List[ClarificationOption] = field(default_factory=list)
    fills_field: Optional[str] = None


@dataclass
class ClarificationRequest:
    """A pause-the-workflow request carrying one or more questions.

    Emitted from a node via ``interrupt(asdict(request))`` and rendered by the
    UI. Designed to be open-ended: new clarification types are added by
    appending a rule in the planner, never by changing the graph or this schema.
    """

    reason: str
    questions: List[ClarificationQuestion] = field(default_factory=list)
    origin: str = "clarify"          # which node raised it (clarify | city_selection)

```

---

## File: `schemas/mcp_schema.py`

```py
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class MCPToolResponse:
    tool_name: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    raw_response: Optional[Any] = None

```

---

## File: `schemas/trip_schema.py`

```py
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TypedDict


@dataclass
class TripRequest:
    user_query: str
    source: Optional[str] = None
    destination: Optional[str] = None
    month: Optional[str] = None
    days: Optional[int] = None
    budget: Optional[str] = None
    travelers: Optional[int] = None
    interests: List[str] = field(default_factory=list)
    travel_dates: Optional[Dict[str, str]] = None

    suggested_agents: List[str] = field(default_factory=list)
    missing_fields: List[str] = field(default_factory=list)
    confidence: float = 0.0
    parser_used: str = "unknown"

    turn_type: str = "new_plan"
    modified_fields: List[str] = field(default_factory=list)
    clarification_questions: List[str] = field(default_factory=list)
    destination_scope: str = "unknown"


class TripState(TypedDict, total=False):
    """Shared trip-planning state — the single channel every agent reads and writes.

    This is the LangGraph graph state. It holds ONLY JSON-serializable values
    (dicts / lists / primitives) so it survives checkpointer serialization
    across an ``interrupt`` pause/resume. The rich dataclasses (``TripRequest``,
    ``AgentInput``, ``AgentOutput``) are reconstructed at node boundaries; they
    never live inside the state itself.
    """

    # --- Core planning inputs / outputs ---
    raw_user_query: str
    request: Dict[str, Any]                    # serialized TripRequest
    agent_results: Dict[str, Dict[str, Any]]   # agent_name -> serialized AgentOutput
    errors: List[str]
    conversation_history: List[Dict[str, Any]]

    # --- Planner-owned control fields (routing / phase bookkeeping) ---
    phase: str
    next_node: str
    pending_clarification: Optional[Dict[str, Any]]   # serialized ClarificationRequest
    clarification_answers: Dict[str, Any]
    asked_clarifications: List[str]            # rule ids already asked, prevents re-asking forever
    planned_agents: List[str]                  # agent set decided once destination is resolved

    # --- Hierarchical destination planning ---
    destination_resolved: bool
    selected_cities: List[str]
    city_recommendations: List[Dict[str, Any]]
    city_attractions: Dict[str, Any]                  # city -> ranked attractions

    # --- Transport / feasibility / replanning ---
    travel_sequence: Optional[Dict[str, Any]]
    feasible: Optional[bool]
    replan_count: int
    replan_directives: List[str]

    # --- Terminal ---
    final_response: Optional[Dict[str, Any]]
    done: bool
    trip_memory: Dict[str, Any]
    conversation_history: List[Dict[str, Any]]


@dataclass
class FinalTripPlan:
    query: str
    destination: Optional[str]
    summary: str
    sections: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
```

---

## File: `schemas/__init__.py`

```py

```

---

## File: `services/hotel_service.py`

```py
from typing import Any, Dict, List, Optional

import requests

from config.settings import api_settings, network_settings


class HotelService:
    def __init__(self):
        self.geoapify_api_key = api_settings.geoapify_api_key
        self.timeout = network_settings.request_timeout
        self.ssl_verify = network_settings.geoapify_ssl_verify

        self.geoapify_geocode_url = "https://api.geoapify.com/v1/geocode/search"
        self.geoapify_places_url = "https://api.geoapify.com/v2/places"

    def search_hotels(
        self,
        destination: str,
        budget: Optional[str] = None,
        travelers: Optional[int] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        if not destination:
            return {
                "success": False,
                "error": "Destination is required for hotel search.",
                "hotels": [],
            }

        geo_data = self._geocode_location(destination)

        if not geo_data:
            return {
                "success": False,
                "error": f"Could not geocode destination: {destination}",
                "hotels": [],
            }

        accommodation_pois = self._fetch_accommodation_pois(
            latitude=geo_data.get("latitude"),
            longitude=geo_data.get("longitude"),
            limit=limit,
        )

        stay_area_signals = self._build_stay_area_signals(
            destination=destination,
            budget=budget,
            travelers=travelers,
            accommodation_pois=accommodation_pois,
        )

        return {
            "success": True,
            "destination": destination,
            "budget": budget,
            "travelers": travelers,
            "location": geo_data,
            "hotel_data_type": "accommodation_pois_and_stay_area_signals",
            "accommodation_pois": accommodation_pois,
            "stay_area_signals": stay_area_signals,
            "note": (
                "This is raw accommodation and stay-area data from Geoapify. "
                "Final hotel advice should be generated by the final composer using this structured data."
            ),
        }

    def _geocode_location(self, location: str) -> Optional[Dict[str, Any]]:
        if not self.geoapify_api_key:
            return None

        params = {
            "text": location,
            "apiKey": self.geoapify_api_key,
            "limit": 1,
            "filter": "countrycode:in",
        }

        try:
            response = requests.get(
                self.geoapify_geocode_url,
                params=params,
                timeout=self.timeout,
                verify=self.ssl_verify,
            )

            response.raise_for_status()
            data = response.json()

            features = data.get("features", [])

            if not features:
                return None

            properties = features[0].get("properties", {})
            geometry = features[0].get("geometry", {})
            coordinates = geometry.get("coordinates", [])

            lon = None
            lat = None

            if len(coordinates) >= 2:
                lon = coordinates[0]
                lat = coordinates[1]

            return {
                "formatted": properties.get("formatted"),
                "city": properties.get("city") or properties.get("name"),
                "state": properties.get("state"),
                "country": properties.get("country"),
                "latitude": lat,
                "longitude": lon,
            }

        except Exception as e:
            print("[HotelService] Geoapify geocoding failed:")
            print(type(e).__name__, str(e))
            return None

    def _fetch_accommodation_pois(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        limit: int,
    ) -> List[Dict[str, Any]]:
        if not self.geoapify_api_key:
            return []

        if latitude is None or longitude is None:
            return []

        categories = [
            "accommodation",
            "accommodation.hotel",
            "accommodation.guest_house",
            "accommodation.hostel",
            "accommodation.apartment",
            "accommodation.resort",
        ]

        params = {
            "categories": ",".join(categories),
            "filter": f"circle:{longitude},{latitude},20000",
            "bias": f"proximity:{longitude},{latitude}",
            "limit": limit,
            "apiKey": self.geoapify_api_key,
        }

        try:
            response = requests.get(
                self.geoapify_places_url,
                params=params,
                timeout=self.timeout,
                verify=self.ssl_verify,
            )

            response.raise_for_status()
            data = response.json()

            hotels = []

            for feature in data.get("features", []):
                properties = feature.get("properties", {})
                geometry = feature.get("geometry", {})
                coordinates = geometry.get("coordinates", [])

                poi_lon = None
                poi_lat = None

                if len(coordinates) >= 2:
                    poi_lon = coordinates[0]
                    poi_lat = coordinates[1]

                name = (
                    properties.get("name")
                    or properties.get("address_line1")
                    or properties.get("formatted")
                )

                if not name:
                    continue

                hotels.append(
                    {
                        "name": name,
                        "categories": properties.get("categories", []),
                        "formatted_address": properties.get("formatted"),
                        "latitude": poi_lat,
                        "longitude": poi_lon,
                        "distance_meters": properties.get("distance"),
                        "place_id": properties.get("place_id"),
                    }
                )

            return hotels[:limit]

        except Exception as e:
            print("[HotelService] Geoapify accommodation lookup failed:")
            print(type(e).__name__, str(e))
            return []

    def _build_stay_area_signals(
        self,
        destination: str,
        budget: Optional[str],
        travelers: Optional[int],
        accommodation_pois: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        budget_level = budget or "medium"
        travelers_count = travelers or 1

        density = "low"

        if len(accommodation_pois) >= 8:
            density = "good"
        elif len(accommodation_pois) >= 4:
            density = "moderate"

        return {
            "destination": destination,
            "budget_level": budget_level,
            "travelers": travelers_count,
            "accommodation_density": density,
            "available_poi_count": len(accommodation_pois),
            "suggested_stay_type": self._suggest_stay_type(
                budget=budget_level,
                travelers=travelers_count,
            ),
            "booking_advice_signal": self._booking_advice_signal(
                budget=budget_level,
                accommodation_count=len(accommodation_pois),
            ),
        }

    def _suggest_stay_type(
        self,
        budget: str,
        travelers: int,
    ) -> List:
        if budget == "low":
            return [
                "budget hotel",
                "guest house",
                "hostel",
                "homestay",
            ]

        if budget == "high":
            return [
                "premium resort",
                "boutique hotel",
                "high-rated hotel",
            ]

        if travelers >= 3:
            return [
                "family hotel",
                "serviced apartment",
                "homestay",
                "mid-range resort",
            ]

        return [
            "mid-range hotel",
            "boutique stay",
            "homestay",
        ]

    def _booking_advice_signal(
        self,
        budget: str,
        accommodation_count: int,
    ) -> str:
        if accommodation_count == 0:
            return "No accommodation POIs found from Geoapify. Use final composer to suggest checking major booking platforms."

        if accommodation_count < 4:
            return "Limited accommodation POIs found. Booking early is recommended."

        if budget == "low":
            return "Compare budget hotels and homestays early because low-cost options may fill quickly."

        if budget == "high":
            return "Premium stays should be filtered by amenities, location, and cancellation policy."

        return "Good number of stay options found. Compare location, reviews, and commute convenience."
```

---

## File: `services/places_service.py`

```py
import html
import json
from typing import Any, Dict, List, Optional

import google.generativeai as genai
import requests

from config.constants import (
    SCOPE_CITY,
    SCOPE_STATE,
    SCOPE_COUNTRY,
    SCOPE_REGION,
    SCOPE_UNKNOWN,
)
from config.settings import api_settings, network_settings


# ---------------------------------------------------------------------- #
# Geoapify destination scope constants
# ---------------------------------------------------------------------- #

CITY_RESULT_TYPES = {
    "city",
    "town",
    "village",
    "suburb",
    "district",
    "municipality",
}

STATE_RESULT_TYPES = {
    "state",
    "county",
    "province",
}

COUNTRY_RESULT_TYPES = {
    "country",
}

KNOWN_REGION_KEYWORDS = [
    "south india",
    "north india",
    "north east india",
    "north east",
    "northeast",
    "east india",
    "west india",
    "central india",
]


# ---------------------------------------------------------------------- #
# POI filtering constants
# ---------------------------------------------------------------------- #

STRONG_ATTRACTION_CATEGORY_TERMS = [
    "tourism",
    "tourism.attraction",
    "tourism.sights",
    "tourism.information",
    "entertainment.museum",
    "museum",
    "heritage",
    "historic",
    "historical",
    "monument",
    "memorial",
    "castle",
    "fort",
    "palace",
    "archaeological",
    "religion",
    "temple",
    "church",
    "mosque",
    "natural",
    "natural.water",
    "natural.mountain",
    "natural.forest",
    "natural.beach",
    "beach",
    "lake",
    "waterfall",
    "park",
    "garden",
    "viewpoint",
    "zoo",
    "aquarium",
    "leisure.park",
    "validated_landmark",
]


BLOCKED_POI_CATEGORY_TERMS = [
    "catering",
    "restaurant",
    "cafe",
    "coffee",
    "bar",
    "pub",
    "fast_food",
    "food_court",
    "accommodation",
    "hotel",
    "hostel",
    "guest_house",
    "apartment",
    "resort",
    "commercial",
    "shop",
    "shopping",
    "marketplace",
    "supermarket",
    "mall",
    "book",
    "books",
    "bookstore",
    "office",
    "bank",
    "atm",
    "street",
    "road",
    "highway",
    "residential",
    "building",
    "service",
    "healthcare",
    "hospital",
    "pharmacy",
    "education",
    "school",
    "college",
    "university",
    "parking",
    "fuel",
    "transport",
    "bus",
    "railway",
    "airport",
]


BLOCKED_POI_NAME_HINTS = [
    "road",
    "street",
    "rasta",
    "marg",
    "path",
    "lane",
    "hotel",
    "restaurant",
    "cafe",
    "coffee",
    "bhojnalaya",
    "dhaba",
    "bar",
    "pub",
    "book",
    "pustak",
    "store",
    "shop",
    "bank",
    "atm",
]


class PlacesService:
    def __init__(self):
        self.geoapify_api_key = api_settings.geoapify_api_key
        self.gemini_api_key = api_settings.gemini_api_key
        self.timeout = network_settings.request_timeout
        self.ssl_verify = network_settings.geoapify_ssl_verify

        self.geoapify_geocode_url = "https://api.geoapify.com/v1/geocode/search"
        self.geoapify_places_url = "https://api.geoapify.com/v2/places"

        self.gemini_model = None
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel(api_settings.gemini_model)

    # ------------------------------------------------------------------ #
    # Destination recommendation when user has no fixed destination
    # ------------------------------------------------------------------ #

    def recommend_destinations(
        self,
        source: Optional[str] = None,
        interests: Optional[List[str]] = None,
        month: Optional[str] = None,
        budget: Optional[str] = None,
        days: Optional[int] = None,
        travelers: Optional[int] = None,
        limit: int = 8,
    ) -> Dict[str, Any]:
        interests = interests or []

        if not self.gemini_model:
            return {
                "success": False,
                "error": "Gemini API key is required to recommend destinations from preference-only queries.",
                "recommendations": [],
            }

        prompt = f"""
You are a destination recommendation engine for an Indian trip planning assistant.

Return only valid JSON.
Do not include markdown.
Do not explain anything.

Task:
Recommend suitable Indian city/town destinations for the user's trip preferences.

Rules:
1. Recommend concrete Indian cities/towns only.
2. Do not recommend broad states/regions/countries.
3. Do not recommend attractions, hotels, restaurants, cafes, roads, or markets as destinations.
4. Prefer practical destinations based on source, month, interests, budget, days, and travelers.
5. Each recommendation must include a short reason and match_score from 0 to 100.
6. Return at most {limit} destinations.

Input:
source: {source}
interests: {json.dumps(interests, ensure_ascii=False)}
month: {month}
budget: {budget}
days: {days}
travelers: {travelers}

Return JSON exactly in this format:
{{
  "recommendations": [
    {{
      "destination": "City Name",
      "state": "State Name",
      "reason": "short reason",
      "match_score": 85,
      "best_for": ["heritage", "food"],
      "budget_fit": "low|medium|high"
    }}
  ]
}}
"""

        try:
            response = self.gemini_model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.25,
                    "top_p": 0.8,
                    "top_k": 40,
                },
            )

            text = getattr(response, "text", "").strip()
            data = json.loads(self._extract_json(text))

            recommendations = data.get("recommendations", [])
            validated = self._validate_recommendation_candidates(
                recommendations=recommendations,
                limit=limit,
            )

            return {
                "success": True,
                "source": source,
                "interests": interests,
                "month": month,
                "budget": budget,
                "days": days,
                "travelers": travelers,
                "recommendations": validated,
                "recommendation_method": "gemini_validated_by_geoapify",
            }

        except Exception as e:
            print("[PlacesService] Destination recommendation failed:")
            print(type(e).__name__, str(e))
            return {
                "success": False,
                "error": f"Destination recommendation failed: {type(e).__name__}: {str(e)}",
                "recommendations": [],
            }

    # ------------------------------------------------------------------ #
    # Destination scope classification
    # ------------------------------------------------------------------ #

    def classify_destination(self, name: str) -> Dict[str, Any]:
        if not name:
            return {
                "success": False,
                "error": "Destination name is required for classification.",
                "scope": SCOPE_UNKNOWN,
            }

        normalized_name = self._clean_text(name)
        if not normalized_name:
            return {
                "success": False,
                "error": "Destination name is empty after cleanup.",
                "scope": SCOPE_UNKNOWN,
            }

        lowered = normalized_name.lower()

        if any(keyword == lowered for keyword in KNOWN_REGION_KEYWORDS):
            return {
                "success": True,
                "input": name,
                "canonical_name": normalized_name.title(),
                "scope": SCOPE_REGION,
                "classification_method": "known_region_keyword",
            }

        geo_data = self._geocode_location(normalized_name)

        if not geo_data:
            return {
                "success": False,
                "error": f"Could not classify destination: {name}",
                "scope": SCOPE_UNKNOWN,
            }

        result_type = str(geo_data.get("result_type") or "").lower()
        canonical_name = (
            geo_data.get("city")
            or geo_data.get("state")
            or geo_data.get("country")
            or geo_data.get("name")
            or normalized_name
        )

        if result_type in CITY_RESULT_TYPES:
            scope = SCOPE_CITY
        elif result_type in STATE_RESULT_TYPES:
            scope = SCOPE_STATE
        elif result_type in COUNTRY_RESULT_TYPES:
            scope = SCOPE_COUNTRY
        else:
            scope = self._fallback_scope_from_geocode(geo_data)

        return {
            "success": True,
            "input": name,
            "canonical_name": canonical_name,
            "scope": scope,
            "result_type": result_type,
            "location": geo_data,
            "classification_method": "geoapify_geocode",
        }

    def _fallback_scope_from_geocode(self, geo_data: Dict[str, Any]) -> str:
        if geo_data.get("city"):
            return SCOPE_CITY

        if geo_data.get("state") and not geo_data.get("city"):
            return SCOPE_STATE

        if geo_data.get("country") and not geo_data.get("city") and not geo_data.get("state"):
            return SCOPE_COUNTRY

        return SCOPE_UNKNOWN

    # ------------------------------------------------------------------ #
    # City recommendations inside state/region/country
    # ------------------------------------------------------------------ #

    def recommend_cities_in_region(
        self,
        region: str,
        interests: Optional[List[str]] = None,
        days: Optional[int] = None,
        budget: Optional[str] = None,
        travelers: Optional[int] = None,
        travel_style: Optional[str] = None,
        limit: int = 6,
    ) -> Dict[str, Any]:
        interests = interests or []

        if not region:
            return {
                "success": False,
                "error": "Region is required to recommend cities.",
                "recommendations": [],
            }

        if not self.gemini_model:
            return {
                "success": False,
                "error": "Gemini API key is required to recommend cities inside a broad region.",
                "recommendations": [],
            }

        prompt = f"""
You are a city selection planner for an Indian trip planning assistant.

Return only valid JSON.
Do not include markdown.
Do not explain anything.

Task:
Recommend concrete cities/towns inside the given broad destination/region.

Rules:
1. Recommend city/town names only.
2. Do not recommend the broad region itself.
3. Do not recommend attractions, restaurants, hotels, roads, or markets as cities.
4. Consider trip duration, interests, budget, travelers, and travel style.
5. Prefer realistic combinations for the number of days.
6. Return at most {limit} cities.

Input:
region: {region}
interests: {json.dumps(interests, ensure_ascii=False)}
days: {days}
budget: {budget}
travelers: {travelers}
travel_style: {travel_style}

Return JSON exactly in this format:
{{
  "recommendations": [
    {{
      "destination": "City Name",
      "state": "State Name",
      "reason": "short reason",
      "match_score": 90,
      "best_for": ["heritage", "food"]
    }}
  ]
}}
"""

        try:
            response = self.gemini_model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.2,
                    "top_p": 0.8,
                    "top_k": 40,
                },
            )

            text = getattr(response, "text", "").strip()
            data = json.loads(self._extract_json(text))

            recommendations = data.get("recommendations", [])
            validated = self._validate_city_candidates_inside_region(
                region=region,
                recommendations=recommendations,
                limit=limit,
            )

            return {
                "success": True,
                "region": region,
                "interests": interests,
                "days": days,
                "budget": budget,
                "travelers": travelers,
                "travel_style": travel_style,
                "recommendations": validated,
                "recommendation_method": "gemini_validated_by_geoapify",
            }

        except Exception as e:
            print("[PlacesService] City recommendation inside region failed:")
            print(type(e).__name__, str(e))
            return {
                "success": False,
                "error": f"City recommendation failed: {type(e).__name__}: {str(e)}",
                "recommendations": [],
            }

    # ------------------------------------------------------------------ #
    # Popular places / attractions
    # ------------------------------------------------------------------ #

    def get_popular_places(
        self,
        destination: str,
        interests: Optional[List[str]] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        interests = interests or []

        if not destination:
            return {
                "success": False,
                "error": "Destination is required for places lookup.",
                "places": [],
            }

        geo_data = self._geocode_location(destination)

        if not geo_data:
            return {
                "success": False,
                "error": f"Could not geocode destination: {destination}",
                "places": [],
            }

        categories = self._build_attraction_categories(interests)

        raw_places = self._fetch_geoapify_places(
            latitude=geo_data.get("latitude"),
            longitude=geo_data.get("longitude"),
            categories=categories,
            limit=max(limit * 4, 30),
        )

        usable_places = self._filter_usable_attractions(raw_places)

        landmark_fallback_used = False
        landmark_candidates = []
        validated_landmarks = []

        if len(usable_places) < 3:
            landmark_fallback_used = True
            landmark_candidates = self._generate_landmark_candidates(
                city=destination,
                interests=interests,
                limit=max(limit, 8),
            )
            validated_landmarks = self._validate_landmark_candidates(
                city=destination,
                city_location=geo_data,
                candidates=landmark_candidates,
                limit=limit,
            )
            usable_places = self._merge_places(
                primary=usable_places,
                secondary=validated_landmarks,
                limit=limit,
            )

        usable_places = usable_places[:limit]

        return {
            "success": True,
            "destination": destination,
            "location": geo_data,
            "interests": interests,
            "categories_used": categories,
            "places": usable_places,
            "raw_place_count": len(raw_places),
            "usable_place_count": len(usable_places),
            "poi_quality": "usable" if len(usable_places) >= 3 else "weak",
            "landmark_fallback_used": landmark_fallback_used,
            "landmark_candidates": landmark_candidates,
            "validated_landmark_count": len(validated_landmarks),
            "note": (
                "Strong sightseeing POIs are returned. Restaurants, cafes, hotels, roads, shops, "
                "bookstores, and commercial POIs are filtered out. If normal Geoapify POIs are weak, "
                "canonical landmark candidates are generated by Gemini and validated with Geoapify."
            ),
        }

    def _build_attraction_categories(self, interests: Optional[List[str]]) -> List:
        interests = interests or []

        base_categories = [
            "tourism",
            "tourism.attraction",
            "tourism.sights",
            "tourism.information",
            "entertainment.museum",
            "natural",
            "natural.water",
            "natural.beach",
            "leisure.park",
            "religion",
        ]

        interest_category_map = {
            "heritage": [
                "tourism.sights",
                "tourism.attraction",
                "entertainment.museum",
            ],
            "religious": [
                "religion",
                "tourism.sights",
            ],
            "nature": [
                "natural",
                "natural.water",
                "natural.forest",
                "natural.mountain",
                "leisure.park",
            ],
            "beach": [
                "natural.beach",
                "natural.water",
                "tourism.attraction",
            ],
            "adventure": [
                "natural",
                "sport",
                "tourism.attraction",
            ],
            "shopping": [
                "tourism.sights",
            ],
            "food": [
                "tourism.sights",
                "tourism.attraction",
            ],
            "nightlife": [
                "tourism.sights",
                "tourism.attraction",
            ],
            "relaxation": [
                "natural",
                "leisure.park",
                "tourism.attraction",
            ],
            "romantic": [
                "natural",
                "natural.water",
                "tourism.attraction",
                "tourism.sights",
            ],
        }

        categories = list(base_categories)

        for interest in interests:
            categories.extend(interest_category_map.get(str(interest).lower(), []))

        seen = set()
        unique_categories = []

        for category in categories:
            if category not in seen:
                seen.add(category)
                unique_categories.append(category)

        return unique_categories

    def _fetch_geoapify_places(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        categories: List[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        if not self.geoapify_api_key:
            return []

        if latitude is None or longitude is None:
            return []

        params = {
            "categories": ",".join(categories),
            "filter": f"circle:{longitude},{latitude},25000",
            "bias": f"proximity:{longitude},{latitude}",
            "limit": limit,
            "apiKey": self.geoapify_api_key,
        }

        try:
            response = requests.get(
                self.geoapify_places_url,
                params=params,
                timeout=self.timeout,
                verify=self.ssl_verify,
            )
            response.raise_for_status()

            data = response.json()
            places = []

            for feature in data.get("features", []):
                properties = feature.get("properties", {})
                geometry = feature.get("geometry", {})
                coordinates = geometry.get("coordinates", [])

                lon = None
                lat = None

                if len(coordinates) >= 2:
                    lon = coordinates[0]
                    lat = coordinates[1]

                name = (
                    properties.get("name")
                    or properties.get("address_line1")
                    or properties.get("formatted")
                )

                if not name:
                    continue

                places.append(
                    {
                        "name": self._clean_text(name),
                        "categories": properties.get("categories", []),
                        "formatted_address": self._clean_text(properties.get("formatted")),
                        "latitude": lat,
                        "longitude": lon,
                        "distance_meters": properties.get("distance"),
                        "place_id": properties.get("place_id"),
                        "source": "geoapify_places",
                    }
                )

            return places

        except Exception as e:
            print("[PlacesService] Geoapify places lookup failed:")
            print(type(e).__name__, str(e))
            return []

    def _filter_usable_attractions(self, places: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not places:
            return []

        filtered = []
        seen_names = set()

        for place in places:
            if not isinstance(place, dict):
                continue

            name = self._clean_text(place.get("name"))

            if not name:
                continue

            normalized_name = name.lower().strip()

            if normalized_name in seen_names:
                continue

            if self._looks_like_blocked_poi_name(normalized_name):
                continue

            categories = (
                place.get("categories")
                or place.get("category")
                or place.get("kinds")
                or []
            )

            if isinstance(categories, str):
                categories = [categories]

            category_text = " ".join(str(category).lower() for category in categories)

            if self._has_blocked_poi_category(category_text):
                continue

            if not self._has_strong_attraction_category(category_text):
                continue

            cleaned_place = {
                "name": name,
                "categories": categories,
                "formatted_address": self._clean_text(place.get("formatted_address")),
                "latitude": place.get("latitude"),
                "longitude": place.get("longitude"),
                "distance_meters": place.get("distance_meters"),
                "place_id": place.get("place_id"),
                "source": place.get("source") or "geoapify",
            }

            filtered.append(cleaned_place)
            seen_names.add(normalized_name)

        return filtered

    # ------------------------------------------------------------------ #
    # Landmark fallback: Gemini candidates + Geoapify validation
    # ------------------------------------------------------------------ #

    def _generate_landmark_candidates(
        self,
        city: str,
        interests: Optional[List[str]],
        limit: int = 8,
    ) -> List[Dict[str, Any]]:
        interests = interests or []

        if not self.gemini_model:
            return []

        prompt = f"""
You are a canonical attraction candidate generator for an Indian travel planning system.

Return only valid JSON.
Do not include markdown.
Do not explain anything.

Task:
List well-known sightseeing attractions for the given Indian city.

Rules:
1. Return only attractions/landmarks suitable for a travel itinerary.
2. Do not return restaurants, cafes, hotels, roads, streets, shops, bookstores, offices, banks, or generic markets.
3. Prefer forts, palaces, temples, museums, lakes, gardens, viewpoints, monuments, heritage sites, and nature spots.
4. Do not invent obscure or fake places.
5. Keep names concise and searchable.
6. Match user interests where possible.
7. Return at most {limit} candidates.

City:
{city}

User interests:
{json.dumps(interests, ensure_ascii=False)}

Return JSON exactly in this format:
{{
  "candidates": [
    {{
      "name": "Attraction Name",
      "type": "fort|palace|museum|lake|temple|garden|viewpoint|monument|heritage|nature|other",
      "reason": "short reason"
    }}
  ]
}}
"""

        try:
            response = self.gemini_model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.15,
                    "top_p": 0.8,
                    "top_k": 40,
                },
            )

            text = getattr(response, "text", "").strip()
            data = json.loads(self._extract_json(text))

            candidates = data.get("candidates", [])
            cleaned = []

            for item in candidates:
                if not isinstance(item, dict):
                    continue

                name = self._clean_text(item.get("name"))
                if not name:
                    continue

                normalized_name = name.lower()
                if self._looks_like_blocked_poi_name(normalized_name):
                    continue

                cleaned.append(
                    {
                        "name": name,
                        "type": self._clean_text(item.get("type")) or "attraction",
                        "reason": self._clean_text(item.get("reason")),
                        "source": "gemini_landmark_candidate",
                    }
                )

                if len(cleaned) >= limit:
                    break

            return cleaned

        except Exception as e:
            print("[PlacesService] Landmark candidate generation failed:")
            print(type(e).__name__, str(e))
            return []

    def _validate_landmark_candidates(
    self,
    city: str,
    city_location: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    limit: int,
) -> List[Dict[str, Any]]:
        if not candidates:
            return []
    
        validated = []
        seen_names = set()
    
        city_name = self._clean_text(city)
        city_name_lower = city_name.lower() if city_name else ""
    
        city_lat = city_location.get("latitude")
        city_lon = city_location.get("longitude")
    
        for candidate in candidates:
            name = self._clean_text(candidate.get("name"))
    
            if not name:
                continue
            
            normalized_name = name.lower().strip()
    
            if normalized_name in seen_names:
                continue
            
            if self._looks_like_blocked_poi_name(normalized_name):
                continue
            
            query = f"{name}, {city}, India"
            geo_data = self._geocode_location(query)
    
            if not geo_data:
                continue
            
            lat = geo_data.get("latitude")
            lon = geo_data.get("longitude")
    
            if lat is None or lon is None:
                continue
            
            resolved_city = self._clean_text(
                geo_data.get("city")
                or geo_data.get("town")
                or geo_data.get("village")
                or geo_data.get("name")
            )
    
            resolved_city_lower = resolved_city.lower() if resolved_city else ""
    
            distance_km = None
    
            if city_lat is not None and city_lon is not None:
                distance_km = self._haversine_km(
                    lat1=float(city_lat),
                    lon1=float(city_lon),
                    lat2=float(lat),
                    lon2=float(lon),
                )
    
            candidate_type = str(candidate.get("type") or "").lower()
    
            # Strict city ownership guard:
            # If Geoapify clearly resolves this landmark to another selected city/town,
            # do not attach it to the current city.
            if resolved_city_lower and city_name_lower:
                if resolved_city_lower != city_name_lower:
                    # Allow only broad natural/outing spots within a reasonable excursion radius.
                    is_excursion_type = any(
                        term in candidate_type
                        for term in ["lake", "beach", "nature", "wildlife", "waterfall"]
                    )
    
                    if not is_excursion_type:
                        continue
                    
            # Normal city landmark radius.
            # This prevents "Konark Sun Temple" from being added to Puri.
            # Natural excursions get a slightly larger radius.
            if distance_km is not None:
                is_excursion_type = any(
                    term in candidate_type
                    for term in ["lake", "beach", "nature", "wildlife", "waterfall"]
                )
    
                max_radius_km = 55 if is_excursion_type else 30
    
                if distance_km > max_radius_km:
                    continue
                
            validated_place = {
                "name": name,
                "categories": [
                    "tourism.attraction",
                    "validated_landmark",
                    str(candidate.get("type") or "attraction"),
                ],
                "formatted_address": geo_data.get("formatted"),
                "latitude": lat,
                "longitude": lon,
                "distance_meters": int(distance_km * 1000) if distance_km is not None else None,
                "place_id": geo_data.get("place_id"),
                "reason": candidate.get("reason"),
                "source": "gemini_candidate_geoapify_validated",
                "resolved_city": resolved_city,
            }
    
            if self._filter_usable_attractions([validated_place]):
                validated.append(validated_place)
                seen_names.add(normalized_name)
    
            if len(validated) >= limit:
                break
            
        return validated
    
    def _merge_places(
        self,
        primary: List[Dict[str, Any]],
        secondary: List[Dict[str, Any]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        merged = []
        seen_names = set()

        for place in list(primary or []) + list(secondary or []):
            if not isinstance(place, dict):
                continue

            name = self._clean_text(place.get("name"))

            if not name:
                continue

            normalized_name = name.lower().strip()

            if normalized_name in seen_names:
                continue

            merged.append(place)
            seen_names.add(normalized_name)

            if len(merged) >= limit:
                break

        return merged

    # ------------------------------------------------------------------ #
    # Place ranking
    # ------------------------------------------------------------------ #

    def rank_places(
        self,
        city: str,
        places: List[Dict[str, Any]],
        interests: Optional[List[str]] = None,
        days: Optional[int] = None,
    ) -> Dict[str, Any]:
        interests = interests or []
        places = places or []

        usable_places = self._filter_usable_attractions(places)

        if not usable_places:
            return {
                "success": True,
                "city": city,
                "interests": interests,
                "days": days,
                "ranked_places": [],
                "poi_quality": "weak",
                "note": (
                    "No reliable sightseeing POIs were available after filtering. "
                    "The final composer should create a high-level itinerary without naming raw POIs."
                ),
            }

        if not self.gemini_model:
            return {
                "success": True,
                "city": city,
                "interests": interests,
                "days": days,
                "ranked_places": usable_places,
                "poi_quality": "usable" if len(usable_places) >= 3 else "weak",
                "ranking_method": "filtered_order_without_llm",
            }

        prompt = f"""
You are ranking sightseeing attractions for a travel itinerary.

Return only valid JSON.
Do not include markdown.
Do not add new places.

Rules:
1. Use only the provided places.
2. Rank genuine sightseeing attractions higher.
3. Prefer places that match the user's interests.
4. Do not rank restaurants, cafes, hotels, shops, roads, offices, banks, streets, or commercial places.
5. Do not invent famous attractions missing from the provided list.

City:
{city}

Interests:
{json.dumps(interests, ensure_ascii=False)}

Days:
{days}

Places:
{json.dumps(usable_places, indent=2, ensure_ascii=False)}

Return JSON exactly in this format:
{{
  "ranked_places": [
    {{
      "name": "place name",
      "reason": "short reason",
      "priority": 1
    }}
  ]
}}
"""

        try:
            response = self.gemini_model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.1,
                    "top_p": 0.8,
                    "top_k": 40,
                },
            )

            text = getattr(response, "text", "").strip()
            data = json.loads(self._extract_json(text))

            ranked_names = [
                item.get("name")
                for item in data.get("ranked_places", [])
                if item.get("name")
            ]

            places_by_name = {
                str(place.get("name")).lower(): place
                for place in usable_places
                if place.get("name")
            }

            ranked_places = []

            for name in ranked_names:
                matched = places_by_name.get(str(name).lower())
                if matched:
                    ranked_places.append(matched)

            ranked_existing_names = {
                str(place.get("name")).lower()
                for place in ranked_places
                if place.get("name")
            }

            for place in usable_places:
                place_name = str(place.get("name")).lower()
                if place_name not in ranked_existing_names:
                    ranked_places.append(place)

            return {
                "success": True,
                "city": city,
                "interests": interests,
                "days": days,
                "ranked_places": ranked_places,
                "poi_quality": "usable" if len(ranked_places) >= 3 else "weak",
                "ranking_method": "gemini_filtered_ranking",
            }

        except Exception as e:
            print("[PlacesService] Gemini place ranking failed:")
            print(type(e).__name__, str(e))

            return {
                "success": True,
                "city": city,
                "interests": interests,
                "days": days,
                "ranked_places": usable_places,
                "poi_quality": "usable" if len(usable_places) >= 3 else "weak",
                "ranking_method": "fallback_filtered_order",
                "ranking_error": str(e),
            }

    # ------------------------------------------------------------------ #
    # Recommendation validation helpers
    # ------------------------------------------------------------------ #

    def _validate_recommendation_candidates(
        self,
        recommendations: List[Dict[str, Any]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        validated = []
        seen = set()

        for item in recommendations:
            if not isinstance(item, dict):
                continue

            destination = self._clean_text(item.get("destination"))
            if not destination:
                continue

            normalized_destination = destination.lower()

            if normalized_destination in seen:
                continue

            geo_data = self._geocode_location(destination)

            if not geo_data:
                continue

            scope = self._fallback_scope_from_geocode(geo_data)

            if scope != SCOPE_CITY:
                continue

            city = geo_data.get("city") or destination
            state = geo_data.get("state") or item.get("state")

            validated.append(
                {
                    "destination": city,
                    "state": state,
                    "reason": self._clean_text(item.get("reason")),
                    "match_score": item.get("match_score"),
                    "best_for": item.get("best_for") or [],
                    "budget_fit": item.get("budget_fit"),
                    "location": geo_data,
                }
            )

            seen.add(normalized_destination)

            if len(validated) >= limit:
                break

        return validated

    def _validate_city_candidates_inside_region(
        self,
        region: str,
        recommendations: List[Dict[str, Any]],
        limit: int,
    ) -> List[Dict[str, Any]]:
        validated = []
        seen = set()
        region_lower = region.lower().strip()

        for item in recommendations:
            if not isinstance(item, dict):
                continue

            destination = self._clean_text(item.get("destination"))

            if not destination:
                continue

            normalized_destination = destination.lower().strip()

            if normalized_destination == region_lower:
                continue

            if normalized_destination in seen:
                continue

            geo_data = self._geocode_location(destination)

            if not geo_data:
                continue

            scope = self._fallback_scope_from_geocode(geo_data)

            if scope != SCOPE_CITY:
                continue

            city = geo_data.get("city") or destination
            state = geo_data.get("state") or item.get("state")

            validated.append(
                {
                    "destination": city,
                    "state": state,
                    "reason": self._clean_text(item.get("reason")),
                    "match_score": item.get("match_score"),
                    "best_for": item.get("best_for") or [],
                    "location": geo_data,
                }
            )

            seen.add(normalized_destination)

            if len(validated) >= limit:
                break

        return validated

    # ------------------------------------------------------------------ #
    # Geoapify helpers
    # ------------------------------------------------------------------ #

    def _geocode_location(self, location: str) -> Optional[Dict[str, Any]]:
        if not self.geoapify_api_key:
            return None

        location = self._clean_text(location)

        if not location:
            return None

        params = {
            "text": location,
            "apiKey": self.geoapify_api_key,
            "limit": 1,
            "filter": "countrycode:in",
        }

        try:
            response = requests.get(
                self.geoapify_geocode_url,
                params=params,
                timeout=self.timeout,
                verify=self.ssl_verify,
            )
            response.raise_for_status()

            data = response.json()
            features = data.get("features", [])

            if not features:
                return None

            properties = features[0].get("properties", {})
            geometry = features[0].get("geometry", {})
            coordinates = geometry.get("coordinates", [])

            lon = None
            lat = None

            if len(coordinates) >= 2:
                lon = coordinates[0]
                lat = coordinates[1]

            return {
                "formatted": properties.get("formatted"),
                "name": properties.get("name"),
                "city": properties.get("city")
                or properties.get("town")
                or properties.get("village"),
                "state": properties.get("state"),
                "country": properties.get("country"),
                "result_type": properties.get("result_type"),
                "latitude": lat,
                "longitude": lon,
                "place_id": properties.get("place_id"),
            }

        except Exception as e:
            print("[PlacesService] Geoapify geocoding failed:")
            print(type(e).__name__, str(e))
            return None

    # ------------------------------------------------------------------ #
    # POI quality helpers
    # ------------------------------------------------------------------ #

    def _has_strong_attraction_category(self, category_text: str) -> bool:
        if not category_text:
            return False

        return any(term in category_text for term in STRONG_ATTRACTION_CATEGORY_TERMS)

    def _has_blocked_poi_category(self, category_text: str) -> bool:
        if not category_text:
            return False

        return any(term in category_text for term in BLOCKED_POI_CATEGORY_TERMS)

    def _looks_like_blocked_poi_name(self, normalized_name: str) -> bool:
        if not normalized_name:
            return True

        return any(hint in normalized_name for hint in BLOCKED_POI_NAME_HINTS)

    # ------------------------------------------------------------------ #
    # Numeric helpers
    # ------------------------------------------------------------------ #

    def _haversine_km(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:
        import math

        radius_km = 6371.0

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return radius_km * c

    # ------------------------------------------------------------------ #
    # Generic helpers
    # ------------------------------------------------------------------ #

    def _extract_json(self, text: str) -> str:
        text = text.strip()

        if text.startswith("```json"):
            text = text.replace("```json", "").replace("```", "").strip()
        elif text.startswith("```"):
            text = text.replace("```", "").strip()

        start = text.find("{")
        end = text.rfind("}")

        if start != -1 and end != -1:
            return text[start:end + 1]

        return text

    def _clean_text(self, value: Any) -> Optional:
        if value is None:
            return None

        if not isinstance(value, str):
            value = str(value)

        value = html.unescape(value)
        value = " ".join(value.split())
        value = value.strip()

        return value or None
```

---

## File: `services/transport_service.py`

```py
import math
from typing import Any, Dict, Optional

import requests

from config.settings import api_settings, network_settings


class TransportService:
    def __init__(self):
        self.geoapify_api_key = api_settings.geoapify_api_key
        self.openrouteservice_api_key = api_settings.openrouteservice_api_key
        self.timeout = network_settings.request_timeout
        self.geoapify_ssl_verify = network_settings.geoapify_ssl_verify
        self.ssl_verify = network_settings.ssl_verify

        self.geoapify_geocode_url = "https://api.geoapify.com/v1/geocode/search"
        self.openrouteservice_directions_url = "https://api.openrouteservice.org/v2/directions"

    def get_transport_options(
        self,
        source: str,
        destination: str,
        mode: str = "driving-car",
    ) -> Dict[str, Any]:
        if not source:
            return {
                "success": False,
                "error": "Source is required for transport planning.",
                "transport": None,
            }

        if not destination:
            return {
                "success": False,
                "error": "Destination is required for transport planning.",
                "transport": None,
            }

        source_location = self._geocode_location(source)
        destination_location = self._geocode_location(destination)

        if not source_location:
            return {
                "success": False,
                "error": f"Could not geocode source: {source}",
                "transport": None,
            }

        if not destination_location:
            return {
                "success": False,
                "error": f"Could not geocode destination: {destination}",
                "transport": None,
            }

        route_data = self._get_openrouteservice_route(
            source_location=source_location,
            destination_location=destination_location,
            mode=mode,
        )

        if not route_data:
            route_data = self._build_fallback_route_estimate(
                source_location=source_location,
                destination_location=destination_location,
                mode=mode,
            )

        return {
            "success": True,
            "source": source,
            "destination": destination,
            "mode": mode,
            "source_location": source_location,
            "destination_location": destination_location,
            "transport": route_data,
        }

    def _geocode_location(self, location: str) -> Optional[Dict[str, Any]]:
        if not self.geoapify_api_key:
            return None

        params = {
            "text": location,
            "apiKey": self.geoapify_api_key,
            "limit": 1,
            "filter": "countrycode:in",
        }

        try:
            response = requests.get(
                self.geoapify_geocode_url,
                params=params,
                timeout=self.timeout,
                verify=self.geoapify_ssl_verify,
            )

            response.raise_for_status()
            data = response.json()

            features = data.get("features", [])

            if not features:
                return None

            properties = features[0].get("properties", {})
            geometry = features[0].get("geometry", {})
            coordinates = geometry.get("coordinates", [])

            lon = None
            lat = None

            if len(coordinates) >= 2:
                lon = coordinates[0]
                lat = coordinates[1]

            return {
                "query": location,
                "formatted": properties.get("formatted"),
                "city": properties.get("city") or properties.get("name"),
                "state": properties.get("state"),
                "country": properties.get("country"),
                "latitude": lat,
                "longitude": lon,
            }

        except Exception as e:
            print("[TransportService] Geoapify geocoding failed:")
            print(type(e).__name__, str(e))
            return None

    def _get_openrouteservice_route(
        self,
        source_location: Dict[str, Any],
        destination_location: Dict[str, Any],
        mode: str,
    ) -> Optional[Dict[str, Any]]:
        if not self.openrouteservice_api_key:
            return None

        source_lat = source_location.get("latitude")
        source_lon = source_location.get("longitude")
        dest_lat = destination_location.get("latitude")
        dest_lon = destination_location.get("longitude")

        if source_lat is None or source_lon is None or dest_lat is None or dest_lon is None:
            return None

        allowed_modes = {
            "driving-car",
            "driving-hgv",
            "cycling-regular",
            "foot-walking",
        }

        if mode not in allowed_modes:
            mode = "driving-car"

        url = f"{self.openrouteservice_directions_url}/{mode}/geojson"

        headers = {
            "Authorization": self.openrouteservice_api_key,
            "Content-Type": "application/json",
        }

        payload = {
            "coordinates": [
                [source_lon, source_lat],
                [dest_lon, dest_lat],
            ]
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=self.timeout,
                verify=self.ssl_verify,
            )

            response.raise_for_status()
            data = response.json()

            features = data.get("features", [])

            if not features:
                return None

            properties = features[0].get("properties", {})
            summary = properties.get("summary", {})

            distance_meters = summary.get("distance")
            duration_seconds = summary.get("duration")

            distance_km = None
            duration_hours = None

            if distance_meters is not None:
                distance_km = round(distance_meters / 1000, 2)

            if duration_seconds is not None:
                duration_hours = round(duration_seconds / 3600, 2)

            return {
                "data_source": "openrouteservice",
                "route_mode": mode,
                "distance_km": distance_km,
                "duration_hours": duration_hours,
                "duration_minutes": round(duration_seconds / 60, 1) if duration_seconds else None,
                "distance_meters": distance_meters,
                "duration_seconds": duration_seconds,
                "route_summary": summary,
                "route_available": True,
            }

        except Exception as e:
            print("[TransportService] OpenRouteService route lookup failed:")
            print(type(e).__name__, str(e))
            return None

    def _build_fallback_route_estimate(
        self,
        source_location: Dict[str, Any],
        destination_location: Dict[str, Any],
        mode: str,
    ) -> Dict[str, Any]:
        source_lat = source_location.get("latitude")
        source_lon = source_location.get("longitude")
        dest_lat = destination_location.get("latitude")
        dest_lon = destination_location.get("longitude")

        distance_km = self._haversine_distance_km(
            source_lat,
            source_lon,
            dest_lat,
            dest_lon,
        )

        road_multiplier = 1.25
        estimated_road_distance = round(distance_km * road_multiplier, 2)

        average_speed_kmph = 50

        if mode == "driving-car":
            average_speed_kmph = 55
        elif mode == "cycling-regular":
            average_speed_kmph = 15
        elif mode == "foot-walking":
            average_speed_kmph = 5

        duration_hours = round(estimated_road_distance / average_speed_kmph, 2)

        return {
            "data_source": "fallback_haversine_estimate",
            "route_mode": mode,
            "distance_km": estimated_road_distance,
            "straight_line_distance_km": round(distance_km, 2),
            "duration_hours": duration_hours,
            "duration_minutes": round(duration_hours * 60, 1),
            "route_available": False,
            "note": (
                "OpenRouteService route was unavailable. "
                "This is an approximate distance estimate using coordinates."
            ),
        }

    def optimize_route(
        self,
        points: list,
        start_index: int = 0,
    ) -> Dict[str, Any]:
        """Order a list of points (attractions in a city, or cities in a trip)
        into a short visiting sequence using nearest-neighbour on straight-line
        distance. Deterministic, needs no external API.

        Each point must be a dict containing at least ``name``, ``latitude``
        and ``longitude``. Points missing coordinates are dropped.
        """
        usable_points = [
            point
            for point in points
            if isinstance(point, dict)
            and point.get("latitude") is not None
            and point.get("longitude") is not None
        ]

        if not usable_points:
            return {
                "success": False,
                "error": "No points with usable coordinates were provided.",
                "ordered_points": [],
                "legs": [],
                "total_distance_km": 0.0,
            }

        start_index = start_index if 0 <= start_index < len(usable_points) else 0

        remaining = list(usable_points)
        current = remaining.pop(start_index)
        ordered = [current]

        while remaining:
            nearest_index = min(
                range(len(remaining)),
                key=lambda i: self._haversine_distance_km(
                    current.get("latitude"),
                    current.get("longitude"),
                    remaining[i].get("latitude"),
                    remaining[i].get("longitude"),
                ),
            )

            current = remaining.pop(nearest_index)
            ordered.append(current)

        legs = []
        total_distance_km = 0.0

        for previous_point, next_point in zip(ordered, ordered[1:]):
            distance_km = round(
                self._haversine_distance_km(
                    previous_point.get("latitude"),
                    previous_point.get("longitude"),
                    next_point.get("latitude"),
                    next_point.get("longitude"),
                ),
                2,
            )

            legs.append(
                {
                    "from": previous_point.get("name"),
                    "to": next_point.get("name"),
                    "distance_km": distance_km,
                }
            )

            total_distance_km += distance_km

        return {
            "success": True,
            "ordered_points": ordered,
            "legs": legs,
            "total_distance_km": round(total_distance_km, 2),
        }

    def _haversine_distance_km(
        self,
        lat1: Optional[float],
        lon1: Optional[float],
        lat2: Optional[float],
        lon2: Optional[float],
    ) -> float:
        if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
            return 0.0

        radius_km = 6371.0

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)

        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )

        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return radius_km * c
```

---

## File: `services/weather_service.py`

```py
from datetime import datetime
from typing import Any, Dict, Optional

import requests

from config.settings import api_settings, network_settings


class WeatherService:
    def __init__(self):
        self.geoapify_api_key = api_settings.geoapify_api_key
        self.timeout = network_settings.request_timeout
        self.ssl_verify = network_settings.geoapify_ssl_verify

        self.geoapify_geocode_url = "https://api.geoapify.com/v1/geocode/search"
        self.open_meteo_forecast_url = "https://api.open-meteo.com/v1/forecast"
        self.open_meteo_elevation_url = "https://api.open-meteo.com/v1/elevation"

    def get_climate(
        self,
        destination: str,
        month: Optional[str] = None,
        travel_dates: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        if not destination:
            return {
                "success": False,
                "error": "Destination is required for climate analysis.",
                "climate": None,
            }

        geo_data = self._geocode_location(destination)

        if not geo_data:
            return {
                "success": False,
                "error": f"Could not geocode destination: {destination}",
                "climate": None,
            }

        elevation_meters = self._get_elevation(
            latitude=geo_data.get("latitude"),
            longitude=geo_data.get("longitude"),
        )

        geo_data["elevation_meters"] = elevation_meters

        climate_data = None

        if travel_dates:
            climate_data = self._get_forecast_if_possible(
                latitude=geo_data.get("latitude"),
                longitude=geo_data.get("longitude"),
                elevation_meters=elevation_meters,
                travel_dates=travel_dates,
            )

        if not climate_data:
            climate_data = self._get_monthly_climate_indicators(
                destination=destination,
                month=month,
                geo_data=geo_data,
            )

        return {
            "success": True,
            "destination": destination,
            "month": month,
            "travel_dates": travel_dates,
            "location": geo_data,
            "climate": climate_data,
        }

    def _geocode_location(self, location: str) -> Optional[Dict[str, Any]]:
        if not self.geoapify_api_key:
            return None

        params = {
            "text": location,
            "apiKey": self.geoapify_api_key,
            "limit": 1,
            "filter": "countrycode:in",
        }

        try:
            response = requests.get(
                self.geoapify_geocode_url,
                params=params,
                timeout=self.timeout,
                verify=self.ssl_verify,
            )

            response.raise_for_status()
            data = response.json()

            features = data.get("features", [])

            if not features:
                return None

            properties = features[0].get("properties", {})
            geometry = features[0].get("geometry", {})
            coordinates = geometry.get("coordinates", [])

            lon = None
            lat = None

            if len(coordinates) >= 2:
                lon = coordinates[0]
                lat = coordinates[1]

            return {
                "formatted": properties.get("formatted"),
                "city": properties.get("city") or properties.get("name"),
                "state": properties.get("state"),
                "country": properties.get("country"),
                "latitude": lat,
                "longitude": lon,
            }

        except Exception as e:
            print("[WeatherService] Geoapify geocoding failed:")
            print(type(e).__name__, str(e))
            return None

    def _get_elevation(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
    ) -> Optional:
        if latitude is None or longitude is None:
            return None

        params = {
            "latitude": latitude,
            "longitude": longitude,
        }

        try:
            response = requests.get(
                self.open_meteo_elevation_url,
                params=params,
                timeout=self.timeout,
                verify=self.ssl_verify,
            )

            response.raise_for_status()
            data = response.json()

            elevation_values = data.get("elevation", [])

            if isinstance(elevation_values, list) and elevation_values:
                return elevation_values[0]

            if isinstance(elevation_values, (int, float)):
                return elevation_values

            return None

        except Exception as e:
            print("[WeatherService] Elevation lookup failed:")
            print(type(e).__name__, str(e))
            return None

    def _get_forecast_if_possible(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        elevation_meters: Optional[float],
        travel_dates: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        if latitude is None or longitude is None:
            return None

        start_date = travel_dates.get("start_date")
        end_date = travel_dates.get("end_date")

        if not start_date or not end_date:
            return None

        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except Exception:
            return None

        params = {
            "latitude": latitude,
            "longitude": longitude,
            "start_date": start_date,
            "end_date": end_date,
            "daily": [
                "temperature_2m_max",
                "temperature_2m_min",
                "precipitation_probability_max",
                "precipitation_sum",
            ],
            "timezone": "auto",
        }

        try:
            response = requests.get(
                self.open_meteo_forecast_url,
                params=params,
                timeout=self.timeout,
                verify=self.ssl_verify,
            )

            response.raise_for_status()
            data = response.json()
            daily = data.get("daily", {})

            max_temps = daily.get("temperature_2m_max", [])
            min_temps = daily.get("temperature_2m_min", [])
            rain_probs = daily.get("precipitation_probability_max", [])
            rain_sums = daily.get("precipitation_sum", [])

            if not max_temps or not min_temps:
                return None

            avg_max = round(sum(max_temps) / len(max_temps), 1)
            avg_min = round(sum(min_temps) / len(min_temps), 1)

            avg_rain_probability = None
            total_rain_mm = None

            if rain_probs:
                avg_rain_probability = round(sum(rain_probs) / len(rain_probs), 1)

            if rain_sums:
                total_rain_mm = round(sum(rain_sums), 1)

            return {
                "data_source": "open_meteo_forecast",
                "forecast_type": "date_specific",
                "temperature_celsius": {
                    "average_min": avg_min,
                    "average_max": avg_max,
                    "daily_min_values": min_temps,
                    "daily_max_values": max_temps,
                },
                "precipitation": {
                    "average_probability_percent": avg_rain_probability,
                    "total_rainfall_mm": total_rain_mm,
                    "daily_probability_values": rain_probs,
                    "daily_rainfall_values": rain_sums,
                },
                "terrain_indicators": {
                    "elevation_meters": elevation_meters,
                    "terrain_type": self._infer_terrain_type(elevation_meters),
                },
                "raw_daily_data": daily,
                "climate_flags": self._build_flags(
                    min_temp=avg_min,
                    max_temp=avg_max,
                    rain_probability=avg_rain_probability,
                    rainfall_mm=total_rain_mm,
                    month=None,
                    latitude=latitude,
                    longitude=longitude,
                    elevation_meters=elevation_meters,
                ),
            }

        except Exception as e:
            print("[WeatherService] Open-Meteo forecast failed:")
            print(type(e).__name__, str(e))
            return None

    def _get_monthly_climate_indicators(
        self,
        destination: str,
        month: Optional[str],
        geo_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        month_name = (month or "").strip().lower()
        latitude = geo_data.get("latitude")
        longitude = geo_data.get("longitude")
        elevation_meters = geo_data.get("elevation_meters")

        seasonal_band = self._infer_seasonal_band(month_name)

        terrain_type = self._infer_terrain_type(elevation_meters)

        region_type = self._infer_region_type(
            latitude=latitude,
            longitude=longitude,
            elevation_meters=elevation_meters,
        )

        estimated_temp = self._estimate_temperature_range(
            month=month_name,
            region_type=region_type,
            latitude=latitude,
            elevation_meters=elevation_meters,
        )

        rainfall_level = self._estimate_rainfall_level(
            month=month_name,
            region_type=region_type,
            elevation_meters=elevation_meters,
        )

        humidity_level = self._estimate_humidity_level(
            month=month_name,
            region_type=region_type,
            elevation_meters=elevation_meters,
        )

        return {
            "data_source": "seasonal_indicator_profile",
            "forecast_type": "month_level_estimate",
            "destination": destination,
            "month": month,
            "seasonal_band": seasonal_band,
            "geo_indicators": {
                "latitude": latitude,
                "longitude": longitude,
                "elevation_meters": elevation_meters,
            },
            "terrain_type": terrain_type,
            "region_type": region_type,
            "temperature_celsius": estimated_temp,
            "rainfall_level": rainfall_level,
            "humidity_level": humidity_level,
            "climate_flags": self._build_flags(
                min_temp=estimated_temp.get("estimated_min"),
                max_temp=estimated_temp.get("estimated_max"),
                rain_probability=None,
                rainfall_mm=None,
                month=month_name,
                latitude=latitude,
                longitude=longitude,
                elevation_meters=elevation_meters,
            ),
            "note": (
                "This is raw structured seasonal climate data, not a live weather forecast. "
                "Final travel advice should be generated by the final response composer."
            ),
        }

    def _infer_seasonal_band(self, month: str) -> str:
        if month in ["december", "january", "february"]:
            return "winter"

        if month in ["march", "april", "may"]:
            return "summer"

        if month in ["june", "july", "august", "september"]:
            return "monsoon"

        if month in ["october", "november"]:
            return "post_monsoon"

        return "unknown"

    def _infer_terrain_type(self, elevation_meters: Optional[float]) -> str:
        if elevation_meters is None:
            return "unknown"

        if elevation_meters >= 1500:
            return "highland"

        if elevation_meters >= 800:
            return "elevated_plateau_or_hill"

        if elevation_meters >= 300:
            return "plateau_or_inland"

        return "lowland"

    def _infer_region_type(
        self,
        latitude: Optional[float],
        longitude: Optional[float],
        elevation_meters: Optional[float],
    ) -> str:
        if elevation_meters is not None:
            if elevation_meters >= 1500:
                return "highland"
            if elevation_meters >= 800:
                return "elevated_plateau_or_hill"

        if latitude is None or longitude is None:
            return "general_india"

        if latitude >= 28:
            return "northern_region"

        if 23 <= latitude <= 29 and 68 <= longitude <= 77:
            return "dry_western_region"

        if 20 <= latitude <= 27 and longitude >= 80:
            return "eastern_humid_region"

        if 8 <= latitude <= 23 and longitude >= 72:
            return "peninsular_region"

        return "general_india"

    def _estimate_temperature_range(
        self,
        month: str,
        region_type: str,
        latitude: Optional[float],
        elevation_meters: Optional[float] = None,
    ) -> Dict[str, Any]:
        season = self._infer_seasonal_band(month)

        if elevation_meters is not None and elevation_meters >= 1500:
            if season == "winter":
                return {"estimated_min": 6, "estimated_max": 22}
            if season == "summer":
                return {"estimated_min": 12, "estimated_max": 26}
            if season == "monsoon":
                return {"estimated_min": 13, "estimated_max": 24}
            return {"estimated_min": 10, "estimated_max": 24}

        if elevation_meters is not None and elevation_meters >= 800:
            if season == "winter":
                return {"estimated_min": 10, "estimated_max": 25}
            if season == "summer":
                return {"estimated_min": 18, "estimated_max": 32}
            if season == "monsoon":
                return {"estimated_min": 18, "estimated_max": 28}
            return {"estimated_min": 15, "estimated_max": 30}

        if region_type == "dry_western_region":
            if season == "summer":
                return {"estimated_min": 26, "estimated_max": 42}
            if season == "winter":
                return {"estimated_min": 8, "estimated_max": 26}
            return {"estimated_min": 18, "estimated_max": 35}

        if region_type in ["eastern_humid_region", "peninsular_region"]:
            if season == "winter":
                return {"estimated_min": 20, "estimated_max": 31}
            if season == "summer":
                return {"estimated_min": 26, "estimated_max": 36}
            if season == "monsoon":
                return {"estimated_min": 25, "estimated_max": 34}
            return {"estimated_min": 23, "estimated_max": 33}

        if season == "winter":
            return {"estimated_min": 12, "estimated_max": 28}

        if season == "summer":
            return {"estimated_min": 25, "estimated_max": 40}

        if season == "monsoon":
            return {"estimated_min": 24, "estimated_max": 33}

        return {"estimated_min": 18, "estimated_max": 32}

    def _estimate_rainfall_level(
        self,
        month: str,
        region_type: str,
        elevation_meters: Optional[float] = None,
    ) -> str:
        season = self._infer_seasonal_band(month)

        if season == "monsoon":
            if region_type in [
                "peninsular_region",
                "eastern_humid_region",
                "highland",
                "elevated_plateau_or_hill",
            ]:
                return "high"

            return "medium"

        if season == "post_monsoon":
            if region_type in ["peninsular_region", "eastern_humid_region"]:
                return "medium"

        if season == "winter":
            return "low"

        if season == "summer":
            if region_type in ["peninsular_region", "eastern_humid_region"]:
                return "medium"

            return "low"

        return "medium"

    def _estimate_humidity_level(
        self,
        month: str,
        region_type: str,
        elevation_meters: Optional[float] = None,
    ) -> str:
        season = self._infer_seasonal_band(month)

        if region_type in ["peninsular_region", "eastern_humid_region"]:
            if season in ["summer", "monsoon", "post_monsoon"]:
                return "high"

            return "medium"

        if region_type == "dry_western_region":
            return "low"

        if season == "monsoon":
            return "high"

        return "medium"

    def _build_flags(
        self,
        min_temp: Optional[float],
        max_temp: Optional[float],
        rain_probability: Optional[float],
        rainfall_mm: Optional[float],
        month: Optional[str],
        latitude: Optional[float],
        longitude: Optional[float],
        elevation_meters: Optional[float] = None,
    ) -> Dict[str, Any]:
        monsoon_month = month in ["june", "july", "august", "september"]

        extreme_heat = False
        cold_nights = False
        rain_risk = False
        high_elevation = False

        if elevation_meters is not None and elevation_meters >= 1500:
            high_elevation = True

        if max_temp is not None and max_temp >= 36:
            extreme_heat = True

        if min_temp is not None and min_temp <= 12:
            cold_nights = True

        if rain_probability is not None and rain_probability >= 50:
            rain_risk = True

        if rainfall_mm is not None and rainfall_mm >= 20:
            rain_risk = True

        if monsoon_month:
            rain_risk = True

        return {
            "monsoon_month": monsoon_month,
            "extreme_heat": extreme_heat,
            "cold_nights": cold_nights,
            "rain_risk": rain_risk,
            "high_elevation": high_elevation,
            "latitude": latitude,
            "longitude": longitude,
            "elevation_meters": elevation_meters,
        }
```

---

## File: `services/__init__.py`

```py

```

---

