import sys
import unittest
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.swarm_coordinator import SwarmCoordinator
from uav_mission_agent.swarm_dialogue import SwarmAgentMessage, SwarmDialogueEngine
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
        mission_id="dialogue-mountain-a",
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


def plan_mission(
    coordinator: SwarmCoordinator,
    mission_state: SwarmMissionState,
) -> None:
    coordinator.plan_mission(
        MISSION_TEXT,
        mission_state,
        timestamp="2026-07-10T10:00:00Z",
    )


class SwarmAgentMessageTests(unittest.TestCase):
    def test_message_serializes_routing_cause_and_memory_link_defensively(self):
        message = SwarmAgentMessage(
            message_id="mission-1-msg-001",
            timestamp="2026-07-10T10:00:00Z",
            sender_id="UAV-1",
            recipient_ids=["SWARM-COORDINATOR", "UAV-2"],
            message_type="target_report",
            content="Thermal target detected at (12, 8).",
            trigger_event_id="evt-target-1",
            related_uav_id="UAV-2",
            target_id="target-1",
            memory_event_id="mission-1-dialogue-001",
            metadata={"position": {"x": 12, "y": 8}, "confidence": 0.91},
        )

        data = message.to_dict()

        self.assertEqual(
            data,
            {
                "message_id": "mission-1-msg-001",
                "timestamp": "2026-07-10T10:00:00Z",
                "sender_id": "UAV-1",
                "recipient_ids": ["SWARM-COORDINATOR", "UAV-2"],
                "message_type": "target_report",
                "content": "Thermal target detected at (12, 8).",
                "trigger_event_id": "evt-target-1",
                "related_uav_id": "UAV-2",
                "target_id": "target-1",
                "memory_event_id": "mission-1-dialogue-001",
                "metadata": {
                    "position": {"x": 12, "y": 8},
                    "confidence": 0.91,
                },
            },
        )
        data["recipient_ids"].append("UAV-3")
        data["metadata"]["position"]["x"] = 99

        self.assertEqual(message.recipient_ids, ["SWARM-COORDINATOR", "UAV-2"])
        self.assertEqual(message.metadata["position"], {"x": 12, "y": 8})


