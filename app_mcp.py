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