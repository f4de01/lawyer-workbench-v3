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

    def test_repo_manifests_are_in_sync(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "--check"],
                           capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
