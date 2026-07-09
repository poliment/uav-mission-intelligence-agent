import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.swarm_algorithms import (
    assign_targets_to_uavs,
    astar_path,
    check_battery_feasibility,
    check_communication_coverage,
    score_candidate_for_target,
)
from uav_mission_agent.swarm_environment import SwarmGridEnvironment
from uav_mission_agent.swarm_models import DetectedTarget, GridPosition, UAVAgentState


class SwarmAlgorithmTests(unittest.TestCase):
    def test_astar_path_avoids_obstacles_and_no_fly_zones(self):
        environment = SwarmGridEnvironment(
            width=5,
            height=5,
            base_position=GridPosition(0, 0),
            obstacles=[GridPosition(1, 0)],
            no_fly_zones=[GridPosition(1, 1)],
        )

        result = astar_path(environment, GridPosition(0, 0), GridPosition(2, 0))

        self.assertTrue(result.reachable)
        self.assertEqual(result.distance, 6)
        self.assertEqual(result.path[0].to_dict(), {"x": 0, "y": 0})
        self.assertEqual(result.path[-1].to_dict(), {"x": 2, "y": 0})
        self.assertNotIn({"x": 1, "y": 0}, [point.to_dict() for point in result.path])
        self.assertNotIn({"x": 1, "y": 1}, [point.to_dict() for point in result.path])
        self.assertEqual(result.reason, "path_found")
        self.assertEqual(result.to_dict()["algorithm"], "astar")

    def test_astar_path_reports_unreachable_goal(self):
        environment = SwarmGridEnvironment(
            width=3,
            height=3,
            base_position=GridPosition(0, 0),
            obstacles=[GridPosition(1, 0), GridPosition(0, 1)],
        )

        result = astar_path(environment, GridPosition(0, 0), GridPosition(2, 0))

        self.assertFalse(result.reachable)
        self.assertIsNone(result.distance)
        self.assertEqual(result.path, [])
        self.assertEqual(result.reason, "no_path")

    def test_battery_feasibility_uses_astar_distance_and_reserve(self):
        environment = SwarmGridEnvironment(
            width=5,
            height=5,
            base_position=GridPosition(0, 0),
            obstacles=[GridPosition(1, 0)],
            no_fly_zones=[GridPosition(1, 1)],
        )
        path = astar_path(environment, GridPosition(0, 0), GridPosition(2, 0))
        agent = UAVAgentState(
            uav_id="UAV-1",
            role="scout",
            position=GridPosition(0, 0),
            battery_level=15.0,
        )

        check = check_battery_feasibility(
            agent,
            path,
            battery_per_step=1.0,
            reserve_battery=10.0,
        )

        self.assertFalse(check.passed)
        self.assertEqual(check.name, "battery_feasibility")
        self.assertEqual(check.details["required_battery"], 16.0)
        self.assertEqual(check.details["remaining_after_path"], 9.0)
        self.assertIn("battery", check.to_dict()["summary"])

    def test_communication_coverage_lists_weak_path_points(self):
        environment = SwarmGridEnvironment(
            width=6,
            height=3,
            base_position=GridPosition(0, 0),
            communication_range=4.0,
        )
        path = astar_path(environment, GridPosition(0, 0), GridPosition(5, 0))

        check = check_communication_coverage(environment, path, min_quality=0.35)

        self.assertFalse(check.passed)
        self.assertEqual(check.name, "communication_coverage")
        self.assertEqual(check.details["minimum_quality"], 0.0)
        self.assertIn({"x": 3, "y": 0}, check.details["weak_points"])
        self.assertIn({"x": 5, "y": 0}, check.details["weak_points"])

    def test_candidate_scoring_prefers_closer_feasible_uav(self):
        environment = SwarmGridEnvironment(
            width=8,
            height=8,
            base_position=GridPosition(0, 0),
            communication_range=12.0,
        )
        target = DetectedTarget(
            target_id="target-1",
            target_type="thermal_source",
            position=GridPosition(2, 0),
            confidence=0.9,
            detected_by="scenario",
            timestamp="scenario",
        )
        near_agent = UAVAgentState(
            uav_id="UAV-1",
            role="scout",
            position=GridPosition(0, 0),
            battery_level=80.0,
        )
        far_agent = UAVAgentState(
            uav_id="UAV-2",
            role="scout",
            position=GridPosition(7, 7),
            battery_level=25.0,
        )

        near_score = score_candidate_for_target(near_agent, target, environment)
        far_score = score_candidate_for_target(far_agent, target, environment)

        self.assertGreater(near_score.score, far_score.score)
        self.assertTrue(near_score.battery_check.passed)
        self.assertTrue(near_score.communication_check.passed)
        self.assertIn("A*", near_score.explanation)
        self.assertEqual(near_score.to_dict()["target_id"], "target-1")

    def test_assign_targets_to_uavs_returns_explainable_records(self):
        environment = SwarmGridEnvironment(
            width=10,
            height=10,
            base_position=GridPosition(0, 0),
            communication_range=15.0,
        )
        agents = [
            UAVAgentState(
                uav_id="UAV-1",
                role="scout",
                position=GridPosition(0, 0),
                battery_level=80.0,
            ),
            UAVAgentState(
                uav_id="UAV-2",
                role="tracker",
                position=GridPosition(9, 9),
                battery_level=80.0,
            ),
        ]
        targets = [
            DetectedTarget(
                target_id="target-a",
                target_type="thermal_source",
                position=GridPosition(1, 0),
                confidence=0.8,
                detected_by="scenario",
                timestamp="scenario",
            ),
            DetectedTarget(
                target_id="target-b",
                target_type="vehicle",
                position=GridPosition(8, 9),
                confidence=0.85,
                detected_by="scenario",
                timestamp="scenario",
            ),
        ]

        assignments = assign_targets_to_uavs(agents, targets, environment)

        self.assertEqual([assignment.target_id for assignment in assignments], ["target-a", "target-b"])
        self.assertEqual([assignment.uav_id for assignment in assignments], ["UAV-1", "UAV-2"])
        self.assertGreater(assignments[0].score, 0)
        self.assertEqual(assignments[0].path.path[-1].to_dict(), {"x": 1, "y": 0})
        self.assertIn("assigned", assignments[0].reason)
        self.assertEqual(assignments[0].to_dict()["path"]["algorithm"], "astar")


if __name__ == "__main__":
    unittest.main()
