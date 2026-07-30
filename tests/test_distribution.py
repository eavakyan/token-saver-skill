import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class DistributionTests(unittest.TestCase):
    def test_clean_wheel_cli_and_symlinked_skill_work_together(self):
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            source = temporary / "source"
            shutil.copytree(
                ROOT,
                source,
                ignore=shutil.ignore_patterns(".git", "build", "dist", "*.egg-info", "__pycache__", ".pytest_cache", ".token-saver"),
            )
            stale_package = source / "build/lib/token_saver"
            stale_package.mkdir(parents=True)
            (stale_package / "__init__.py").write_text('__version__ = "0.0.0"\n', encoding="utf-8")
            (stale_package / "config.py").write_text("raise RuntimeError('stale build tree used')\n", encoding="utf-8")
            wheelhouse = temporary / "wheelhouse"
            wheelhouse.mkdir()
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "wheel",
                    "--no-deps",
                    "--no-cache-dir",
                    "--no-build-isolation",
                    "--wheel-dir",
                    str(wheelhouse),
                    str(source),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            wheels = list(wheelhouse.glob("agent_token_saver-*.whl"))
            self.assertEqual(len(wheels), 1)

            environment = temporary / "venv"
            venv.EnvBuilder(with_pip=True).create(environment)
            bin_dir = environment / ("Scripts" if os.name == "nt" else "bin")
            python = bin_dir / ("python.exe" if os.name == "nt" else "python")
            command = bin_dir / ("token-saver.exe" if os.name == "nt" else "token-saver")
            subprocess.run(
                [str(python), "-m", "pip", "install", "--no-deps", str(wheels[0])],
                check=True,
                capture_output=True,
                text=True,
            )
            doctor = subprocess.run([str(command), "doctor"], check=True, capture_output=True, text=True)
            payload = json.loads(doctor.stdout)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["version"], "1.1.0")
            self.assertEqual(payload["config"], "packaged-default")

            fake_home = temporary / "home"
            fake_home.mkdir()
            child_env = os.environ.copy()
            child_env["HOME"] = str(fake_home)
            child_env["PATH"] = os.pathsep.join((str(bin_dir), child_env.get("PATH", "")))
            subprocess.run(
                [str(python), str(source / "scripts/install.py"), "--platform", "codex", "--scope", "global"],
                check=True,
                capture_output=True,
                text=True,
                env=child_env,
            )
            target = fake_home / ".agents/skills/token-saver"
            self.assertTrue(target.is_symlink())
            self.assertEqual(target.resolve(), (source / "skill").resolve())
            self.assertTrue((target / "SKILL.md").is_file())
            routed = subprocess.run(
                [str(command), "route", "--request", "Implement and test a routine parser change"],
                check=True,
                capture_output=True,
                text=True,
                env=child_env,
            )
            self.assertEqual(json.loads(routed.stdout)["model"], "gpt-5.6-terra")
