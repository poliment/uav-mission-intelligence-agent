import sys
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.swarm_coordinator import SwarmCoordinator
from uav_mission_agent.swarm_environment import SwarmGridEnvironment
from uav_mission_agent.swarm_models import (
    GridPosition,
    SwarmEvent,
    SwarmMemory,
    SwarmMissionState,
    UAVAgentState,
)


MISSION_TEXT = (
    "使用4架无人机搜索山区A，优先寻找疑似热源目标，其中1架保持通信中继，"
    "低电量无人机不得进入远端区域。"
)


def build_environment() -> SwarmGridEnvironment:
    return SwarmGridEnvironment(
        width=20,
        height=20,
        base_position=GridPosition(0, 0),
        communication_center=GridPosition(0, 0),
        communication_range=30.0,
        battery_drain_per_step=1.0,
        low_battery_threshold=25.0,
    )


def build_mission_state() -> SwarmMissionState:
    return SwarmMissionState(
        mission_id="mission-mountain-a",
        agents=[
            UAVAgentState(
                uav_id="UAV-1",
                role="unassigned",
                position=GridPosition(0, 0),
                battery_level=92.0,
            ),
            UAVAgentState(
                uav_id="UAV-2",
                role="unassigned",
                position=GridPosition(1, 0),
                battery_level=88.0,
            ),
            UAVAgentState(
                uav_id="UAV-3",
                role="unassigned",
                position=GridPosition(0, 1),
                battery_level=84.0,
            ),
            UAVAgentState(
                uav_id="UAV-4",
                role="unassigned",
                position=GridPosition(1, 1),
                battery_level=76.0,
            ),
        ],
        memory=SwarmMemory(),
        base_position=GridPosition(0, 0),
        grid_size={"width": 20, "height": 20},
    )


class ConflictingExplanationProvider:
    provider_name = "fake-provider"
    model = "fake-model"

    def __init__(self):
        self.calls = []

    def generate_plan(
        self,
        *,
        task,
        retrieved_knowledge,
        baseline_plan,
        output_schema,
    ):
        self.calls.append(
            {
                "task": task,
                "retrieved_knowledge": retrieved_knowledge,
                "baseline_plan": baseline_plan,
                "output_schema": output_schema,
            }
        )
        return {
            "recommendations": ["Provider advisory: keep the relay role stable."],
            "risks": ["Thermal target confirmation remains uncertain."],
            "mission_config": {
                "role_assignments": [
                    {"uav_id": "UAV-1", "role": "tracker"},
                    {"uav_id": "UAV-2", "role": "tracker"},
                ]
            },
        }


