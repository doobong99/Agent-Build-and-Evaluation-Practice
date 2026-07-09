import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "langchain-deepagents.py"
WORLDCUP_SCRIPT = ROOT / "workspace_seed" / "skills" / "worldcup-result-screenshot" / "collect_worldcup_result.py"


def load_worldcup_module():
    spec = importlib.util.spec_from_file_location("worldcup_result_script", WORLDCUP_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


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
        self.assertIn("SAVED_PATH:", source)
        self.assertIn("IMAGE_MARKDOWN:", source)
        self.assertIn("NO_MATCHES:", source)
        self.assertIn("SCHEDULE_URL:", source)
        self.assertIn("경기가 없는 날짜 입니다. 다른 날짜를 조회해 주세요", source)
        self.assertIn("http://127.0.0.1:8765/screenshots/worldcup-YYYYMMDD.png", source)
        self.assertIn("data:image/png;base64", source)
        self.assertNotIn("![월드컵 경기 결과](screenshots/worldcup-YYYYMMDD.png)", source)

    def test_image_markdown_prefers_local_http_url(self):
        module = load_worldcup_module()

        image_path = Path(r"C:\repo\workspace\screenshots\worldcup-20260707.png")

        markdown = module.build_image_markdown(image_path, base_url="http://127.0.0.1:8765/screenshots")

        self.assertEqual(
            markdown,
            "![worldcup-result](http://127.0.0.1:8765/screenshots/worldcup-20260707.png)",
        )

    def test_image_markdown_falls_back_to_data_uri(self):
        module = load_worldcup_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            image_path = Path(temp_dir) / "result.png"
            image_path.write_bytes(b"png-bytes")

            with patch.dict(os.environ, {}, clear=True):
                markdown = module.build_image_markdown(image_path)

        self.assertEqual(markdown, "![worldcup-result](data:image/png;base64,cG5nLWJ5dGVz)")

    def test_loaded_schedule_date_is_read_from_page_url(self):
        module = load_worldcup_module()

        loaded_date = module.loaded_schedule_date(
            "https://m.sports.naver.com/fifaworldcup2026/schedule?date=2026-07-10"
        )

        self.assertEqual(loaded_date, "2026-07-10")

    def test_redirected_schedule_date_is_reported_as_no_matches(self):
        module = load_worldcup_module()

        with self.assertRaises(module.NoMatchesForDate) as raised:
            module.ensure_requested_date_available(
                "2026-07-09",
                "https://m.sports.naver.com/fifaworldcup2026/schedule?date=2026-07-10",
            )

        self.assertEqual(str(raised.exception), "경기가 없는 날짜 입니다. 다른 날짜를 조회해 주세요")
        self.assertEqual(raised.exception.requested_date, "2026-07-09")
        self.assertEqual(raised.exception.loaded_date, "2026-07-10")

    def test_chromium_candidates_include_env_and_installed_chrome(self):
        module = load_worldcup_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            configured = temp_path / "custom-chrome.exe"
            installed = temp_path / "ms-playwright" / "chromium-1228" / "chrome-win64" / "chrome.exe"
            installed.parent.mkdir(parents=True)
            configured.write_text("", encoding="utf-8")
            installed.write_text("", encoding="utf-8")

            with patch.dict(
                os.environ,
                {
                    "PLAYWRIGHT_CHROMIUM_EXECUTABLE": str(configured),
                    "LOCALAPPDATA": str(temp_path),
                    "USERPROFILE": str(temp_path / "profile"),
                },
            ):
                candidates = module.chromium_executable_candidates()

        self.assertEqual(candidates[:2], [configured, installed])

    def test_launch_chromium_retries_with_full_chrome_executable(self):
        module = load_worldcup_module()

        class FakeChromium:
            def __init__(self):
                self.calls = []

            def launch(self, **kwargs):
                self.calls.append(kwargs)
                if len(self.calls) == 1:
                    raise RuntimeError("headless shell blocked")
                return kwargs

        class FakePlaywright:
            def __init__(self):
                self.chromium = FakeChromium()

        fake_playwright = FakePlaywright()
        chrome_path = Path(r"C:\Users\SKAX\AppData\Local\ms-playwright\chromium-1228\chrome-win64\chrome.exe")

        with patch.object(module, "chromium_executable_candidates", return_value=[chrome_path]):
            result = module.launch_chromium(fake_playwright)

        self.assertEqual(fake_playwright.chromium.calls[0], {"headless": True})
        self.assertEqual(result, {"headless": True, "executable_path": str(chrome_path)})


if __name__ == "__main__":
    unittest.main()
