# Annotation files — shapes and one real example each

All files are JSON in the session folder. `python3 -m core_sample init` writes
empty templates. Coded values must come from `core_sample/taxonomy.py`; the
build rejects anything else.

## session.json
```json
{"session_id": "2026-10-08_models-lying-about-their-work", "title": "A Picture of What It Expected",
 "chat_title": "Models lying about their work", "chat_url": "https://claude.ai/chat/…",
 "timezone": "America/New_York", "date": "2026-10-08", "project": "mazze-leczzare-blog",
 "transcript_first_exchange": "E11", "transcript_exchange_offset": 12,
 "how_found_sets": ["map-rebuild"],
 "notes": ["The transcript file holds only post-compaction entries (from 19:13 EDT)…"]}
```
- `transcript_first_exchange`: the exchange in progress when the transcript file begins.
- `transcript_exchange_offset`: exchange number of the transcript's first prompt.
- `export_turn_map` (optional): `{"21": "E11"}` when export turns don't alternate.
- `how_found_sets` (optional): finding sets to chart by how each defect was found.
- `notes`: shown on the index under "About this record". Put every known gap here.

## exchanges.json
```json
{"exchange": "E04", "at_local": "17:44", "initiator": "Mazze",
 "prompt": "3 things: first, I'd like you do do your own svg Blake inspired art piece…",
 "prompt_provenance": "Verbatim", "kind": "Request", "export_turn": "6",
 "response_summary": "Made the original plate in 20 kept renders, read 9 sources, wrote the MDX field note…",
 "response_kind": "Build", "outputs": "Plate v1.0.0, plate log, research notes, post patch v0.1.0"}
```
`initiator` is the person's name, or `Harness` for a stop-hook. Exchanges with no
tools (reflection, conversation) still get a row; the "no tools" count is a finding.

## calls_manual.json — only for calls no file holds
```json
{"exchange": "E10", "tool": "Bash", "description": "Load the live post in Chromium and check whether its embed is CSP-blocked",
 "input": "node live.cjs"}
```
Order matters: rows are numbered in file order within their exchange.

## failures.json
```json
{"failure_id": "F18", "exchange": "E04", "call": {"exchange": "E04", "seq": 138},
 "link_basis": "log", "layer": "environment", "class": "silent-omission",
 "summary": "The commit silently left out the logs/ folder (.gitignore); the post would have shipped three dead links.",
 "detection": "reread", "detected_by": "self", "detected_in": "E04", "caught": "before-delivery",
 "severity": 3, "status": "fixed", "evidence": ".gitignore:54:logs   public/…/logs/plate-build-log.md"}
```
- `call`: `null`, `{"exchange","seq"}`, or `{"exchange","tool","contains"}` (matches input or description).
- `evidence`: verbatim only (a quoted log line, an error line). Leave it empty rather than paraphrase.
- `class` is free text, but reuse classes across sessions (`missing-dependency`, `wrong-api`,
  `self-matching-kill`, `silent-omission`, `stale-claim`, `overstatement`, `false-memory`,
  `stale-artifact`, `misleading-capture`, `unasked-decision`…) so they can be counted.
- Severity: 1 noise or cosmetic · 2 wrong output, caught · 3 would ship (or shipped) a false claim or broken page.

## findings.json — defects in the work itself, grouped by set
```json
{"finding_id": "P015", "set": "plate-build", "ref": "iter 015", "subject": "Mend and figure",
 "detail": "Figure a beige lump; mend a lightning bolt.", "how_found": "render-look",
 "resolution": "Figure rebuilt from jointed segments; calmer seam.", "status": "Failed → rebuilt", "exchange": "E04"}
```
A set whose refs read `iter N` (five or more) gets a convergence chart automatically:
statuses starting "Failed", "Partly failed" or "Overclaim" count as failures.

## sources.json
```json
{"source_id": "R08", "title": "OverclaimBench — Smyth et al. (preprint)", "year": "2026",
 "url": "https://arxiv.org/abs/2609.20812", "finding": "80.4% of incomplete runs misleading…",
 "bearing": "Most direct evidence; implicates the model family.", "checked": "Read (alphaXiv); not peer-reviewed"}
```
`checked` says how far it was read. Keep "Not read" / "Excluded" rows.

## deliverables.json / open_items.json
```json
{"deliverable_id": "D14", "name": "csp-allow-same-origin-artifact-frames_v1.0.0.patch", "version": "1.0.0",
 "type": "CSP fix (commit 5f966ff)", "destination": "Sent as file; pushed", "exchange": "E10", "provenance": "Tool"}
{"item_id": "O06", "item": "Cloudflare Pages preview of the branch may expose public/ files", "kind": "Exposure",
 "status": "Unverified", "owner": "Mazze", "next_action": "Check the Pages project's preview deployment settings", "exchange": "E12"}
```
Open-item status: Open · Decision needed · Unverified · Idea · Done.
