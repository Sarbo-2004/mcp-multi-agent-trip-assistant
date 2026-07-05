import streamlit as st

from orchestrator.trip_orchestrator import TripOrchestrator


st.set_page_config(
    page_title="MCP Trip Planner",
    page_icon="🧭",
    layout="centered",
)


def init_state():
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = TripOrchestrator()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "last_result" not in st.session_state:
        st.session_state.last_result = None

    if "pending_prompt" not in st.session_state:
        st.session_state.pending_prompt = None


def _clarification_summary_text(clarification: dict) -> str:
    reason = clarification.get("reason") or "I need a bit more information to continue."
    questions = clarification.get("questions") or []
    lines = [reason]

    for question in questions:
        lines.append(f"- {question.get('question')}")

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

    with st.spinner("Planning your trip..."):
        result = st.session_state.orchestrator.run(user_query=user_query, debug=False)

    if result.get("awaiting_clarification"):
        content = _clarification_summary_text(result.get("clarification") or {})
    else:
        content = result.get("response") or result.get("error") or "I could not generate a final response."

    _record_result(content, result)


def run_answer(answers: dict):
    with st.spinner("Continuing..."):
        result = st.session_state.orchestrator.run(answer=answers, debug=False)

    if result.get("awaiting_clarification"):
        content = _clarification_summary_text(result.get("clarification") or {})
    else:
        content = result.get("response") or result.get("error") or "I could not generate a final response."

    _record_result(content, result)


def _render_question_input(question: dict):
    kind = question.get("kind", "free_text")
    options = question.get("options") or []
    widget_key = f"clarify_{question.get('id')}"
    label = question.get("question") or "Please provide more detail"

    if kind == "single_select" and options:
        labels = [option.get("label") for option in options]
        ids = [option.get("id") for option in options]
        choice = st.radio(label, labels, key=widget_key)
        return ids[labels.index(choice)] if choice in labels else None

    if kind == "multi_select" and options:
        labels = [option.get("label") for option in options]
        ids = [option.get("id") for option in options]
        chosen = st.multiselect(label, labels, key=widget_key)
        return [ids[labels.index(item)] for item in chosen]

    return st.text_input(label, key=widget_key)


def render_pending_clarification():
    """Generic form for whatever the planner is currently asking.

    Renders every ``kind`` (free_text / single_select / multi_select) the
    same way regardless of which clarification rule produced it, so new
    clarification cases never require UI changes.
    """
    last_result = st.session_state.last_result

    if not last_result or not last_result.get("awaiting_clarification"):
        return

    clarification = last_result.get("clarification") or {}
    questions = clarification.get("questions") or []

    if not questions:
        return

    st.markdown(f"##### {clarification.get('reason', 'A quick question')}")

    with st.form(key=f"clarification_form_{len(st.session_state.messages)}"):
        answers = {}

        for question in questions:
            question_id = question.get("id")
            answers[question_id] = _render_question_input(question)

        submitted = st.form_submit_button("Submit")

    if submitted:
        run_answer(answers)
        st.rerun()


def render_sidebar():
    with st.sidebar:
        st.markdown("### MCP Trip Planner")

        st.markdown(
            """
            **System Flow**

            - Intent Analyzer
            - Planner Agent (routes every step)
            - Clarification / City Selection
            - Destination · Climate · Transport · Hotel · Itinerary · Budget MCP agents
            - Replanning (feasibility gate)
            - Final Composer
            """
        )

        st.divider()

        if st.button("Clear chat"):
            st.session_state.messages = []
            st.session_state.last_result = None
            st.session_state.pending_prompt = None
            st.session_state.orchestrator = TripOrchestrator()
            st.rerun()

        st.divider()

        st.caption("Make sure all MCP servers are running before using the app.")


def render_chat():
    for message in st.session_state.messages:
        role = message.get("role")
        content = message.get("content")

        with st.chat_message(role):
            st.markdown(content)


def main():
    init_state()
    render_sidebar()

    st.title("🧭 Dynamic MCP Trip Planner")
    st.caption("Plan trips using planner-led multi-agent orchestration with MCP tools.")

    render_chat()
    render_pending_clarification()

    if st.session_state.pending_prompt:
        prompt = st.session_state.pending_prompt
        st.session_state.pending_prompt = None
        run_query(prompt)
        st.rerun()

    awaiting_clarification = bool(
        st.session_state.last_result and st.session_state.last_result.get("awaiting_clarification")
    )

    placeholder = (
        "Or type your answer here instead of using the form above..."
        if awaiting_clarification
        else "Tell me what kind of trip you want..."
    )

    user_query = st.chat_input(placeholder)

    if user_query:
        run_query(user_query)
        st.rerun()


if __name__ == "__main__":
    main()
