"""scripts/sync-plugin-version.py 的脚本层单测（unittest，标准库零依赖）。

运行：python -m unittest tests/sync-plugin-version/test_sync_plugin_version.py
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

REPO = pathlib.Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "sync-plugin-version.py"

CLAUDE_BEFORE = '{\n  "name": "x",\n  "version": "0.0.0",\n  "skills": []\n}\n'
CLAUDE_AFTER = '{\n  "name": "x",\n  "version": "1.2.3",\n  "skills": []\n}\n'
CODEX_BEFORE = '{\n  "name": "x",\n  "version": "0.0.0",\n  "skills": "./skills/"\n}\n'

# lock 里 "version" 出现上百次：根一处、packages[""] 一处要跟着升，别的包各是自己的
# 版本，一个字都不许动。这份样本把依赖的版本也写成 0.0.0，正是为了逼出误伤。
LOCK_BEFORE = """{
  "name": "x",
  "version": "0.0.0",
  "lockfileVersion": 3,
  "requires": true,
  "packages": {
    "": {
      "name": "x",
      "version": "0.0.0",
      "license": "MIT",
      "devDependencies": {
        "dep": "^1.0.0"
      }
    },
    "node_modules/dep": {
      "version": "0.0.0",
      "resolved": "https://example.invalid/dep/-/dep-0.0.0.tgz"
    }
  }
}
"""


def write(root, rel, text):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def run(root, *flags):
    return subprocess.run([sys.executable, str(SCRIPT), "--root", str(root), *flags],
                          capture_output=True, text=True, encoding="utf-8")


class SyncPluginVersionTest(unittest.TestCase):
    def setUp(self):
        self.root = pathlib.Path(tempfile.mkdtemp(prefix="sync-ver-"))
        write(self.root, "package.json", json.dumps({"name": "x", "version": "1.2.3"}))
        self.claude = write(self.root, ".claude-plugin/plugin.json", CLAUDE_BEFORE)
        self.codex = write(self.root, ".codex-plugin/plugin.json", CODEX_BEFORE)
        self.lock = write(self.root, "package-lock.json", LOCK_BEFORE)

    def test_sync_writes_version_into_both_manifests(self):
        r = run(self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        for p in (self.claude, self.codex):
            self.assertEqual(json.loads(p.read_text(encoding="utf-8"))["version"], "1.2.3")

    def test_sync_keeps_formatting_and_key_order(self):
        run(self.root)
        self.assertEqual(self.claude.read_text(encoding="utf-8"), CLAUDE_AFTER)

    def test_check_fails_when_out_of_sync_and_changes_nothing(self):
        r = run(self.root, "--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn(".codex-plugin/plugin.json", r.stderr)
        self.assertEqual(self.codex.read_text(encoding="utf-8"), CODEX_BEFORE)

    def test_check_passes_when_in_sync(self):
        run(self.root)
        r = run(self.root, "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_sync_writes_version_into_lock_both_places(self):
        r = run(self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        lock = json.loads(self.lock.read_text(encoding="utf-8"))
        self.assertEqual(lock["version"], "1.2.3")
        self.assertEqual(lock["packages"][""]["version"], "1.2.3")

    def test_sync_leaves_other_packages_alone(self):
        run(self.root)
        lock = json.loads(self.lock.read_text(encoding="utf-8"))
        self.assertEqual(lock["packages"]["node_modules/dep"]["version"], "0.0.0")
        self.assertEqual(lock["packages"][""]["license"], "MIT")
        self.assertEqual(lock["lockfileVersion"], 3)

    def test_check_fails_when_only_lock_is_out_of_sync(self):
        run(self.root)
        self.lock.write_text(LOCK_BEFORE, encoding="utf-8")
        r = run(self.root, "--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("package-lock.json", r.stderr)
        self.assertEqual(self.lock.read_text(encoding="utf-8"), LOCK_BEFORE)

    def test_missing_lock_is_skipped_not_an_error(self):
        self.lock.unlink()
        r = run(self.root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        r = run(self.root, "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_repo_manifests_are_in_sync(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "--check"],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
