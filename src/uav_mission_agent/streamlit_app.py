from __future__ import annotations

import json
from typing import Any

import streamlit as st

from uav_mission_agent.demo_service import (
    DemoError,
    build_mission_demo_payload,
    load_demo_benchmark,
)
from uav_mission_agent.llm_provider import LLMProviderError, build_llm_provider
from uav_mission_agent.swarm_demo import (
    DEFAULT_SWARM_DEMO_MISSION,
    DEMO_EVENT_ORDER,
    SwarmDemoSession,
    create_swarm_demo_session,
)
from uav_mission_agent.swarm_visualization import build_swarm_grid_figure


VIEWS = (
    "Swarm Plan",
    "Event Response",
    "Agent Dialogue",
    "Mission Intelligence",
    "Evaluation",
)
PROVIDERS = ("offline", "deepseek", "openai-compatible")


def main() -> None:
    st.set_page_config(
        page_title="UAV Swarm Mission Console",
        page_icon=None,
        layout="wide",
        initial_sidebar_state="auto",
    )
    _ensure_session_defaults()
    _render_sidebar()

    session: SwarmDemoSession = st.session_state["swarm_demo_session"]
    st.title("UAV Swarm Mission Console")
    st.caption("确定性群体任务规划、事件响应与多 Agent 协作演示。")
    metrics_slot = st.empty()

    view = st.radio("View", VIEWS, horizontal=True, key="active_view")
    if view == "Swarm Plan":
        _render_swarm_plan(session)
    elif view == "Event Response":
        _render_event_response(session)
    elif view == "Agent Dialogue":
        _render_agent_dialogue(session)
    elif view == "Mission Intelligence":
        _render_mission_intelligence(session)
    else:
        _render_evaluation()

    with metrics_slot.container():
        _render_metrics(session)


def _ensure_session_defaults() -> None:
    if "mission_text_input" not in st.session_state:
        st.session_state["mission_text_input"] = DEFAULT_SWARM_DEMO_MISSION
    if "provider_input" not in st.session_state:
        st.session_state["provider_input"] = "offline"
    if "active_provider" not in st.session_state:
        st.session_state["active_provider"] = "offline"
    if "swarm_demo_session" not in st.session_state:
        st.session_state["swarm_demo_session"] = create_swarm_demo_session(
            st.session_state["mission_text_input"]
        )


def _render_sidebar() -> None:
    with st.sidebar:
        st.header("Mission Setup")
        st.caption("配置任务并创建新的共享会话；凭据仅从环境变量读取。")
        mission_text = st.text_area(
            "Mission text",
            height=150,
            key="mission_text_input",
        )
        provider = st.selectbox("Provider", PROVIDERS, key="provider_input")
        model: str | None = None
        base_url: str | None = None
        if provider != "offline":
            model = st.text_input(
                "Model",
                value=_provider_default_model(provider),
                key="model_input",
            )
            base_url = st.text_input(
                "Base URL",
                value=_provider_default_base_url(provider),
                key="base_url_input",
            )

        initialize_column, reset_column = st.columns(2)
        initialize = initialize_column.button(
            "Initialize Mission",
            type="primary",
            use_container_width=True,
        )
        reset_column.button(
            "Reset",
            use_container_width=True,
            on_click=_reset_demo_state,
        )

        if initialize:
            try:
                llm_provider = build_llm_provider(
                    provider,
                    model=_blank_to_none(model),
                    base_url=_blank_to_none(base_url),
                )
                candidate = create_swarm_demo_session(
                    mission_text,
                    llm_provider=llm_provider,
                )
            except (DemoError, LLMProviderError, ValueError) as exc:
                st.error(_safe_error_message(exc))
            else:
                st.session_state["swarm_demo_session"] = candidate
                st.session_state["active_view"] = "Swarm Plan"
                st.session_state.pop("mission_intelligence_payload", None)
                advisory = candidate.initial_plan.provider_advisory or {}
                if advisory.get("status") == "offline_fallback":
                    st.session_state["active_provider"] = "offline fallback"
                    st.warning(
                        "Offline fallback: provider enhancement was unavailable, "
                        "so the deterministic plan was initialized."
                    )
                else:
                    st.session_state["active_provider"] = provider
                    st.success("Mission session initialized.")

        st.divider()
        st.caption("Events and dialogue remain offline and deterministic.")


def _reset_demo_state() -> None:
    st.session_state["mission_text_input"] = DEFAULT_SWARM_DEMO_MISSION
    st.session_state["provider_input"] = "offline"
    st.session_state["active_provider"] = "offline"
    st.session_state["active_view"] = "Swarm Plan"
    st.session_state.pop("model_input", None)
    st.session_state.pop("base_url_input", None)
    st.session_state.pop("mission_intelligence_payload", None)
    st.session_state.pop("benchmark_payload", None)
    st.session_state["swarm_demo_session"] = create_swarm_demo_session()


