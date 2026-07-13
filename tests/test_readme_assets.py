import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
README = REPO_ROOT / "README.md"
STREAMLIT_ASSET = REPO_ROOT / "docs" / "assets" / "streamlit-swarm-console.jpg"


class ReadmeAssetsTests(unittest.TestCase):
    def test_readme_documents_the_current_console_interface(self):
        readme = README.read_text(encoding="utf-8")
        lines = readme.splitlines()
        required = (
            "UAV Swarm Mission Console",
            'python -m pip install -e ".[demo]"',
            "Swarm Plan",
            "Event Response",
            "Agent Dialogue",
            "Mission Intelligence",
            "Evaluation",
            "/api/swarm/demo-plan",
            "/api/swarm/demo-events",
            "/api/swarm/demo-dialogue",
        )

        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, readme)

        exact_commands = (
            "uav-mission-agent-demo --host 127.0.0.1 --port 8000",
            "uav-mission-agent-api --host 127.0.0.1 --port 8010",
            "uav-mission-agent-demo --env-file .env --no-browser",
        )
        for command in exact_commands:
            with self.subTest(command=command):
                self.assertIn(command, lines)

    def test_readme_preserves_supported_cli_and_retrieval_features(self):
        readme = README.read_text(encoding="utf-8")
        lines = readme.splitlines()
        required = (
            "--trace",
            "local-vector",
            "rag-faiss",
            "rag-chroma",
            "DEEPSEEK_API_KEY",
            "OPENAI_API_KEY",
        )

        for text in required:
            with self.subTest(text=text):
                self.assertIn(text, readme)

        exact_commands = (
            "uav-mission-agent --benchmark data\\scenarios",
            "uav-mission-agent --benchmark-v2 data\\scenarios",
            "uav-mission-agent --dashboard dashboard\\uav_mission_dashboard.html",
            "uav-mission-agent --trajectory-intent examples\\trajectory_intent_example.json",
        )
        for command in exact_commands:
            with self.subTest(command=command):
                self.assertIn(command, lines)

    def test_readme_distinguishes_retrieval_from_workflow_backends(self):
        readme = README.read_text(encoding="utf-8")

        self.assertNotIn("FAISS、Chroma 和 LangGraph", readme)
        self.assertRegex(readme, r"离线 RAG[^\n]*FAISS[^\n]*Chroma")
        self.assertRegex(readme, r"LangGraph[^\n]*工作流")

    def test_readme_rejects_abandoned_history_and_secret_examples(self):
        readme = README.read_text(encoding="utf-8")
        stale_patterns = (
            r"\bstage\s*[45]\b",
            r"阶段\s*[45]",
            r"swarm\s+upgrade\s+status",
            r"fastapi\s*\+\s*html",
            r"^##\s+roadmap\b",
            r"\byour-api-key\b",
            r"(?:export\s+|\$env:)?(?:deepseek|openai)_api_key\s*=",
            r"\.env\.local\b",
            r"\b[A-Z]:\\",
            r"/(?:home|Users)/[^/\s]+/",
        )

        for pattern in stale_patterns:
            with self.subTest(pattern=pattern):
                self.assertIsNone(
                    re.search(pattern, readme, flags=re.IGNORECASE | re.MULTILINE)
                )

    def test_readme_uses_only_the_current_console_hero(self):
        readme = README.read_text(encoding="utf-8")
        images = re.findall(r"!\[[^]]*]\(([^)]+)\)", readme)
        local_assets = [image for image in images if image.startswith("docs/assets/")]

        self.assertEqual(local_assets, ["docs/assets/streamlit-swarm-console.jpg"])

    def test_readme_local_links_exist(self):
        readme = README.read_text(encoding="utf-8")
        targets = re.findall(r"!?(?:\[[^]]*])\(([^)]+)\)", readme)
        local_targets = [
            target.strip("<>").split("#", 1)[0]
            for target in targets
            if not re.match(r"^(?:https?://|mailto:|#)", target)
        ]

        for target in local_targets:
            with self.subTest(target=target):
                self.assertTrue((REPO_ROOT / target).exists())

    def test_readme_has_compact_console_first_structure(self):
        readme = README.read_text(encoding="utf-8")
        headings = re.findall(r"^## (.+)$", readme, flags=re.MULTILINE)

        self.assertEqual(
            headings,
            [
                "UAV Swarm Mission Console",
                "核心能力",
                "快速开始",
                "控制台视图",
                "确定性演示流程",
                "JSON API",
                "CLI 与扩展能力",
                "可选在线模型",
                "架构",
                "测试",
                "项目结构",
            ],
        )

    def test_streamlit_console_screenshot_exists(self):
        self.assertTrue(STREAMLIT_ASSET.exists())
        self.assertGreater(STREAMLIT_ASSET.stat().st_size, 50_000)
        image_bytes = STREAMLIT_ASSET.read_bytes()
        self.assertTrue(image_bytes.startswith(b"\xff\xd8"))
        self.assertTrue(image_bytes.endswith(b"\xff\xd9"))

    def test_streamlit_console_screenshot_decodes_with_pillow(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow is installed with the demo extra")

        with Image.open(STREAMLIT_ASSET) as image:
            image.verify()


if __name__ == "__main__":
    unittest.main()
