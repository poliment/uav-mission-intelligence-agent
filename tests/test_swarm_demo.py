import json
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.swarm_demo import (
    DEFAULT_SWARM_DEMO_MISSION,
    DEMO_EVENT_ORDER,
    create_swarm_demo_session,
)


class RecordingProvider:
    provider_name = "recording-provider"
    model = "recording-model"

    def __init__(self) -> None:
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
            "recommendations": ["Keep the deterministic role allocation."],
            "risks": ["Confirm the thermal target before approach."],
            "mission_config": {},
        }


class MutatingFailingDialogue:
    def coordinate_event(self, event, mission_state):
        mission_state.phase = "broken"
        mission_state.agents[0].position.x = 19
        mission_state.memory.add_event(event)
        raise RuntimeError("simulated coordination failure")


class SwarmDemoSessionTests(unittest.TestCase):
    def test_initial_session_has_four_roles_and_serializable_state(self):
        session = create_swarm_demo_session()

        self.assertEqual(
            DEMO_EVENT_ORDER,
            ("target_detected", "battery_warning", "communication_degraded"),
        )
        self.assertIn("4", DEFAULT_SWARM_DEMO_MISSION)
        self.assertEqual(session.mission_text, DEFAULT_SWARM_DEMO_MISSION)
        self.assertEqual(session.environment.width, 20)
        self.assertEqual(session.environment.height, 20)
        self.assertEqual(session.next_event_type, "target_detected")
        self.assertEqual(
            {assignment.role for assignment in session.initial_plan.role_assignments},
            {"scout", "tracker", "relay", "reserve"},
        )
        self.assertEqual(
            set(session.current_assignments),
            {"UAV-1", "UAV-2", "UAV-3", "UAV-4"},
        )
        self.assertEqual(
            session.initial_plan.memory_updates[0].timestamp,
            "2026-07-10T10:00:00Z",
        )

        data = session.to_dict()
        self.assertEqual(data["mission_id"], session.mission_state.mission_id)
        self.assertEqual(data["mission_text"], DEFAULT_SWARM_DEMO_MISSION)
        self.assertEqual(data["event_order"], list(DEMO_EVENT_ORDER))
        self.assertEqual(data["processed_event_count"], 0)
        self.assertEqual(data["next_event_type"], "target_detected")
        self.assertEqual(len(data["initial_plan"]["role_assignments"]), 4)
        self.assertEqual(set(data["current_assignments"]), set(session.current_assignments))
        self.assertIsInstance(json.dumps(data, ensure_ascii=False), str)

    def test_processes_only_the_fixed_event_sequence_and_updates_live_state(self):
        session = create_swarm_demo_session()

        target_result = session.process_next_event()
        self.assertEqual(target_result.trigger_event.event_type, "target_detected")
        self.assertEqual(target_result.trigger_event.uav_id, "UAV-1")
        self.assertEqual(
            target_result.trigger_event.metadata["position"],
            {"x": 12, "y": 8},
        )
        self.assertEqual(session.next_event_type, "battery_warning")
        self.assertEqual(session.mission_state.memory.targets[0].position.to_dict(), {"x": 12, "y": 8})

        battery_result = session.process_next_event()
        self.assertEqual(battery_result.trigger_event.event_type, "battery_warning")
        uav_2 = next(agent for agent in session.mission_state.agents if agent.uav_id == "UAV-2")
        self.assertEqual(uav_2.battery_level, 20.0)
        self.assertEqual(session.next_event_type, "communication_degraded")

        communication_result = session.process_next_event()
        self.assertEqual(
            communication_result.trigger_event.event_type,
            "communication_degraded",
        )
        uav_1 = next(agent for agent in session.mission_state.agents if agent.uav_id == "UAV-1")
        self.assertEqual(uav_1.position.to_dict(), {"x": 18, "y": 18})
        self.assertEqual(uav_1.communication_quality, 0.2)
        self.assertIsNone(session.next_event_type)

        for uav_id, assignment in session.current_assignments.items():
            agent = next(agent for agent in session.mission_state.agents if agent.uav_id == uav_id)
            self.assertEqual(assignment.role, agent.role)
            self.assertTrue(assignment.path.path)

    def test_running_all_events_creates_three_replans_and_nine_linked_messages(self):
        session = create_swarm_demo_session()

        results = session.run_remaining_events()

        self.assertEqual(len(results), 3)
        self.assertEqual(
            [result.trigger_event.event_type for result in results],
            list(DEMO_EVENT_ORDER),
        )
        self.assertTrue(all(result.coordination_result.assignment_changes for result in results))
        replans = session.mission_state.memory.events_by_type("replanning")
        messages = [message for result in results for message in result.messages]
        message_memory = session.mission_state.memory.events_by_type("agent_message")
        self.assertEqual(len(replans), 3)
        self.assertEqual(len(messages), 9)
        self.assertEqual(len(message_memory), 9)
        self.assertEqual(
            [message.memory_event_id for message in messages],
            [event.event_id for event in message_memory],
        )
        self.assertTrue(all(message.memory_event_id for message in messages))

    def test_completion_is_idempotent_and_does_not_duplicate_memory(self):
        session = create_swarm_demo_session()
        session.run_remaining_events()
        state_after_completion = session.to_dict()

        self.assertEqual(session.run_remaining_events(), [])
        with self.assertRaisesRegex(RuntimeError, "processed"):
            session.process_next_event()

        self.assertEqual(session.to_dict(), state_after_completion)
        self.assertEqual(len(session.event_results), 3)

    def test_failed_event_processing_does_not_partially_mutate_session(self):
        session = create_swarm_demo_session()
        state_before = session.to_dict()
        session.dialogue_engine = MutatingFailingDialogue()

        with self.assertRaisesRegex(RuntimeError, "coordination failure"):
            session.process_next_event()

        self.assertEqual(session.to_dict(), state_before)
        self.assertEqual(session.next_event_type, "target_detected")

    def test_provider_is_used_only_for_initial_planning(self):
        provider = RecordingProvider()

        session = create_swarm_demo_session(llm_provider=provider)

        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(session.initial_plan.decision_source, "provider_enhanced")
        results = session.run_remaining_events()
        self.assertEqual(len(provider.calls), 1)
        self.assertTrue(
            all(
                result.coordination_result.decision_source == "offline_rules"
                for result in results
            )
        )

    def test_factory_rejects_blank_mission_without_partial_session(self):
        with self.assertRaisesRegex(ValueError, "mission_text"):
            create_swarm_demo_session("   ")


if __name__ == "__main__":
    unittest.main()
