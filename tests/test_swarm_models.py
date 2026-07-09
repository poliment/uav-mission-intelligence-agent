import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.swarm_models import (
    DetectedTarget,
    GridPosition,
    SwarmEvent,
    SwarmMemory,
    SwarmMissionState,
    UAVAgentState,
)


class SwarmModelTests(unittest.TestCase):
    def test_uav_agent_state_serializes_independent_agent_fields(self):
        agent = UAVAgentState(
            uav_id="UAV-1",
            role="scout",
            position=GridPosition(3, 4),
            battery_level=87.5,
            assigned_area="mountain-a-north",
            current_objective="Search north ridge",
            status="active",
            communication_quality=0.92,
            memory_refs=["evt-001"],
        )

        self.assertEqual(
            agent.to_dict(),
            {
                "uav_id": "UAV-1",
                "role": "scout",
                "position": {"x": 3, "y": 4},
                "battery_level": 87.5,
                "assigned_area": "mountain-a-north",
                "current_objective": "Search north ridge",
                "status": "active",
                "communication_quality": 0.92,
                "memory_refs": ["evt-001"],
            },
        )

    def test_swarm_memory_records_and_retrieves_events(self):
        memory = SwarmMemory()
        mission_event = SwarmEvent(
            event_id="evt-001",
            event_type="mission_started",
            message="Mountain area search started.",
            timestamp="2026-07-09T09:00:00Z",
            severity="info",
            metadata={"area": "mountain-a"},
        )
        comms_event = SwarmEvent(
            event_id="evt-002",
            event_type="communication_degraded",
            message="Relay link is weak near east ridge.",
            timestamp="2026-07-09T09:05:00Z",
            uav_id="UAV-3",
            area_id="mountain-a-east",
            severity="warning",
            metadata={"risk": "weak communication"},
        )

        self.assertIs(memory.add_event(mission_event), mission_event)
        memory.add_event(comms_event)

        self.assertEqual(memory.events_for_uav("UAV-3"), [comms_event])
        self.assertEqual(memory.events_by_type("communication_degraded"), [comms_event])
        self.assertEqual(memory.events_for_area("mountain-a-east"), [comms_event])
        self.assertEqual(memory.search_events("weak communication"), [comms_event])
        self.assertEqual(
            memory.to_dict()["events"][1],
            {
                "event_id": "evt-002",
                "event_type": "communication_degraded",
                "message": "Relay link is weak near east ridge.",
                "timestamp": "2026-07-09T09:05:00Z",
                "uav_id": "UAV-3",
                "target_id": None,
                "area_id": "mountain-a-east",
                "severity": "warning",
                "metadata": {"risk": "weak communication"},
            },
        )

    def test_swarm_memory_records_detected_targets(self):
        memory = SwarmMemory()
        target = DetectedTarget(
            target_id="target-heat-001",
            target_type="thermal_source",
            position=GridPosition(12, 8),
            confidence=0.84,
            detected_by="UAV-1",
            timestamp="2026-07-09T09:12:00Z",
            status="queued_for_tracking",
            metadata={"sensor": "thermal"},
        )

        self.assertIs(memory.add_target(target), target)

        self.assertEqual(memory.targets_by_type("thermal_source"), [target])
        self.assertEqual(
            memory.to_dict()["targets"],
            [
                {
                    "target_id": "target-heat-001",
                    "target_type": "thermal_source",
                    "position": {"x": 12, "y": 8},
                    "confidence": 0.84,
                    "detected_by": "UAV-1",
                    "timestamp": "2026-07-09T09:12:00Z",
                    "status": "queued_for_tracking",
                    "metadata": {"sensor": "thermal"},
                }
            ],
        )

    def test_serialized_metadata_does_not_expose_internal_lists(self):
        event = SwarmEvent(
            event_id="evt-001",
            event_type="battery_warning",
            message="Battery reserve check failed.",
            timestamp="2026-07-09T09:15:00Z",
            metadata={"checks": ["battery"]},
        )
        target = DetectedTarget(
            target_id="target-001",
            target_type="thermal_source",
            position=GridPosition(4, 5),
            confidence=0.8,
            detected_by="UAV-1",
            timestamp="2026-07-09T09:16:00Z",
            metadata={"sensors": ["thermal"]},
        )

        event_data = event.to_dict()
        target_data = target.to_dict()

        event_data["metadata"]["checks"].append("communication")
        target_data["metadata"]["sensors"].append("visual")

        self.assertEqual(event.metadata["checks"], ["battery"])
        self.assertEqual(target.metadata["sensors"], ["thermal"])

    def test_swarm_memory_records_failure_experience_as_event(self):
        memory = SwarmMemory()

        event = memory.record_failure(
            event_id="evt-fail-001",
            message="UAV-2 could not continue remote area assignment.",
            timestamp="2026-07-09T09:18:00Z",
            uav_id="UAV-2",
            area_id="mountain-a-remote",
            reason="battery below reserve threshold",
            impact="remote area coverage delayed",
            recommended_action="assign reserve UAV",
        )

        self.assertEqual(event.event_type, "failure_experience")
        self.assertEqual(event.severity, "warning")
        self.assertEqual(memory.events_by_type("failure_experience"), [event])
        self.assertEqual(memory.search_events("battery below reserve"), [event])
        self.assertEqual(
            event.metadata,
            {
                "reason": "battery below reserve threshold",
                "impact": "remote area coverage delayed",
                "recommended_action": "assign reserve UAV",
            },
        )

    def test_swarm_mission_state_serializes_agents_and_memory(self):
        memory = SwarmMemory()
        memory.add_event(
            SwarmEvent(
                event_id="evt-001",
                event_type="area_assigned",
                message="UAV-1 assigned to north ridge.",
                timestamp="2026-07-09T09:01:00Z",
                uav_id="UAV-1",
                area_id="mountain-a-north",
            )
        )
        state = SwarmMissionState(
            mission_id="mission-mountain-a",
            agents=[
                UAVAgentState(
                    uav_id="UAV-1",
                    role="scout",
                    position=GridPosition(2, 3),
                    battery_level=90.0,
                    assigned_area="mountain-a-north",
                    current_objective="Search north ridge",
                    status="active",
                ),
                UAVAgentState(
                    uav_id="UAV-2",
                    role="relay",
                    position=GridPosition(0, 4),
                    battery_level=95.0,
                    current_objective="Maintain communication relay",
                    status="holding",
                ),
            ],
            memory=memory,
            base_position=GridPosition(0, 0),
            phase="execution",
            grid_size={"width": 20, "height": 20},
        )

        data = state.to_dict()

        self.assertEqual(data["mission_id"], "mission-mountain-a")
        self.assertEqual(data["phase"], "execution")
        self.assertEqual(data["base_position"], {"x": 0, "y": 0})
        self.assertEqual(data["grid_size"], {"width": 20, "height": 20})
        self.assertEqual([agent["uav_id"] for agent in data["agents"]], ["UAV-1", "UAV-2"])
        self.assertEqual(data["memory"]["events"][0]["event_type"], "area_assigned")

    def test_validates_numeric_ranges(self):
        with self.assertRaises(ValueError):
            UAVAgentState(
                uav_id="UAV-1",
                role="scout",
                position=GridPosition(0, 0),
                battery_level=101.0,
            )

        with self.assertRaises(ValueError):
            UAVAgentState(
                uav_id="UAV-1",
                role="scout",
                position=GridPosition(0, 0),
                battery_level=50.0,
                communication_quality=-0.1,
            )

        with self.assertRaises(ValueError):
            DetectedTarget(
                target_id="target-001",
                target_type="thermal_source",
                position=GridPosition(1, 1),
                confidence=1.2,
                detected_by="UAV-1",
                timestamp="2026-07-09T09:10:00Z",
            )


if __name__ == "__main__":
    unittest.main()
