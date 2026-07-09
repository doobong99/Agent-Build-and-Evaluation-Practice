import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "langchain-deepagents.py"


class WorldcupRuntimeConfigTests(unittest.TestCase):
    def test_runtime_path_helper_exposes_python_and_scripts_dirs(self):
        spec = importlib.util.spec_from_file_location("agent_app_source", SOURCE)
        module = importlib.util.module_from_spec(spec)

        source = SOURCE.read_text(encoding="utf-8")
        helper_source = source[
            source.index("def _runtime_path_entries") : source.index("def _prepare_runtime_environment")
        ]
        exec("from pathlib import Path\n" + helper_source, module.__dict__)

        entries = module._runtime_path_entries(r"C:\Tools\Python\python.exe")

        self.assertEqual(entries, [r"C:\Tools\Python", r"C:\Tools\Python\Scripts"])

    def test_worldcup_prompt_uses_backend_relative_python_command_and_image_markdown(self):
        source = SOURCE.read_text(encoding="utf-8")

        self.assertIn(
            "python skills/worldcup-result-screenshot/collect_worldcup_result.py --date YYYY-MM-DD",
            source,
        )
        self.assertNotIn(
            "python3 workspace/skills/worldcup-result-screenshot/collect_worldcup_result.py",
            source,
        )
        self.assertIn("Markdown image", source)
        self.assertIn("![월드컵 경기 결과]", source)


if __name__ == "__main__":
    unittest.main()