class SwarmCoordinatorMissionPlanTests(unittest.TestCase):
    def test_plan_mission_assigns_four_roles_with_algorithm_checks(self):
        mission_state = build_mission_state()

        result = SwarmCoordinator(build_environment()).plan_mission(
            MISSION_TEXT,
            mission_state,
            timestamp="2026-07-10T09:00:00Z",
        )
        data = result.to_dict()

        self.assertEqual(data["result_type"], "swarm_mission_plan")
        self.assertEqual(data["mission_id"], "mission-mountain-a")
        self.assertEqual(data["decision_source"], "offline_rules")
        self.assertEqual(data["task"]["drone_count"], 4)
        self.assertEqual(
            {assignment["role"] for assignment in data["role_assignments"]},
            {"scout", "tracker", "relay", "reserve"},
        )
        self.assertEqual(len(data["algorithm_checks"]), 4)
        self.assertTrue(all(check["path"]["reachable"] for check in data["algorithm_checks"]))
        self.assertTrue(all(check["battery"]["passed"] for check in data["algorithm_checks"]))
        self.assertTrue(
            all(check["communication"]["passed"] for check in data["algorithm_checks"])
        )
        self.assertIn("offline", data["decision_rationale"].lower())

    def test_plan_mission_updates_agents_and_memory(self):
        mission_state = build_mission_state()

        result = SwarmCoordinator(build_environment()).plan_mission(
            MISSION_TEXT,
            mission_state,
            timestamp="2026-07-10T09:00:00Z",
        )
        data = result.to_dict()

        self.assertEqual(mission_state.phase, "planned")
        self.assertTrue(all(agent.role != "unassigned" for agent in mission_state.agents))
        self.assertTrue(all(agent.current_objective for agent in mission_state.agents))
        self.assertEqual(
            [event["event_type"] for event in data["memory_updates"]],
            ["mission_started", "area_assigned", "area_assigned", "area_assigned", "area_assigned"],
        )
        self.assertEqual(len(mission_state.memory.events), 5)
        self.assertEqual(
            data["swarm_state"]["memory"]["events"],
            data["memory_updates"],
        )
        for event in data["memory_updates"][1:]:
            self.assertIn("waypoint", event["metadata"])
            self.assertIn("algorithm_checks", event["metadata"])

    def test_plan_mission_rejects_blank_mission(self):
        with self.assertRaisesRegex(ValueError, "mission_text"):
            SwarmCoordinator(build_environment()).plan_mission(
                "   ",
                build_mission_state(),
                timestamp="2026-07-10T09:00:00Z",
            )

    def test_plan_mission_rejects_empty_fleet(self):
        mission_state = SwarmMissionState(
            mission_id="mission-empty",
            agents=[],
            memory=SwarmMemory(),
            base_position=GridPosition(0, 0),
            grid_size={"width": 20, "height": 20},
        )

        with self.assertRaisesRegex(ValueError, "agent"):
            SwarmCoordinator(build_environment()).plan_mission(
                MISSION_TEXT,
                mission_state,
                timestamp="2026-07-10T09:00:00Z",
            )

    def test_provider_enhances_explanation_without_changing_offline_assignments(self):
        baseline_data = SwarmCoordinator(build_environment()).plan_mission(
            MISSION_TEXT,
            build_mission_state(),
            timestamp="2026-07-10T09:00:00Z",
        ).to_dict()
        provider = ConflictingExplanationProvider()

        enhanced_data = SwarmCoordinator(
            build_environment(),
            llm_provider=provider,
        ).plan_mission(
            MISSION_TEXT,
            build_mission_state(),
            timestamp="2026-07-10T09:00:00Z",
        ).to_dict()

        self.assertEqual(enhanced_data["decision_source"], "provider_enhanced")
        self.assertIn("Provider advisory", enhanced_data["decision_rationale"])
        self.assertEqual(
            enhanced_data["role_assignments"],
            baseline_data["role_assignments"],
        )
        self.assertEqual(
            enhanced_data["algorithm_checks"],
            baseline_data["algorithm_checks"],
        )
        self.assertEqual(
            enhanced_data["provider_advisory"]["recommendations"],
            ["Provider advisory: keep the relay role stable."],
        )
        self.assertEqual(enhanced_data["provider_advisory"]["provider"], "fake-provider")
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(
            provider.calls[0]["baseline_plan"]["role_assignments"],
            baseline_data["role_assignments"],
        )

    def test_plan_mission_generates_unique_event_ids_with_existing_memory(self):
        mission_state = build_mission_state()
        mission_state.memory.add_event(
            SwarmEvent(
                event_id="mission-mountain-a-evt-002",
                event_type="operator_note",
                message="Preloaded mission context.",
                timestamp="2026-07-10T08:55:00Z",
            )
        )

        SwarmCoordinator(build_environment()).plan_mission(
            MISSION_TEXT,
            mission_state,
            timestamp="2026-07-10T09:00:00Z",
        )

        event_ids = [event.event_id for event in mission_state.memory.events]
        self.assertEqual(len(event_ids), len(set(event_ids)))


