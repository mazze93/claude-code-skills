"""Stdlib tests for core-sample. Run: python3 -m unittest discover -s tests"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from core_sample import taxonomy as T
from core_sample.ledger import link_failures, number_calls, validate, reconcile_observations, reconcile_unkeyed_mentions, build_ledger
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
            self.run_hook(home, {"hook_event_name": "PostToolUse", "session_id": "s1",
                                 "tool_name": "Bash", "tool_input": {"command": load_hook().ARM_COMMAND}})
            self.run_hook(home, {"hook_event_name": "PostToolUse", "session_id": "s1",
                                 "tool_name": "Bash", "tool_input": {"command": "echo ok"},
                                 "tool_use_id": "t1", "tool_response": "ok"})
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



class CaptureLifecycle(unittest.TestCase):
    """A tool-result hook must stay dormant until the exact opt-in command."""

    def fire(self, home, sid, event="PostToolUse", command="echo test", response="ok"):
        import os, subprocess, sys
        p = {"session_id": sid, "hook_event_name": event, "tool_name": "Bash",
             "tool_input": {"command": command}, "tool_use_id": "tool-" + command,
             "tool_response": response}
        return subprocess.run(
            [sys.executable, str(ROOT / "hooks" / "ledger_hook.py")],
            input=json.dumps(p), text=True, capture_output=True,
            env=dict(os.environ, CORE_SAMPLE_HOME=str(home))
        )

    def test_explicit_arm_and_disarm_scope(self):
        h = load_hook()
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "cs"
            self.fire(home, "session-one")
            self.assertFalse((home / "ledger").exists(), "capture is off by default")
            self.fire(home, "session-one", command=h.ARM_COMMAND)
            self.fire(home, "session-one", command="echo during", response="result1")
            self.fire(home, "session-two", command="echo independent", response="result2")
            self.fire(home, "session-one", command=h.DISARM_COMMAND)
            self.fire(home, "session-one", command="echo after", response="result3")
            rows = [json.loads(x) for x in (home / "ledger" / "session-one.jsonl").read_text().splitlines()]
            self.assertEqual([x["event"] for x in rows],
                             ["CaptureStarted", "PostToolUse", "CaptureStopped"])
            self.assertNotIn("result3", json.dumps(rows))
            self.assertNotIn("result2", json.dumps(rows))
            self.assertFalse((home / "ledger" / "session-two.jsonl").exists())
            self.assertEqual((home / "state" / "session-one.state").read_text().strip(), "off")

    def test_arming_is_successful_event_not_arbitrary_text(self):
        h = load_hook()
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "cs"
            self.fire(home, "s1", event="PostToolUseFailure", command=h.ARM_COMMAND)
            self.fire(home, "s1", command="echo " + h.ARM_COMMAND)
            self.assertFalse((home / "ledger").exists())

    def test_session_end_disarms_and_raw_archive_is_opt_in(self):
        h = load_hook()
        with tempfile.TemporaryDirectory() as d:
            home = Path(d) / "cs"
            self.fire(home, "s1", command=h.ARM_COMMAND)
            self.fire(home, "s1", event="SessionEnd")
            self.assertEqual((home / "state" / "s1.state").read_text().strip(), "off")
            self.assertFalse((home / "archive").exists())

    def test_nested_secret_values_masked(self):
        h = load_hook()
        self.assertEqual(h.scrub({"token": {"private": "value"}})["token"], "[REDACTED]")


class EvidenceReconciliation(unittest.TestCase):
    def row(self, uid, outcome="ok", source="transcript"):
        return {"tool_use_id": uid, "tool": "Bash", "input": "echo ok", "exchange": "E01",
                "record_source": source, "evidence_sources": source,
                "outcome": outcome, "outcome_source": "tool-flag",
                "error_signature": "", "error_excerpt": "", "ended_at": "now"}

    def test_reconciles_single_observation(self):
        t = self.row("t1")
        h = self.row("t1", source="hook")
        rows = reconcile_observations([t], [h])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["evidence_sources"], "transcript+hook")

    def test_restores_missing_result(self):
        t = self.row("t1", outcome="unrecorded")
        h = self.row("t1", outcome="error", source="hook")
        rows = reconcile_observations([t], [h])
        self.assertEqual(rows[0]["outcome"], "error")
        self.assertEqual(rows[0]["evidence_sources"], "transcript+hook")

    def test_rejects_conflicting_results(self):
        with self.assertRaisesRegex(ValueError, "conflicting observed"):
            reconcile_observations([self.row("t1")], [self.row("t1", "error", "hook")])

    def test_rejects_missing_identifier_and_collisions(self):
        with self.assertRaisesRegex(ValueError, "no tool_use_id"):
            reconcile_observations([self.row("t1")], [self.row("", source="hook")])
        with self.assertRaisesRegex(ValueError, "duplicate hook"):
            reconcile_observations([], [self.row("same", source="hook"),
                                        self.row("same", source="hook")])



class CrossSourceProvenance(unittest.TestCase):
    def row(self, tool_use_id, source="transcript"):
        return {"tool_use_id": tool_use_id, "tool": "Bash", "input": "echo ok",
                "exchange": "E01", "record_source": source, "evidence_sources": source,
                "outcome": "ok", "outcome_source": "tool-flag"}

    def test_unique_export_corroborates_without_extra_execution(self):
        observed = [self.row("tool1")]
        manual = [self.row("", "export")]
        extra, mentions = reconcile_unkeyed_mentions(manual, observed)
        self.assertEqual(len(extra), 0)
        self.assertEqual(mentions[0]["match_status"], "corroborated")
        self.assertEqual(observed[0]["evidence_sources"], "transcript+export")

    def test_ambiguous_repeated_calls_preserved_but_not_double_counted(self):
        observed = [self.row("tool1"), self.row("tool2")]
        extra, mentions = reconcile_unkeyed_mentions([self.row("", "export")], observed)
        self.assertFalse(extra)
        self.assertEqual(mentions[0]["match_status"], "ambiguous_overlap")
        self.assertEqual(len(observed), 2)

    def test_full_ledger_reconciles_hook_transcript_and_export(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "raw" / "export").mkdir(parents=True)
            (p / "session.json").write_text(json.dumps({
                "session_id": "test-sid", "timezone": "UTC",
                "transcript_first_exchange": "E01", "transcript_exchange_offset": 1
            }))
            (p / "exchanges.json").write_text(json.dumps([{
                "exchange": "E01", "initiator": "Person", "prompt": "do it"
            }]))
            transcript = [
                {"type": "user", "timestamp": "2026-10-09T10:00:00Z",
                 "origin": {"kind": "human"}, "message": {"content": "do it"}},
                {"type": "assistant", "timestamp": "2026-10-09T10:00:01Z",
                 "message": {"content": [{"type": "tool_use", "id": "tool1",
                  "name": "Bash", "input": {"command": "echo ok"}}]}},
                {"type": "user", "timestamp": "2026-10-09T10:00:02Z",
                 "message": {"content": [{"type": "tool_result", "tool_use_id": "tool1",
                  "content": "ok"}]}}
            ]
            (p / "raw" / "transcript.jsonl").write_text(
                "\n".join(json.dumps(x) for x in transcript))
            hook = {"event": "PostToolUse", "received_at": "2026-10-09T10:00:02Z",
                    "payload": {"tool_name": "Bash", "tool_use_id": "tool1",
                                "tool_input": {"command": "echo ok"}, "tool_response": "ok"}}
            (p / "raw" / "hook-ledger.jsonl").write_text(json.dumps(hook) + "\n")
            (p / "raw" / "export" / "page.txt").write_text(
                '<turn n="1">Assistant: <tool name="Bash">'
                '<parameter name="command">echo ok</parameter></tool></turn>')
            tables = build_ledger(p)
            self.assertEqual(len(tables["tool_calls"]), 1)
            self.assertEqual(tables["tool_calls"][0]["tool_use_id"], "tool1")
            self.assertEqual(tables["tool_calls"][0]["evidence_sources"],
                             "transcript+hook+export")
            self.assertEqual(tables["source_mentions"][0]["match_status"], "corroborated")


if __name__ == "__main__":
    unittest.main()
