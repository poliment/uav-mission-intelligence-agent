from __future__ import annotations

import builtins
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.swarm_coordinator import SwarmCoordinator
from uav_mission_agent.swarm_demo import create_swarm_demo_session
from uav_mission_agent.swarm_environment import SwarmGridEnvironment
from uav_mission_agent.swarm_models import (
    DetectedTarget,
    GridPosition,
    SwarmMemory,
    SwarmMissionState,
    UAVAgentState,
)
from uav_mission_agent.swarm_visualization import build_swarm_grid_figure


try:
    import plotly  # noqa: F401
    PLOTLY_AVAILABLE = True
except ModuleNotFoundError:
    PLOTLY_AVAILABLE = False


def build_demo_session() -> SimpleNamespace:
    target = DetectedTarget(
        target_id="thermal-1",
        target_type="thermal_source",
        position=GridPosition(12, 8),
        confidence=0.91,
        detected_by="UAV-1",
        timestamp="2026-07-10T10:05:00Z",
        status="detected",
    )
    environment = SwarmGridEnvironment(
        width=20,
        height=20,
        base_position=GridPosition(0, 0),
        communication_center=GridPosition(0, 0),
        communication_range=8.0,
        obstacles=[GridPosition(6, 5), GridPosition(6, 6)],
        no_fly_zones=[GridPosition(8, 8)],
        targets=[target],
        battery_drain_per_step=1.0,
        low_battery_threshold=25.0,
    )
    mission_state = SwarmMissionState(
        mission_id="visualization-demo",
        agents=[
            UAVAgentState("UAV-1", "unassigned", GridPosition(0, 0), 96.0),
            UAVAgentState("UAV-2", "unassigned", GridPosition(1, 0), 92.0),
            UAVAgentState("UAV-3", "unassigned", GridPosition(0, 1), 88.0),
            UAVAgentState("UAV-4", "unassigned", GridPosition(1, 1), 84.0),
        ],
        memory=SwarmMemory(targets=[target]),
        base_position=GridPosition(0, 0),
        grid_size={"width": 20, "height": 20},
    )
    plan = SwarmCoordinator(environment).plan_mission(
        "Use 4 UAVs to search area A, track a thermal target, and maintain a relay.",
        mission_state,
        timestamp="2026-07-10T10:00:00Z",
    )
    return SimpleNamespace(
        environment=environment,
        mission_state=mission_state,
        initial_plan=plan,
        current_assignments={
            assignment.uav_id: assignment for assignment in plan.role_assignments
        },
    )


class SwarmVisualizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.session = build_demo_session()

    @unittest.skipUnless(PLOTLY_AVAILABLE, "Plotly is not installed")
    def test_figure_covers_every_map_element_and_reachable_assignment_path(self):
        figure = build_swarm_grid_figure(self.session)
        traces = {trace.name: trace for trace in figure.data}

        self.assertEqual(len(traces["Base"].x), 1)
        self.assertEqual(
            len(traces["Obstacles"].x),
            len(self.session.environment.obstacles),
        )
        self.assertEqual(
            len(traces["No-fly zones"].x),
            len(self.session.environment.no_fly_zones),
        )
        self.assertGreater(len(traces["Communication range"].x), 20)
        self.assertTrue(
            any(
                0 <= x <= 20 and 0 <= y <= 20
                for x, y in zip(
                    traces["Communication range"].x,
                    traces["Communication range"].y,
                )
            )
        )
        self.assertEqual(
            len(traces["Discovered targets"].x),
            len(self.session.mission_state.memory.targets),
        )

        reachable = [
            assignment
            for assignment in self.session.current_assignments.values()
            if assignment.path.reachable
        ]
        self.assertTrue(reachable)
        for assignment in reachable:
            path_trace = traces[f"Path - {assignment.uav_id}"]
            self.assertEqual(len(path_trace.x), len(assignment.path.path))
            self.assertGreater(len(path_trace.x), 0)

    @unittest.skipUnless(PLOTLY_AVAILABLE, "Plotly is not installed")
    def test_figure_uses_stable_20_by_20_equal_aspect_axes(self):
        figure = build_swarm_grid_figure(self.session)

        self.assertEqual(list(figure.layout.xaxis.range), [0, 20])
        self.assertEqual(list(figure.layout.yaxis.range), [0, 20])
        self.assertEqual(figure.layout.yaxis.scaleanchor, "x")
        self.assertEqual(figure.layout.yaxis.scaleratio, 1)

    @unittest.skipUnless(PLOTLY_AVAILABLE, "Plotly is not installed")
    def test_default_demo_communication_boundary_is_visible_in_grid(self):
        figure = build_swarm_grid_figure(create_swarm_demo_session())
        communication = next(
            trace for trace in figure.data if trace.name == "Communication range"
        )

        self.assertTrue(
            any(
                0 <= x <= 20 and 0 <= y <= 20
                for x, y in zip(communication.x, communication.y)
            )
        )

    @unittest.skipUnless(PLOTLY_AVAILABLE, "Plotly is not installed")
    def test_figure_renders_four_uavs_with_role_colors_and_hover_details(self):
        figure = build_swarm_grid_figure(self.session)
        uav_trace = next(trace for trace in figure.data if trace.name == "UAVs")

        self.assertEqual(len(uav_trace.x), 4)
        self.assertEqual(len(uav_trace.y), 4)
        self.assertEqual(len(uav_trace.marker.color), 4)
        self.assertEqual(
            len(set(uav_trace.marker.color)),
            len({agent.role for agent in self.session.mission_state.agents}),
        )
        self.assertIn("Role", uav_trace.hovertemplate)
        self.assertEqual(
            {row[0] for row in uav_trace.customdata},
            {agent.uav_id for agent in self.session.mission_state.agents},
        )

    def test_missing_plotly_raises_clear_demo_extra_install_hint(self):
        real_import = builtins.__import__

        def import_without_plotly(name, *args, **kwargs):
            if name == "plotly" or name.startswith("plotly."):
                raise ModuleNotFoundError("No module named 'plotly'")
            return real_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=import_without_plotly):
            with self.assertRaisesRegex(RuntimeError, r"\.\[demo\]"):
                build_swarm_grid_figure(self.session)


if __name__ == "__main__":
    unittest.main()