def _render_metrics(session: SwarmDemoSession) -> None:
    active_uavs = sum(agent.status != "returning" for agent in session.mission_state.agents)
    message_count = sum(len(result.messages) for result in session.event_results)
    columns = st.columns(5)
    columns[0].metric("Phase", session.mission_state.phase.title())
    columns[1].metric("Active UAVs", active_uavs)
    columns[2].metric("Events", f"{len(session.event_results)}/{len(DEMO_EVENT_ORDER)}")
    columns[3].metric("Messages", message_count)
    columns[4].metric("Provider", st.session_state.get("active_provider", "offline"))


def _render_swarm_plan(session: SwarmDemoSession) -> None:
    st.header("Swarm Plan")
    st.caption("查看初始角色、算法约束与固定 20×20 任务空间。")
    initial_assignments = {
        assignment.uav_id: assignment
        for assignment in session.initial_plan.role_assignments
    }
    map_column, plan_column = st.columns((3, 2), gap="large")
    with map_column:
        st.plotly_chart(
            build_swarm_grid_figure(
                session,
                mission_state=session.initial_plan.swarm_state,
                assignments=initial_assignments,
            ),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with plan_column:
        st.subheader("Role assignments")
        st.dataframe(
            _role_rows(session.initial_plan.role_assignments),
            use_container_width=True,
            hide_index=True,
        )
        st.subheader("Algorithm checks")
        st.dataframe(
            _algorithm_rows(session.initial_plan.role_assignments),
            use_container_width=True,
            hide_index=True,
        )

    with st.expander("Decision rationale", expanded=True):
        st.write(session.initial_plan.decision_rationale)
        if session.initial_plan.provider_advisory:
            st.json(session.initial_plan.provider_advisory)


def _render_event_response(session: SwarmDemoSession) -> None:
    st.header("Event Response")
    st.caption("按固定顺序推进目标发现、低电量与通信降级事件。")
    process_column, run_column, status_column = st.columns((1, 1, 3))
    process_next = process_column.button(
        "Process next event",
        disabled=session.next_event_type is None,
        use_container_width=True,
    )
    run_remaining = run_column.button(
        "Run remaining",
        disabled=session.next_event_type is None,
        use_container_width=True,
    )
    if process_next:
        try:
            session.process_next_event()
        except (ValueError, RuntimeError) as exc:
            st.error(_safe_error_message(exc))
    if run_remaining:
        try:
            session.run_remaining_events()
        except (ValueError, RuntimeError) as exc:
            st.error(_safe_error_message(exc))

    next_event = session.next_event_type or "complete"
    status_column.caption(f"Next event: {next_event}")
    st.dataframe(
        _event_queue_rows(session),
        use_container_width=True,
        hide_index=True,
    )

    map_column, response_column = st.columns((3, 2), gap="large")
    with map_column:
        st.plotly_chart(
            build_swarm_grid_figure(session),
            use_container_width=True,
            config={"displayModeBar": False},
        )
    with response_column:
        if not session.event_results:
            st.info("No event has been processed yet.")
        else:
            latest = session.event_results[-1]
            st.subheader("Latest response")
            st.write(latest.coordinator_summary)
            st.dataframe(
                _assignment_change_rows(latest.coordination_result.assignment_changes),
                use_container_width=True,
                hide_index=True,
            )
            st.subheader("Replanning memory")
            st.dataframe(
                _replanning_memory_rows(session),
                use_container_width=True,
                hide_index=True,
            )


def _render_agent_dialogue(session: SwarmDemoSession) -> None:
    st.header("Agent Dialogue")
    timeline = [
        message
        for result in session.event_results
        for message in result.messages
    ]
    st.caption(f"{len(timeline)} structured messages with deterministic memory links.")
    if not timeline:
        st.info("Process events to populate the agent dialogue.")
    else:
        st.dataframe(
            [
                {
                    "time": message.timestamp,
                    "sender": message.sender_id,
                    "recipients": ", ".join(message.recipient_ids),
                    "type": message.message_type,
                    "content": message.content,
                    "memory_id": message.memory_event_id,
                }
                for message in timeline
            ],
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Coordinator summaries")
    for result in session.event_results:
        st.write(f"{result.trigger_event.event_type}: {result.coordinator_summary}")

    st.subheader("Memory links")
    st.dataframe(
        _message_memory_rows(session),
        use_container_width=True,
        hide_index=True,
    )


def _render_mission_intelligence(session: SwarmDemoSession) -> None:
    st.header("Mission Intelligence")
    st.caption("保留单任务 Agent 工作流、执行图与结构化计划。")
    cached = st.session_state.get("mission_intelligence_payload")
    if not cached or cached.get("mission_text") != session.mission_text:
        try:
            cached = build_mission_demo_payload(session.mission_text, provider="offline")
        except (DemoError, LLMProviderError, ValueError) as exc:
            st.error(_safe_error_message(exc))
            return
        st.session_state["mission_intelligence_payload"] = cached

    visualization_column, trace_column = st.columns((3, 2), gap="large")
    with visualization_column:
        st.image(
            cached["mission_svg"],
            caption="Mission execution visualization",
            use_column_width=True,
        )
    with trace_column:
        st.subheader("Agent trace")
        st.dataframe(
            cached.get("agent_trace", []),
            use_container_width=True,
            hide_index=True,
        )
        st.subheader("Validation")
        st.json(cached.get("schema_validation", {}))

    with st.expander("Structured mission JSON"):
        st.code(cached["json_plan"], language="json")


def _render_evaluation() -> None:
    st.header("Evaluation")
    st.caption("展示离线基准结果与 provider 对比，不触发在线请求。")
    if "benchmark_payload" not in st.session_state:
        try:
            st.session_state["benchmark_payload"] = load_demo_benchmark()
        except (OSError, ValueError) as exc:
            st.error(_safe_error_message(exc))
            return
    payload = st.session_state["benchmark_payload"]
    summary = payload.get("summary", {})
    columns = st.columns(3)
    columns[0].metric("Scenarios", summary.get("total_scenarios", 0))
    columns[1].metric("Benchmark", summary.get("benchmark_version", "offline"))
    columns[2].metric("Source", payload.get("source", "offline"))
    st.subheader("Provider comparison")
    st.dataframe(
        payload.get("provider_comparison", []),
        use_container_width=True,
        hide_index=True,
    )
    st.subheader("Difficulty summary")
    st.dataframe(
        payload.get("difficulty_summary", []),
        use_container_width=True,
        hide_index=True,
    )
    with st.expander("Benchmark JSON"):
        st.code(payload.get("json_report", "{}"), language="json")


def _role_rows(assignments: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "UAV": assignment.uav_id,
            "role": assignment.role,
            "area": assignment.assigned_area,
            "objective": assignment.objective,
            "waypoint": f"({assignment.waypoint.x}, {assignment.waypoint.y})",
            "feasible": assignment.feasible,
        }
        for assignment in assignments
    ]


def _algorithm_rows(assignments: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "UAV": assignment.uav_id,
            "A*": assignment.path.reachable,
            "distance": assignment.path.distance,
            "battery": assignment.battery_check.passed,
            "communication": assignment.communication_check.passed,
        }
        for assignment in assignments
    ]


