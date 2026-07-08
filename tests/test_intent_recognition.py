import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.intent_recognition import recognize_intent
from uav_mission_agent.trajectory import load_trajectory_points


class IntentRecognitionTests(unittest.TestCase):
    def test_recognizes_loitering_from_high_heading_change_and_low_displacement(self):
        points = load_trajectory_points(
            [
                {"timestamp": 0, "latitude": 30.0, "longitude": 120.0, "altitude": 100, "speed": 4, "heading": 0, "roll": 10, "pitch": 0, "yaw": 0},
                {"timestamp": 10, "latitude": 30.0001, "longitude": 120.0001, "altitude": 101, "speed": 4, "heading": 160, "roll": -10, "pitch": 0, "yaw": 160},
                {"timestamp": 20, "latitude": 30.0002, "longitude": 120.0001, "altitude": 101, "speed": 4, "heading": 320, "roll": 12, "pitch": 0, "yaw": 320},
            ]
        )

        result = recognize_intent(points)

        self.assertEqual(result.intent, "loitering")
        self.assertGreater(result.confidence, 0.5)
        self.assertIn("high heading change", result.evidence[0])

    def test_recognizes_return_to_base_from_descending_decelerating_track(self):
        points = load_trajectory_points(
            [
                {"timestamp": 0, "latitude": 30.0, "longitude": 120.0, "altitude": 160, "speed": 16, "heading": 20, "roll": 0, "pitch": -1, "yaw": 20},
                {"timestamp": 20, "latitude": 29.998, "longitude": 119.998, "altitude": 120, "speed": 11, "heading": 25, "roll": 0, "pitch": -2, "yaw": 25},
                {"timestamp": 40, "latitude": 29.996, "longitude": 119.996, "altitude": 80, "speed": 7, "heading": 30, "roll": 0, "pitch": -3, "yaw": 30},
            ]
        )

        result = recognize_intent(points)

        self.assertEqual(result.intent, "return_to_base")
        self.assertGreaterEqual(result.confidence, 0.7)

    def test_recognizes_area_search_from_multi_turn_coverage_track(self):
        points = load_trajectory_points(
            [
                {"timestamp": 0, "latitude": 30.0, "longitude": 120.0, "altitude": 100, "speed": 10, "heading": 0, "roll": 0, "pitch": 0, "yaw": 0},
                {"timestamp": 10, "latitude": 30.001, "longitude": 120.0, "altitude": 101, "speed": 10, "heading": 80, "roll": 6, "pitch": 0, "yaw": 80},
                {"timestamp": 20, "latitude": 30.001, "longitude": 120.002, "altitude": 100, "speed": 10, "heading": 170, "roll": -6, "pitch": 0, "yaw": 170},
                {"timestamp": 30, "latitude": 30.002, "longitude": 120.002, "altitude": 101, "speed": 11, "heading": 260, "roll": 6, "pitch": 0, "yaw": 260},
                {"timestamp": 40, "latitude": 30.002, "longitude": 120.004, "altitude": 100, "speed": 10, "heading": 350, "roll": -6, "pitch": 0, "yaw": 350},
            ]
        )

        result = recognize_intent(points)

        self.assertEqual(result.intent, "area_search")
        self.assertIn("multi-turn", " ".join(result.evidence))

    def test_recognizes_target_tracking_from_stable_speed_and_moderate_turning(self):
        points = load_trajectory_points(
            [
                {"timestamp": 0, "latitude": 30.0, "longitude": 120.0, "altitude": 120, "speed": 9, "heading": 0, "roll": 2, "pitch": 0, "yaw": 0},
                {"timestamp": 10, "latitude": 30.0005, "longitude": 120.0003, "altitude": 120, "speed": 9, "heading": 50, "roll": 3, "pitch": 0, "yaw": 50},
                {"timestamp": 20, "latitude": 30.001, "longitude": 120.0007, "altitude": 120, "speed": 9, "heading": 100, "roll": 2, "pitch": 0, "yaw": 100},
            ]
        )

        result = recognize_intent(points)

        self.assertEqual(result.intent, "target_tracking")
        self.assertIn("steady speed", " ".join(result.evidence))

    def test_recognizes_transit_as_low_maneuvering_fallback(self):
        points = load_trajectory_points(
            [
                {"timestamp": 0, "latitude": 30.0, "longitude": 120.0, "altitude": 120, "speed": 12, "heading": 5, "roll": 0, "pitch": 0, "yaw": 5},
                {"timestamp": 20, "latitude": 30.01, "longitude": 120.01, "altitude": 120, "speed": 12, "heading": 10, "roll": 0, "pitch": 0, "yaw": 10},
            ]
        )

        result = recognize_intent(points)

        self.assertEqual(result.intent, "transit")
        self.assertIn("point-to-point", " ".join(result.evidence))


if __name__ == "__main__":
    unittest.main()
