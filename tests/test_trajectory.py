import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.trajectory import load_trajectory_points, summarize_trajectory


class TrajectoryTests(unittest.TestCase):
    def test_summarize_trajectory_reports_trends_and_heading_change(self):
        points = load_trajectory_points(
            [
                {
                    "timestamp": 0,
                    "latitude": 30.0,
                    "longitude": 120.0,
                    "altitude": 100,
                    "speed": 10,
                    "heading": 0,
                    "roll": 0,
                    "pitch": 1,
                    "yaw": 0,
                },
                {
                    "timestamp": 10,
                    "latitude": 30.001,
                    "longitude": 120.001,
                    "altitude": 120,
                    "speed": 12,
                    "heading": 90,
                    "roll": 5,
                    "pitch": 2,
                    "yaw": 90,
                },
                {
                    "timestamp": 20,
                    "latitude": 30.002,
                    "longitude": 120.002,
                    "altitude": 140,
                    "speed": 14,
                    "heading": 180,
                    "roll": -5,
                    "pitch": 1,
                    "yaw": 180,
                },
            ]
        )

        summary = summarize_trajectory(points)

        self.assertEqual(summary.point_count, 3)
        self.assertEqual(summary.duration_seconds, 20)
        self.assertEqual(summary.altitude_trend, "climbing")
        self.assertEqual(summary.speed_trend, "accelerating")
        self.assertEqual(summary.heading_change_degrees, 180)
        self.assertAlmostEqual(summary.mean_altitude, 120.0)
        self.assertAlmostEqual(summary.mean_speed, 12.0)
        self.assertGreater(summary.displacement_meters, 250)

    def test_load_trajectory_points_rejects_missing_required_field(self):
        with self.assertRaisesRegex(ValueError, "missing required field: heading"):
            load_trajectory_points(
                [
                    {
                        "timestamp": 0,
                        "latitude": 30.0,
                        "longitude": 120.0,
                        "altitude": 100,
                        "speed": 10,
                        "roll": 0,
                        "pitch": 1,
                        "yaw": 0,
                    }
                ]
            )


if __name__ == "__main__":
    unittest.main()