def _event_queue_rows(session: SwarmDemoSession) -> list[dict[str, str]]:
    processed = len(session.event_results)
    return [
        {
            "order": str(index + 1),
            "event": event_type,
            "status": (
                "processed"
                if index < processed
                else "next"
                if index == processed
                else "pending"
            ),
        }
        for index, event_type in enumerate(DEMO_EVENT_ORDER)
    ]


def _assignment_change_rows(changes: list[Any]) -> list[dict[str, str]]:
    return [
        {
            "UAV": change.uav_id,
            "before": json.dumps(change.before, ensure_ascii=False),
            "after": json.dumps(change.after, ensure_ascii=False),
            "reason": change.reason,
        }
        for change in changes
    ]


def _replanning_memory_rows(session: SwarmDemoSession) -> list[dict[str, Any]]:
    return [
        {
            "memory_id": event.event_id,
            "time": event.timestamp,
            "UAV": event.uav_id,
            "trigger": event.metadata.get("trigger_event_id"),
            "message": event.message,
        }
        for event in session.mission_state.memory.events_by_type("replanning")
    ]


def _message_memory_rows(session: SwarmDemoSession) -> list[dict[str, Any]]:
    return [
        {
            "memory_id": event.event_id,
            "message_id": event.metadata.get("message_id"),
            "sender": event.metadata.get("sender_id"),
            "type": event.metadata.get("message_type"),
            "trigger": event.metadata.get("trigger_event_id"),
        }
        for event in session.mission_state.memory.events_by_type("agent_message")
    ]


def _provider_default_model(provider: str) -> str:
    if provider == "deepseek":
        return "deepseek-v4-flash"
    return "gpt-4o-mini"


def _provider_default_base_url(provider: str) -> str:
    if provider == "deepseek":
        return "https://api.deepseek.com"
    return "https://api.openai.com/v1"


def _blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _safe_error_message(exc: Exception) -> str:
    return str(exc).replace("Bearer ", "Bearer [redacted] ")


if __name__ == "__main__":
    main()
