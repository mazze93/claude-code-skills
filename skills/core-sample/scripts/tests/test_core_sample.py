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
