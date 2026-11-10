#!/usr/bin/env python3
"""Build a blind paired review page from a skill-creator eval workspace.

Reads one iteration directory laid out as

    <iteration>/<case>/eval_metadata.json
    <iteration>/<case>/<arm>/outputs/<one .md file>
    <iteration>/<case>/<arm>/grading.json     (optional)
    <iteration>/<case>/<arm>/timing.json      (optional)

and writes a single HTML page in which each case shows its prompt once and
its two outputs as "Answer A" and "Answer B". Which arm sits in slot A is
decided per case from a hash, so it is stable across rebuilds and not
something the builder chose by looking at the outputs.

A case is skipped, and reported, unless BOTH arms have an output: a blind
pair with one side missing is not a pair.

    python3 build_blind_review.py WORKSPACE/iteration-1 \\
        --skill-name Backwalk --skill-revision 159c7854c1bf48f3 \\
        --executor-model "claude-opus-4-7 (inferred; not logged at run time)" \\
        --run-date 2026-11-07 --out page.html
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ARMS = ("with_skill", "without_skill")
TEMPLATE = Path(__file__).with_name("template.html")


def read_json(path: Path) -> dict | None:
    """Return parsed JSON, or None when the file is absent."""
    if not path.exists():
        return None
    return json.loads(path.read_text())


def find_output(arm_dir: Path) -> Path | None:
    """The single Markdown output of a run, or None if the run left none."""
    outputs = sorted((arm_dir / "outputs").glob("*.md"))
    return outputs[0] if outputs else None


def word_count(text: str) -> int:
    return len(re.findall(r"\S+", text))


def slot_a_arm(packet_id: str, case_id: str) -> str:
    """Deterministic, content-blind choice of which arm is shown as Answer A."""
    digest = hashlib.sha256(f"{packet_id}:{case_id}".encode()).digest()
    return ARMS[digest[0] % 2]


def load_arm(arm_dir: Path, arm: str) -> dict | None:
    """Everything the page needs about one run, or None if it has no output."""
    output = find_output(arm_dir)
    if output is None:
        return None
    text = output.read_text()
    grading = read_json(arm_dir / "grading.json") or {}
    timing = read_json(arm_dir / "timing.json") or {}
    summary = grading.get("summary", {})
    return {
        "arm": arm,
        "text": text,
        "words": word_count(text),
        "rubric_passed": summary.get("passed"),
        "rubric_total": summary.get("total"),
        "seconds": timing.get("total_duration_seconds"),
        "tokens": timing.get("total_tokens"),
    }


def title_from_id(case_id: str) -> str:
    return case_id.replace("-", " ")


def load_case(case_dir: Path, packet_id: str) -> tuple[dict | None, str | None]:
    """Return (case, None), or (None, reason) when the pair is incomplete."""
    meta = read_json(case_dir / "eval_metadata.json")
    if meta is None:
        return None, "no eval_metadata.json"
    arms = {arm: load_arm(case_dir / arm, arm) for arm in ARMS}
    missing = [arm for arm, data in arms.items() if data is None]
    if missing:
        return None, "no output for " + ", ".join(missing)
    first = slot_a_arm(packet_id, case_dir.name)
    second = ARMS[1 - ARMS.index(first)]
    prompt = re.sub(r"\n*Input files:.*\Z", "", meta["prompt"].strip(), flags=re.S).strip()
    return {
        "id": case_dir.name,
        "title": title_from_id(case_dir.name),
        "prompt": prompt,
        "slots": {"A": arms[first], "B": arms[second]},
    }, None


def build_packet(iteration: Path, args: argparse.Namespace) -> tuple[dict, list[str]]:
    packet_id = f"{args.skill_name.lower()}-{iteration.name}"
    cases, skipped = [], []
    for case_dir in sorted(p for p in iteration.iterdir() if p.is_dir()):
        case, reason = load_case(case_dir, packet_id)
        if case is None:
            skipped.append(f"{case_dir.name}: {reason}")
        else:
            cases.append(case)
    meta = {
        "packet_id": packet_id,
        "skill": args.skill_name,
        "skill_revision": args.skill_revision,
        "executor_model": args.executor_model,
        "run_date": args.run_date,
        "runs_per_cell": 1,
        "arm_labels": {
            "with_skill": f"with {args.skill_name}",
            "without_skill": f"without {args.skill_name}",
        },
    }
    return {"meta": meta, "cases": cases}, skipped


def render(packet: dict, title: str) -> str:
    """Inject the packet into the template. `<` is escaped so no output text
    can close the JSON script element."""
    data = json.dumps(packet, ensure_ascii=False).replace("<", "\\u003c")
    page = TEMPLATE.read_text()
    return page.replace("__PACKET_JSON__", data).replace("__PAGE_TITLE__", title)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("iteration", type=Path, help="Path to <workspace>/iteration-N")
    p.add_argument("--skill-name", required=True)
    p.add_argument("--skill-revision", required=True, help="Content hash or commit of the tested skill")
    p.add_argument("--executor-model", required=True, help="Model that produced the outputs; say so if inferred")
    p.add_argument("--run-date", required=True)
    p.add_argument("--out", type=Path, required=True)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    packet, skipped = build_packet(args.iteration, args)
    for line in skipped:
        print(f"SKIPPED {line}", file=sys.stderr)
    if not packet["cases"]:
        print("No complete pairs; nothing to build.", file=sys.stderr)
        return 1
    title = f"{args.skill_name} Blind Review"
    args.out.write_text(render(packet, title))
    for case in packet["cases"]:
        a, b = case["slots"]["A"], case["slots"]["B"]
        print(f"{case['id']}: A={a['arm']} ({a['words']} words)  B={b['arm']} ({b['words']} words)")
    print(f"Wrote {args.out} ({args.out.stat().st_size:,} bytes), {len(packet['cases'])} cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
