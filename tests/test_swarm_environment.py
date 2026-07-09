import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.swarm_environment import SwarmGridEnvironment
from uav_mission_agent.swarm_models import (
    DetectedTarget,
    GridPosition,
    SwarmMemory,
    SwarmMissionState,
    UAVAgentState,
)


class SwarmEnvironmentTests(unittest.TestCase):
    def test_environment_serializes_grid_features(self):
        target = DetectedTarget(
            target_id="target-heat-001",
            target_type="thermal_source",
            position=GridPosition(12, 8),
            confidence=0.86,
            detected_by="scenario",
            timestamp="scenario",
            status="unconfirmed",
        )
        environment = SwarmGridEnvironment(
            width=20,
            height=20,
            base_position=GridPosition(0, 0),
            communication_center=GridPosition(1, 1),
            communication_range=8.0,
            obstacles=[GridPosition(5, 5)],
            no_fly_zones=[GridPosition(6, 5)],
            targets=[target],
        )

        data = environment.to_dict()

        self.assertEqual(data["width"], 20)
        self.assertEqual(data["height"], 20)
        self.assertEqual(data["base_position"], {"x": 0, "y": 0})
        self.assertEqual(data["communication_center"], {"x": 1, "y": 1})
        self.assertEqual(data["communication_range"], 8.0)
        self.assertEqual(data["obstacles"], [{"x": 5, "y": 5}])
        self.assertEqual(data["no_fly_zones"], [{"x": 6, "y": 5}])
        self.assertEqual(data["targets"][0]["target_id"], "target-heat-001")

    def test_distance_and_communication_helpers_are_deterministic(self):
        environment = SwarmGridEnvironment(
            width=20,
            height=20,
            base_position=GridPosition(0, 0),
            communication_range=10.0,
        )

        self.assertEqual(
            environment.manhattan_distance(GridPosition(0, 0), GridPosition(3, 4)),
            7,
        )
        self.assertEqual(
            environment.euclidean_distance(GridPosition(0, 0), GridPosition(3, 4)),
            5.0,
        )
        self.assertTrue(environment.is_in_communication_range(GridPosition(3, 4)))
        self.assertEqual(environment.communication_quality_at(GridPosition(3, 4)), 0.5)
        self.assertFalse(environment.is_in_communication_range(GridPosition(11, 0)))
        self.assertEqual(environment.communication_quality_at(GridPosition(11, 0)), 0.0)

    def test_move_agent_toward_consumes_battery_and_uses_safe_fallback(self):
        environment = SwarmGridEnvironment(
            width=10,
            height=10,
            base_position=GridPosition(0, 0),
            communication_range=10.0,
            obstacles=[GridPosition(1, 0)],
            battery_drain_per_step=1.5,
        )
        agent = UAVAgentState(
            uav_id="UAV-1",
            role="scout",
            position=GridPosition(0, 0),
            battery_level=10.0,
            status="active",
        )

        moved = environment.move_agent_toward(agent, GridPosition(2, 1))

        self.assertEqual(moved.position.to_dict(), {"x": 0, "y": 1})
        self.assertEqual(moved.battery_level, 8.5)
        self.assertEqual(moved.communication_quality, 0.9)
        self.assertEqual(moved.status, "active")
        self.assertEqual(agent.position.to_dict(), {"x": 0, "y": 0})
        self.assertEqual(agent.battery_level, 10.0)

    def test_tick_records_low_battery_target_and_weak_communication_events(self):
        target = DetectedTarget(
            target_id="target-heat-001",
            target_type="thermal_source",
            position=GridPosition(3, 0),
            confidence=0.9,
            detected_by="scenario",
            timestamp="scenario",
            status="unconfirmed",
        )
        environment = SwarmGridEnvironment(
            width=10,
            height=10,
            base_position=GridPosition(0, 0),
            communication_range=4.0,
            targets=[target],
            battery_drain_per_step=1.0,
            low_battery_threshold=25.0,
            degraded_communication_threshold=0.5,
            discovery_range=0,
        )
        mission_state = SwarmMissionState(
            mission_id="mission-1",
            agents=[
                UAVAgentState(
                    uav_id="UAV-1",
                    role="scout",
                    position=GridPosition(2, 0),
                    battery_level=25.5,
                    status="active",
                )
            ],
            memory=SwarmMemory(),
            base_position=GridPosition(0, 0),
            phase="execution",
            grid_size={"width": 10, "height": 10},
        )

        tick = environment.tick(
            mission_state,
            {"UAV-1": GridPosition(3, 0)},
            timestamp="2026-07-09T10:00:00Z",
        )

        event_types = [event.event_type for event in tick.events]
        self.assertIn("battery_warning", event_types)
        self.assertIn("communication_degraded", event_types)
        self.assertIn("target_detected", event_types)
        self.assertEqual(mission_state.agents[0].position.to_dict(), {"x": 3, "y": 0})
        self.assertEqual(mission_state.agents[0].battery_level, 24.5)
        self.assertEqual(mission_state.agents[0].communication_quality, 0.25)
        self.assertEqual(mission_state.agents[0].status, "returning")
        self.assertEqual(mission_state.memory.targets[0].detected_by, "UAV-1")
        self.assertEqual(mission_state.memory.targets[0].timestamp, "2026-07-09T10:00:00Z")
        self.assertEqual(tick.to_dict()["detected_targets"][0]["status"], "detected")

    def test_tick_records_movement_blocked_when_no_safe_step_exists(self):
        environment = SwarmGridEnvironment(
            width=5,
            height=5,
            base_position=GridPosition(0, 0),
            obstacles=[GridPosition(1, 0)],
        )
        mission_state = SwarmMissionState(
            mission_id="mission-2",
            agents=[
                UAVAgentState(
                    uav_id="UAV-1",
                    role="scout",
                    position=GridPosition(0, 0),
                    battery_level=80.0,
                    status="active",
                )
            ],
            memory=SwarmMemory(),
            base_position=GridPosition(0, 0),
        )

        tick = environment.tick(
            mission_state,
            {"UAV-1": GridPosition(1, 0)},
            timestamp="2026-07-09T10:05:00Z",
        )

        self.assertEqual(mission_state.agents[0].position.to_dict(), {"x": 0, "y": 0})
        self.assertEqual(mission_state.agents[0].battery_level, 80.0)
        self.assertEqual(mission_state.agents[0].status, "blocked")
        self.assertEqual([event.event_type for event in tick.events], ["movement_blocked"])
        self.assertEqual(mission_state.memory.events[0].metadata["destination"], {"x": 1, "y": 0})


if __name__ == "__main__":
    unittest.main()
