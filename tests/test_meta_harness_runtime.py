import importlib.util
import subprocess
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
METAHARNESS = ROOT / "workspace_seed" / "skills" / "meta-harness" / "metaharness.py"


def load_metaharness_module():
    spec = importlib.util.spec_from_file_location("metaharness_script", METAHARNESS)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MetaHarnessRuntimeTests(unittest.TestCase):
    def test_headless_subprocess_uses_utf8_output_decoding(self):
        module = load_metaharness_module()

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            variant = root / "variants" / "baseline"
            workspace = root / "runs" / "baseline" / "_ws"
            out = root / "runs" / "baseline"
            query = root / "query.txt"
            variant.mkdir(parents=True)
            workspace.mkdir(parents=True)
            out.mkdir(parents=True, exist_ok=True)
            query.write_text("hello", encoding="utf-8")

            completed = subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")
            with patch.object(module.subprocess, "run", return_value=completed) as run:
                return_code, log = module._run_headless_subprocess(
                    ROOT,
                    variant,
                    workspace,
                    out,
                    query,
                    recursion_limit=5,
                    timeout=10,
                )

        self.assertEqual(return_code, 0)
        self.assertEqual(log, "ok")
        self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")
        self.assertEqual(run.call_args.kwargs["errors"], "replace")

    def test_headless_subprocess_env_forces_utf8_python_io(self):
        module = load_metaharness_module()

        with patch.dict(module.os.environ, {"WORKSPACE_DIR": "ignored", "PYTHONIOENCODING": "cp949"}):
            env = module._headless_subprocess_env()

        self.assertNotIn("WORKSPACE_DIR", env)
        self.assertEqual(env["PYTHONUTF8"], "1")
        self.assertEqual(env["PYTHONIOENCODING"], "utf-8")


if __name__ == "__main__":
    unittest.main()
