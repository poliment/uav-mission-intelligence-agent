from __future__ import annotations

import math
from typing import Any


PLOTLY_INSTALL_HINT = (
    "Swarm visualization requires Plotly; install the demo dependencies with "
    'pip install -e ".[demo]"'
)

ROLE_COLORS = {
    "scout": "#1677ff",
    "tracker": "#d64545",
    "relay": "#168a83",
    "reserve": "#d99100",
    "returning": "#7b61a8",
    "unassigned": "#667085",
}


def build_swarm_grid_figure(
    session: Any,
    *,
    mission_state: Any | None = None,
    assignments: dict[str, Any] | None = None,
):
    try:
        import plotly.graph_objects as go
    except ModuleNotFoundError as exc:
        raise RuntimeError(PLOTLY_INSTALL_HINT) from exc

    environment = session.environment
    mission_state = mission_state if mission_state is not None else session.mission_state
    assignments = assignments if assignments is not None else session.current_assignments
    figure = go.Figure()

    center = environment.communication_center
    circle_angles = [index * (2 * math.pi / 72) for index in range(73)]
    figure.add_trace(
        go.Scatter(
            name="Communication range",
            x=[center.x + environment.communication_range * math.cos(angle) for angle in circle_angles],
            y=[center.y + environment.communication_range * math.sin(angle) for angle in circle_angles],
            mode="lines",
            line={"color": "#78a9c4", "dash": "dot", "width": 1.5},
            hoverinfo="skip",
        )
    )

    _add_position_trace(
        figure,
        go,
        name="Obstacles",
        positions=environment.obstacles,
        symbol="square",
        color="#344054",
        size=12,
    )
    _add_position_trace(
        figure,
        go,
        name="No-fly zones",
        positions=environment.no_fly_zones,
        symbol="x",
        color="#c11574",
        size=14,
    )

    base = environment.base_position
    figure.add_trace(
        go.Scatter(
            name="Base",
            x=[base.x],
            y=[base.y],
            mode="markers+text",
            text=["BASE"],
            textposition="top right",
            marker={
                "symbol": "diamond",
                "size": 17,
                "color": "#111927",
                "line": {"color": "white", "width": 1},
            },
            hovertemplate="Base (%{x}, %{y})<extra></extra>",
        )
    )

    targets = mission_state.memory.targets or []
    figure.add_trace(
        go.Scatter(
            name="Discovered targets",
            x=[target.position.x for target in targets],
            y=[target.position.y for target in targets],
            mode="markers+text",
            text=[target.target_id for target in targets],
            textposition="top center",
            customdata=[
                [target.target_type, target.confidence, target.detected_by]
                for target in targets
            ],
            marker={
                "symbol": "star",
                "size": 17,
                "color": "#e5484d",
                "line": {"color": "#7a0916", "width": 1},
            },
            hovertemplate=(
                "Target %{text}<br>Type: %{customdata[0]}<br>"
                "Confidence: %{customdata[1]:.2f}<br>Detected by: %{customdata[2]}"
                "<extra></extra>"
            ),
        )
    )

    for uav_id, assignment in sorted(assignments.items()):
        if not assignment.path.reachable:
            continue
        path = assignment.path.path
        figure.add_trace(
            go.Scatter(
                name=f"Path - {uav_id}",
                x=[position.x for position in path],
                y=[position.y for position in path],
                mode="lines",
                line={
                    "color": ROLE_COLORS.get(assignment.role, ROLE_COLORS["unassigned"]),
                    "width": 2,
                },
                opacity=0.72,
                hovertemplate=f"{uav_id} path (%{{x}}, %{{y}})<extra></extra>",
            )
        )

    agents = sorted(mission_state.agents, key=lambda agent: agent.uav_id)
    figure.add_trace(
        go.Scatter(
            name="UAVs",
            x=[agent.position.x for agent in agents],
            y=[agent.position.y for agent in agents],
            mode="markers+text",
            text=[agent.uav_id for agent in agents],
            textposition="bottom center",
            customdata=[
                [
                    agent.uav_id,
                    agent.role,
                    agent.battery_level,
                    agent.communication_quality,
                    agent.status,
                ]
                for agent in agents
            ],
            marker={
                "symbol": "triangle-up",
                "size": 16,
                "color": [
                    ROLE_COLORS.get(agent.role, ROLE_COLORS["unassigned"])
                    for agent in agents
                ],
                "line": {"color": "white", "width": 1.5},
            },
            hovertemplate=(
                "%{customdata[0]}<br>Role: %{customdata[1]}<br>"
                "Battery: %{customdata[2]:.0f}%<br>Link: %{customdata[3]:.2f}<br>"
                "Status: %{customdata[4]}<extra></extra>"
            ),
        )
    )

    figure.update_layout(
        height=620,
        template="plotly_white",
        margin={"l": 30, "r": 20, "t": 30, "b": 30},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "x": 0},
        hovermode="closest",
        xaxis={
            "title": "Grid X",
            "range": [0, 20],
            "dtick": 2,
            "fixedrange": True,
            "showgrid": True,
        },
        yaxis={
            "title": "Grid Y",
            "range": [0, 20],
            "dtick": 2,
            "fixedrange": True,
            "showgrid": True,
            "scaleanchor": "x",
            "scaleratio": 1,
        },
    )
    return figure


def _add_position_trace(
    figure: Any,
    go: Any,
    *,
    name: str,
    positions: list[Any],
    symbol: str,
    color: str,
    size: int,
) -> None:
    figure.add_trace(
        go.Scatter(
            name=name,
            x=[position.x for position in positions],
            y=[position.y for position in positions],
            mode="markers",
            marker={"symbol": symbol, "size": size, "color": color},
            hovertemplate=f"{name} (%{{x}}, %{{y}})<extra></extra>",
        )
    )