class SwarmDialogueEngineTests(unittest.TestCase):
    def test_target_event_creates_report_acknowledgement_and_summary_with_memory_links(self):
        mission_state = build_mission_state()
        coordinator = SwarmCoordinator(build_environment())
        plan_mission(coordinator, mission_state)
        event = SwarmEvent(
            event_id="evt-dialogue-target",
            event_type="target_detected",
            message="UAV-3 detected a thermal source.",
            timestamp="2026-07-10T10:05:00Z",
            uav_id="UAV-3",
            target_id="target-thermal-1",
            area_id="山区A-sector-2",
            metadata={
                "target_type": "thermal_source",
                "position": {"x": 12, "y": 8},
                "confidence": 0.91,
            },
        )

        data = SwarmDialogueEngine(coordinator).coordinate_event(
            event,
            mission_state,
        ).to_dict()

        self.assertEqual(data["result_type"], "swarm_dialogue")
        self.assertEqual(
            [message["message_type"] for message in data["messages"]],
            ["target_report", "task_acknowledgement", "coordination_summary"],
        )
        selected_uav = data["coordination_result"]["assignment_changes"][0]["uav_id"]
        self.assertEqual(data["messages"][0]["sender_id"], "UAV-3")
        self.assertEqual(data["messages"][0]["recipient_ids"], ["SWARM-COORDINATOR"])
        self.assertEqual(data["messages"][1]["sender_id"], selected_uav)
        self.assertIn("UAV-3", data["messages"][1]["recipient_ids"])
        self.assertEqual(data["messages"][2]["sender_id"], "SWARM-COORDINATOR")
        self.assertEqual(
            data["messages"][2]["recipient_ids"],
            ["UAV-1", "UAV-2", "UAV-3", "UAV-4"],
        )
        self.assertEqual(
            data["algorithm_checks"],
            data["coordination_result"]["algorithm_checks"],
        )
        self.assertEqual(len(data["memory_updates"]), 3)
        self.assertEqual(
            [event["event_type"] for event in data["memory_updates"]],
            ["agent_message", "agent_message", "agent_message"],
        )
        for message, memory_event in zip(data["messages"], data["memory_updates"]):
            self.assertEqual(message["memory_event_id"], memory_event["event_id"])
            self.assertEqual(memory_event["metadata"]["message_id"], message["message_id"])
            self.assertEqual(memory_event["metadata"]["trigger_event_id"], event.event_id)
        for agent in mission_state.agents:
            self.assertIn(data["messages"][2]["memory_event_id"], agent.memory_refs)

    def test_tracker_acknowledgement_does_not_address_its_own_sender(self):
        mission_state = build_mission_state()
        coordinator = SwarmCoordinator(build_environment())
        plan_mission(coordinator, mission_state)
        event = SwarmEvent(
            event_id="evt-dialogue-self-target",
            event_type="target_detected",
            message="UAV-1 detected a target at its current position.",
            timestamp="2026-07-10T10:06:00Z",
            uav_id="UAV-1",
            target_id="target-near-uav-1",
            metadata={
                "target_type": "thermal_source",
                "position": {"x": 0, "y": 0},
                "confidence": 0.95,
            },
        )

        data = SwarmDialogueEngine(coordinator).coordinate_event(
            event,
            mission_state,
        ).to_dict()

        acknowledgement = data["messages"][1]
        self.assertEqual(acknowledgement["sender_id"], "UAV-1")
        self.assertEqual(acknowledgement["recipient_ids"], ["SWARM-COORDINATOR"])

    def test_battery_event_creates_status_handoff_and_summary_from_real_changes(self):
        mission_state = build_mission_state()
        coordinator = SwarmCoordinator(build_environment())
        plan_mission(coordinator, mission_state)
        event = SwarmEvent(
            event_id="evt-dialogue-battery",
            event_type="battery_warning",
            message="UAV-1 battery below reserve threshold.",
            timestamp="2026-07-10T10:08:00Z",
            uav_id="UAV-1",
            severity="warning",
            metadata={"battery_level": 20.0},
        )

        data = SwarmDialogueEngine(coordinator).coordinate_event(
            event,
            mission_state,
        ).to_dict()

        self.assertEqual(
            [message["message_type"] for message in data["messages"]],
            ["battery_status", "task_handoff", "coordination_summary"],
        )
        self.assertEqual(data["messages"][0]["sender_id"], "UAV-1")
        replacement_change = next(
            change
            for change in data["coordination_result"]["assignment_changes"]
            if change["uav_id"] != "UAV-1"
        )
        handoff = data["messages"][1]
        self.assertEqual(handoff["sender_id"], replacement_change["uav_id"])
        self.assertEqual(handoff["related_uav_id"], "UAV-1")
        self.assertEqual(
            handoff["metadata"]["assignment_change"],
            replacement_change,
        )
        self.assertEqual(
            handoff["metadata"]["assignment_change"]["after"]["role"],
            "relay",
        )
        self.assertEqual(
            handoff["metadata"]["assignment_change"]["after"]["waypoint"],
            replacement_change["after"]["waypoint"],
        )
        self.assertIn("UAV-1", handoff["recipient_ids"])
        self.assertTrue(data["algorithm_checks"])

    def test_communication_event_creates_status_relay_acknowledgement_and_summary(self):
        mission_state = build_mission_state()
        environment = build_environment()
        coordinator = SwarmCoordinator(environment)
        plan_mission(coordinator, mission_state)
        affected = next(agent for agent in mission_state.agents if agent.uav_id == "UAV-3")
        affected.position = GridPosition(18, 18)
        affected.communication_quality = 0.2
        event = SwarmEvent(
            event_id="evt-dialogue-communication",
            event_type="communication_degraded",
            message="UAV-3 communication quality dropped below threshold.",
            timestamp="2026-07-10T10:10:00Z",
            uav_id="UAV-3",
            severity="warning",
            metadata={"communication_quality": 0.2},
        )

        data = SwarmDialogueEngine(coordinator).coordinate_event(
            event,
            mission_state,
        ).to_dict()

        self.assertEqual(
            [message["message_type"] for message in data["messages"]],
            ["communication_status", "relay_acknowledgement", "coordination_summary"],
        )
        relay_change = data["coordination_result"]["assignment_changes"][0]
        acknowledgement = data["messages"][1]
        self.assertEqual(acknowledgement["sender_id"], relay_change["uav_id"])
        self.assertEqual(acknowledgement["related_uav_id"], "UAV-3")
        self.assertEqual(
            acknowledgement["metadata"]["assignment_change"],
            relay_change,
        )
        self.assertEqual(relay_change["after"]["role"], "relay")
        waypoint = relay_change["after"]["waypoint"]
        self.assertGreaterEqual(
            environment.communication_quality_at(
                GridPosition(waypoint["x"], waypoint["y"])
            ),
            environment.degraded_communication_threshold,
        )
        self.assertTrue(acknowledgement["metadata"]["algorithm_checks"])

    def test_rejects_unsupported_or_anonymous_events_before_state_changes(self):
        mission_state = build_mission_state()
        coordinator = SwarmCoordinator(build_environment())
        plan_mission(coordinator, mission_state)
        state_before = mission_state.to_dict()
        engine = SwarmDialogueEngine(coordinator)

        with self.assertRaisesRegex(ValueError, "unsupported dialogue event type"):
            engine.coordinate_event(
                SwarmEvent(
                    event_id="evt-unsupported",
                    event_type="wind_warning",
                    message="Wind increased.",
                    timestamp="2026-07-10T10:12:00Z",
                    uav_id="UAV-1",
                ),
                mission_state,
            )
        with self.assertRaisesRegex(ValueError, "requires uav_id"):
            engine.coordinate_event(
                SwarmEvent(
                    event_id="evt-anonymous",
                    event_type="communication_degraded",
                    message="Unknown link degraded.",
                    timestamp="2026-07-10T10:13:00Z",
                ),
                mission_state,
            )

        self.assertEqual(mission_state.to_dict(), state_before)

    def test_duplicate_processed_event_does_not_duplicate_messages_or_memory(self):
        mission_state = build_mission_state()
        coordinator = SwarmCoordinator(build_environment())
        plan_mission(coordinator, mission_state)
        engine = SwarmDialogueEngine(coordinator)
        event = SwarmEvent(
            event_id="evt-dialogue-duplicate",
            event_type="battery_warning",
            message="UAV-1 battery below reserve threshold.",
            timestamp="2026-07-10T10:14:00Z",
            uav_id="UAV-1",
            severity="warning",
            metadata={"battery_level": 20.0},
        )
        engine.coordinate_event(event, mission_state)
        state_after_first = mission_state.to_dict()

        duplicate = engine.coordinate_event(event, mission_state).to_dict()

        self.assertEqual(duplicate["messages"], [])
        self.assertEqual(duplicate["memory_updates"], [])
        self.assertIn("already processed", duplicate["coordinator_summary"])
        self.assertEqual(mission_state.to_dict(), state_after_first)