class SwarmCoordinatorReplanTests(unittest.TestCase):
    def test_low_battery_event_returns_uav_and_hands_role_to_reserve(self):
        mission_state = build_mission_state()
        coordinator = SwarmCoordinator(build_environment())
        coordinator.plan_mission(
            MISSION_TEXT,
            mission_state,
            timestamp="2026-07-10T09:00:00Z",
        )
        self.assertEqual(mission_state.agents[0].role, "relay")
        self.assertEqual(mission_state.agents[3].role, "reserve")
        event = SwarmEvent(
            event_id="evt-low-battery",
            event_type="battery_warning",
            message="UAV-1 battery below reserve threshold.",
            timestamp="2026-07-10T09:10:00Z",
            uav_id="UAV-1",
            severity="warning",
            metadata={"battery_level": 20.0},
        )

        result = coordinator.replan_for_event(event, mission_state)
        data = result.to_dict()

        self.assertEqual(data["result_type"], "swarm_replan")
        self.assertEqual(data["decision_source"], "offline_rules")
        self.assertEqual(data["trigger_event"]["event_id"], "evt-low-battery")
        self.assertEqual(mission_state.agents[0].role, "returning")
        self.assertEqual(mission_state.agents[0].status, "returning")
        self.assertEqual(mission_state.agents[0].assigned_area, "base")
        self.assertEqual(mission_state.agents[0].battery_level, 20.0)
        self.assertEqual(mission_state.agents[3].role, "relay")
        self.assertEqual(mission_state.agents[3].assigned_area, "communication-relay")
        self.assertEqual(
            {change["uav_id"] for change in data["assignment_changes"]},
            {"UAV-1", "UAV-4"},
        )
        self.assertEqual(len(data["algorithm_checks"]), 2)
        self.assertTrue(all(check["path"]["reachable"] for check in data["algorithm_checks"]))
        self.assertEqual(
            [item["event_type"] for item in data["memory_updates"]],
            ["battery_warning", "replanning"],
        )
        self.assertEqual(mission_state.phase, "replanned")

    def test_target_detected_event_assigns_feasible_tracker_and_records_target(self):
        mission_state = build_mission_state()
        coordinator = SwarmCoordinator(build_environment())
        coordinator.plan_mission(
            MISSION_TEXT,
            mission_state,
            timestamp="2026-07-10T09:00:00Z",
        )
        event = SwarmEvent(
            event_id="evt-target-detected",
            event_type="target_detected",
            message="UAV-3 detected a high-confidence thermal source.",
            timestamp="2026-07-10T09:12:00Z",
            uav_id="UAV-3",
            target_id="target-thermal-1",
            area_id="山区A-sector-2",
            metadata={
                "target_type": "thermal_source",
                "position": {"x": 12, "y": 8},
                "confidence": 0.91,
            },
        )

        data = coordinator.replan_for_event(event, mission_state).to_dict()

        self.assertEqual(data["trigger_event"]["event_type"], "target_detected")
        self.assertEqual(len(mission_state.memory.targets), 1)
        self.assertEqual(mission_state.memory.targets[0].target_id, "target-thermal-1")
        self.assertEqual(mission_state.memory.targets[0].position.to_dict(), {"x": 12, "y": 8})
        tracker_change = data["assignment_changes"][0]
        tracker = next(
            agent for agent in mission_state.agents if agent.uav_id == tracker_change["uav_id"]
        )
        self.assertEqual(tracker.role, "tracker")
        self.assertEqual(tracker.assigned_area, "target-thermal-1")
        self.assertIn("target-thermal-1", tracker.current_objective)
        self.assertTrue(data["algorithm_checks"][0]["feasible"])
        self.assertIn("candidate score", data["role_assignments"][0]["reason"])
        self.assertEqual(
            [item["event_type"] for item in data["memory_updates"]],
            ["target_detected", "replanning"],
        )

    def test_communication_degraded_event_positions_relay_at_safe_waypoint(self):
        mission_state = build_mission_state()
        environment = build_environment()
        coordinator = SwarmCoordinator(environment)
        coordinator.plan_mission(
            MISSION_TEXT,
            mission_state,
            timestamp="2026-07-10T09:00:00Z",
        )
        affected = next(agent for agent in mission_state.agents if agent.uav_id == "UAV-3")
        affected.position = GridPosition(18, 18)
        affected.communication_quality = 0.2
        event = SwarmEvent(
            event_id="evt-communication-degraded",
            event_type="communication_degraded",
            message="UAV-3 communication quality dropped below threshold.",
            timestamp="2026-07-10T09:14:00Z",
            uav_id="UAV-3",
            severity="warning",
            metadata={"communication_quality": 0.2},
        )

        data = coordinator.replan_for_event(event, mission_state).to_dict()

        relay_change = data["assignment_changes"][0]
        relay = next(
            agent for agent in mission_state.agents if agent.uav_id == relay_change["uav_id"]
        )
        waypoint = relay_change["after"]["waypoint"]
        relay_waypoint = GridPosition(waypoint["x"], waypoint["y"])
        self.assertNotEqual(relay.uav_id, "UAV-3")
        self.assertEqual(relay.role, "relay")
        self.assertEqual(relay.assigned_area, "relay-support-UAV-3")
        self.assertGreaterEqual(
            environment.communication_quality_at(relay_waypoint),
            environment.degraded_communication_threshold,
        )
        self.assertEqual(affected.communication_quality, 0.2)
        self.assertTrue(data["algorithm_checks"][0]["feasible"])
        self.assertIn("communication", data["decision_rationale"].lower())
        self.assertEqual(
            [item["event_type"] for item in data["memory_updates"]],
            ["communication_degraded", "replanning"],
        )

    def test_later_battery_handoff_uses_waypoint_from_previous_replan(self):
        mission_state = build_mission_state()
        coordinator = SwarmCoordinator(build_environment())
        coordinator.plan_mission(
            MISSION_TEXT,
            mission_state,
            timestamp="2026-07-10T09:00:00Z",
        )
        affected = next(agent for agent in mission_state.agents if agent.uav_id == "UAV-3")
        affected.position = GridPosition(18, 18)
        communication_result = coordinator.replan_for_event(
            SwarmEvent(
                event_id="evt-communication-first",
                event_type="communication_degraded",
                message="UAV-3 communication degraded.",
                timestamp="2026-07-10T09:14:00Z",
                uav_id="UAV-3",
                severity="warning",
                metadata={"communication_quality": 0.2},
            ),
            mission_state,
        ).to_dict()
        relay_change = communication_result["assignment_changes"][0]
        relay_uav_id = relay_change["uav_id"]
        relay_waypoint = relay_change["after"]["waypoint"]

        battery_result = coordinator.replan_for_event(
            SwarmEvent(
                event_id="evt-relay-low-battery",
                event_type="battery_warning",
                message=f"{relay_uav_id} battery below reserve threshold.",
                timestamp="2026-07-10T09:18:00Z",
                uav_id=relay_uav_id,
                severity="warning",
                metadata={"battery_level": 20.0},
            ),
            mission_state,
        ).to_dict()

        handoff = next(
            change
            for change in battery_result["assignment_changes"]
            if change["uav_id"] != relay_uav_id
        )
        self.assertEqual(handoff["after"]["role"], "relay")
        self.assertEqual(handoff["after"]["assigned_area"], "relay-support-UAV-3")
        self.assertEqual(handoff["after"]["waypoint"], relay_waypoint)

    def test_replan_is_idempotent_for_an_already_processed_event(self):
        mission_state = build_mission_state()
        coordinator = SwarmCoordinator(build_environment())
        coordinator.plan_mission(
            MISSION_TEXT,
            mission_state,
            timestamp="2026-07-10T09:00:00Z",
        )
        event = SwarmEvent(
            event_id="evt-idempotent-battery",
            event_type="battery_warning",
            message="UAV-1 battery below reserve threshold.",
            timestamp="2026-07-10T09:10:00Z",
            uav_id="UAV-1",
            severity="warning",
            metadata={"battery_level": 20.0},
        )
        coordinator.replan_for_event(event, mission_state)
        state_after_first_replan = mission_state.to_dict()

        duplicate = coordinator.replan_for_event(event, mission_state).to_dict()

        self.assertEqual(duplicate["assignment_changes"], [])
        self.assertEqual(duplicate["algorithm_checks"], [])
        self.assertEqual(duplicate["memory_updates"], [])
        self.assertIn("already processed", duplicate["decision_rationale"])
        self.assertEqual(mission_state.to_dict(), state_after_first_replan)


class SwarmCoordinatorDemoTests(unittest.TestCase):
    def test_fixed_demo_returns_plan_and_event_response_outputs(self):
        demo_path = Path(__file__).resolve().parents[1] / "examples" / "swarm_coordinator_demo.py"
        spec = spec_from_file_location("swarm_coordinator_demo", demo_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        data = module.run_demo()

        self.assertEqual(data["demo_plan"]["result_type"], "swarm_mission_plan")
        self.assertEqual(data["demo_event_response"]["result_type"], "swarm_replan")
        self.assertEqual(
            data["demo_event_response"]["trigger_event"]["event_type"],
            "battery_warning",
        )
        for output in (data["demo_plan"], data["demo_event_response"]):
            self.assertTrue(output["decision_rationale"])
            self.assertTrue(output["algorithm_checks"])
            self.assertTrue(output["memory_updates"])


if __name__ == "__main__":
    unittest.main()
