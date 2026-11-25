# blind-review

Builds a blind paired review page from a skill-creator eval workspace.

Each case shows its prompt once and its two outputs as Answer A and Answer B. Which arm
is which stays hidden until the reviewer records a preference (A, B or tie), an optional
note on the evidence, and the time they spent reading. Only then does the page show the
arms and the rubric results.

```sh
python3 build_blind_review.py <workspace>/iteration-1 \
  --skill-name Backwalk --skill-revision <hash or commit> \
  --executor-model "<model id; say so if inferred>" --run-date YYYY-MM-DD \
  --out page.html
```

A case is skipped, and named on stderr, unless both arms left an output.

## Why this exists

The stock skill-creator viewer shows one run at a time with the arm named up front, and
renders long Markdown as preformatted text. Review of the first `backwalk` packet also
found that both of its feedback handlers treat a resolved `fetch()` as success, so a 404
or 500 can show "Saved" without storing anything, and that finishing a review exports
every run with blank feedback, including runs the reviewer skipped.

This page is built to avoid those three things:

- **The case is the unit.** One prompt, two answers side by side (one at a time with a
  persistent A/B switch on a phone), Markdown rendered with a heading outline per answer.
- **"Saved" means saved.** Published as a claude.ai Artifact with the `db` capability,
  the page says "Saved to the review record" only after the write resolves. A failed
  write says so, keeps the answer in the browser, and offers a retry. There is always an
  explicit JSON export.
- **Review state is explicit.** Every case is `unreviewed`, `reviewed_no_comment` or
  `reviewed_with_comment`, in the record and in the export.

## Publishing

Publish the built page as an Artifact with these capabilities, so each reviewer's answers
sit in their own subtree and a second reviewer cannot read the first one's choices:

```json
{"db": {"rules": [
  {"path": "reviews", "read": "admin", "write": "owner"},
  {"path": "reviews/{self}", "read": "interact", "write": "interact"}]},
 "user": {}, "downloads": true}
```

Records land at `reviews/<reviewer id>/cases/<case>`. Opened as a plain file, the page
works without a record: answers stay in the browser and the export still works.

## Limits

- Slot assignment comes from a hash of the packet and case names. It is in the page
  source, so the blinding stops a reader, not someone who goes looking.
- An output can give its own arm away: a skill's template is recognizable, and the
  longer answer is usually the one written with the skill.
- A reviewer who has already seen the labelled outputs is not blind. Use a second reader.
- The page was checked once at desktop and phone width, opened as a plain file. The save
  path against a live record was checked by reading and writing the record from outside
  the page, not by clicking through the published page.