class SwarmDialogueDemoTests(unittest.TestCase):
    def test_fixed_demo_builds_three_event_multi_agent_timeline(self):
        demo_path = Path(__file__).resolve().parents[1] / "examples" / "swarm_dialogue_demo.py"
        spec = spec_from_file_location("swarm_dialogue_demo", demo_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)

        demo = module.run_demo()["demo_dialogue"]

        self.assertEqual(len(demo["event_results"]), 3)
        self.assertEqual(len(demo["timeline"]), 9)
        message_types = [message["message_type"] for message in demo["timeline"]]
        self.assertIn("target_report", message_types)
        self.assertIn("battery_status", message_types)
        self.assertIn("task_handoff", message_types)
        self.assertIn("communication_status", message_types)
        self.assertIn("relay_acknowledgement", message_types)
        self.assertEqual(message_types.count("coordination_summary"), 3)
        target_report = next(
            message for message in demo["timeline"] if message["message_type"] == "target_report"
        )
        battery_status = next(
            message for message in demo["timeline"] if message["message_type"] == "battery_status"
        )
        relay_ack = next(
            message
            for message in demo["timeline"]
            if message["message_type"] == "relay_acknowledgement"
        )
        self.assertEqual(target_report["sender_id"], "UAV-1")
        self.assertEqual(battery_status["sender_id"], "UAV-2")
        self.assertEqual(relay_ack["sender_id"], "UAV-3")
        self.assertEqual(len(demo["memory_updates"]), len(demo["timeline"]))
        self.assertEqual(
            [message["memory_event_id"] for message in demo["timeline"]],
            [event["event_id"] for event in demo["memory_updates"]],
        )
        self.assertTrue(
            all(result["algorithm_checks"] for result in demo["event_results"])
        )
        self.assertEqual(
            len(
                [
                    event
                    for event in demo["swarm_state"]["memory"]["events"]
                    if event["event_type"] == "agent_message"
                ]
            ),
            9,
        )


if __name__ == "__main__":
    unittest.main()
