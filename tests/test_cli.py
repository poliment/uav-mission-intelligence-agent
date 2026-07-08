import contextlib
import io
import json
import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


from uav_mission_agent.cli import main


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "scenarios"


class CliTests(unittest.TestCase):
    def test_benchmark_mode_prints_json_report(self):
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            main(["--benchmark", str(FIXTURE_DIR)])

        report = json.loads(output.getvalue())
        self.assertEqual(report["summary"]["total_scenarios"], 1)
        self.assertGreaterEqual(report["summary"]["average_score"], 0.85)


if __name__ == "__main__":
    unittest.main()

