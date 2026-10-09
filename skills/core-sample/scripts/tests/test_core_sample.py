"""Stdlib tests for core-sample. Run: python3 -m unittest discover -s tests"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from core_sample import taxonomy as T
from core_sample.ledger import link_failures, number_calls, validate
from core_sample.parse_transcript import parse_transcript

ROOT = Path(__file__).resolve().parents[1]


def load_hook():
    spec = importlib.util.spec_from_file_location("hook", ROOT / "hooks" / "ledger_hook.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ErrorScan(unittest.TestCase):
    def test_catches_masked_failures(self):
        self.assertEqual(T.scan_errors("x\nfatal: unable to access 'https://…': The requested URL returned error: 403")[0], "git-fatal")
        self.assertEqual(T.scan_errors("ModuleNotFoundError: No module named 'fitz'")[0], "python-exception")

    def test_ignores_error_words_in_success(self):
        self.assertEqual(T.scan_errors('{"status": "success", "total_errors": 0, "error_summary": {}}')[0], "")


class Redaction(unittest.TestCase):
    def test_secrets_never_survive(self):
        h = load_hook()
        for text, secret in [('Authorization: Bearer abcdefghijklmnopqrstuv', "abcdefghijklmnop"),
                             ("export API_KEY=supersecret123", "supersecret123"),
                             ("ghp_ABCDEFGHIJKLMNOPQRSTUVWX", "ABCDEFGHIJKLMN")]:
            self.assertNotIn(secret, h.redact(text))

    def test_prose_untouched(self):
        self.assertEqual(load_hook().redact("Explain token usage"), "Explain token usage")


class HookHardening(unittest.TestCase):
    """The three defects an eval run found in v0.1 of the hook."""

    def run_hook(self, home, payload):
        import os, subprocess, sys
        env = dict(os.environ, CORE_SAMPLE_HOME=str(home))
        return subprocess.run([sys.executable, str(ROOT / "hooks" / "ledger_hook.py")], input=json.dumps(payload),
                              text=True, env=env, capture_output=True)

    def test_session_id_cannot_escape_home(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "cs"
            self.run_hook(home, {"hook_event_name": "PostToolUse", "session_id": "../../escape", "tool_name": "Bash"})
            self.assertFalse((Path(d) / "escape.jsonl").exists())
            self.assertTrue(all(home in p.parents for p in Path(d).rglob("*.jsonl")))

    def test_secret_named_dict_values_are_masked(self):
        h = load_hook()
        out = h.scrub({"tool_input": {"api_key": "plainsecret123", "password": "hunter2", "query": "ok"}})
        self.assertNotIn("plainsecret123", json.dumps(out))
        self.assertNotIn("hunter2", json.dumps(out))
        self.assertEqual(out["tool_input"]["query"], "ok")

    def test_folders_are_private(self):
        import stat
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "cs"
            self.run_hook(home, {"hook_event_name": "PostToolUse", "session_id": "s1", "tool_name": "Bash"})
            for folder in (home, home / "ledger"):
                self.assertEqual(stat.S_IMODE(folder.stat().st_mode), 0o700, folder)

    def test_never_blocks_on_bad_input(self):
        with tempfile.TemporaryDirectory() as d:
            import os, subprocess, sys
            r = subprocess.run([sys.executable, str(ROOT / "hooks" / "ledger_hook.py")], input="not json", text=True,
                               env=dict(os.environ, CORE_SAMPLE_HOME=d), capture_output=True)
            self.assertEqual(r.returncode, 0)


class Redaction2(unittest.TestCase):
    def test_redact_terms_reach_every_table(self):
        from core_sample.ledger import redact_terms
        t = {"tool_calls": [{"input": "grep -E 'privatetopic|other' x", "n": 1}], "events": [{"text": "PrivateTopic here"}]}
        redact_terms(t, ["privatetopic"])
        self.assertNotIn("privatetopic", json.dumps(t).lower())


class Transcript(unittest.TestCase):
    def test_outcomes_and_exchanges(self):
        lines = [
            {"type": "user", "timestamp": "2026-10-08T23:16:00Z", "origin": {"kind": "human"}, "message": {"content": "do it"}},
            {"type": "assistant", "timestamp": "2026-10-08T23:16:01Z", "message": {"content": [
                {"type": "tool_use", "id": "a", "name": "Bash", "input": {"command": "git push | tail", "description": "Push"}}]}},
            {"type": "user", "timestamp": "2026-10-08T23:16:03Z", "toolUseResult": {"stdout": "fatal: denied"},
             "message": {"content": [{"type": "tool_result", "tool_use_id": "a", "content": "fatal: denied"}]}},
            {"type": "assistant", "timestamp": "2026-10-08T23:16:04Z", "message": {"content": [
                {"type": "tool_use", "id": "b", "name": "Read", "input": {"file_path": "/x"}}]}},
            {"type": "user", "timestamp": "2026-10-08T23:16:05Z",
             "message": {"content": [{"type": "tool_result", "tool_use_id": "b", "is_error": True, "content": "File does not exist"}]}},
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
            fh.write("\n".join(json.dumps(l) for l in lines))
        tr = parse_transcript(Path(fh.name))
        self.assertEqual(len(tr["prompts"]), 1)
        self.assertEqual([c["outcome"] for c in tr["calls"]], ["error_unflagged", "error"])
        self.assertEqual(tr["calls"][0]["duration_s"], 2.0)


class Ledger(unittest.TestCase):
    def test_attested_failure_marks_unrecorded_call(self):
        calls = number_calls([{"exchange": "E01", "tool": "Bash", "input": "npm ci", "description": "",
                               "record_source": "export", "outcome": "unrecorded", "failure_id": ""}])
        f = link_failures([{"failure_id": "F01", "exchange": "E01", "detected_in": "E02", "link_basis": "log",
                            "call": {"exchange": "E01", "seq": 1}}], calls)
        self.assertEqual(calls[0]["outcome"], "attested_fail")
        self.assertEqual(f[0]["exchanges_to_detect"], 1)

    def test_dangling_call_reference_fails_loudly(self):
        with self.assertRaises(ValueError):
            link_failures([{"failure_id": "F09", "exchange": "E01", "detected_in": "E01", "link_basis": "log",
                            "call": {"exchange": "E01", "seq": 9}}], [])

    def test_unknown_vocabulary_fails_loudly(self):
        bad = {"exchanges": [{"exchange": "E01"}], "tool_calls": [],
               "failures": [{"failure_id": "F1", "layer": "vibes", "detection": "measure", "detected_by": "self",
                             "caught": "before-delivery", "status": "fixed", "link_basis": "log", "severity": 1}]}
        with self.assertRaisesRegex(ValueError, "vibes"):
            validate(bad)


if __name__ == "__main__":
    unittest.main()
