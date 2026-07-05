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


def run_query(user_query: str):
    st.session_state.messages.append(
        {
            "role": "user",
            "content": user_query,
        }
    )

    with st.spinner("Planning your trip..."):
        result = st.session_state.orchestrator.run(
            user_query=user_query,
            debug=False,
        )

    st.session_state.last_result = result

    response = result.get("response")

    if not response:
        response = result.get("error") or "I could not generate a final response."

    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response,
            "result": result,
        }
    )


def render_recommendation_buttons(result):
    summary = result.get("summary", {})
    recommendations = summary.get("destination_recommendations", [])

    if not recommendations:
        return

    st.markdown("#### Choose a destination to continue")

    cols = st.columns(2)

    for index, item in enumerate(recommendations):
        destination = item.get("destination")
        score = item.get("match_score")

        if not destination:
            continue

        label = destination

        if score:
            label = f"{destination} · {score}% match"

        with cols[index % 2]:
            if st.button(label, key=f"destination_{index}_{destination}"):
                st.session_state.pending_prompt = f"Continue with {destination}"
                st.rerun()


def render_sidebar():
    with st.sidebar:
        st.markdown("### MCP Trip Planner")

        st.markdown(
            """
            **System Flow**
            
            - Intent Analyzer  
            - Dynamic Workflow Planner  
            - Places MCP  
            - Climate MCP  
            - Transport MCP  
            - Hotel MCP  
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

            if role == "assistant":
                result = message.get("result")
                if result:
                    render_recommendation_buttons(result)


def main():
    init_state()
    render_sidebar()

    st.title("🧭 Dynamic MCP Trip Planner")
    st.caption("Plan trips using dynamic multi-agent orchestration with MCP tools.")

    render_chat()

    if st.session_state.pending_prompt:
        prompt = st.session_state.pending_prompt
        st.session_state.pending_prompt = None
        run_query(prompt)
        st.rerun()

    user_query = st.chat_input("Tell me what kind of trip you want...")

    if user_query:
        run_query(user_query)
        st.rerun()


if __name__ == "__main__":
    main()