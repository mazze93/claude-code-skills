---
name: read-arxiv-paper
description: >
  Use this skill when asked to read an arxiv paper given an arxiv URL.
  Fetches the LaTeX source (not the PDF), unpacks it, locates the entrypoint,
  reads the full paper recursively through \input{}/\include{} directives, and
  produces a project-contextualized summary at ./knowledge/summary_{tag}.md.
---

# Read arXiv Paper

Fetch, unpack, and deeply read an arXiv paper's LaTeX source, then produce a
summary that explicitly connects the paper's findings to the current project context.

---

## Part 1: Normalize the URL

You will receive an arXiv URL in one of these forms:

```
https://arxiv.org/abs/2601.07372
https://www.arxiv.org/abs/2601.07372
https://arxiv.org/pdf/2601.07372
```

Extract the numeric (or alphanumeric) arXiv ID — everything after the last `/`.
Strip any file extension (`.pdf`, `.html`).

The source URL is always:

```
https://arxiv.org/src/{arxiv_id}
```

Example: `https://arxiv.org/abs/2601.07372` → `https://arxiv.org/src/2601.07372`

---

## Part 2: Download the Paper Source

Target path: `~/.cache/knowledge/{arxiv_id}.tar.gz`

**Check before downloading** — if the file already exists, skip the download.

```bash
ARXIV_ID="2601.07372"
CACHE_DIR="$HOME/.cache/knowledge"
TARBALL="$CACHE_DIR/$ARXIV_ID.tar.gz"

mkdir -p "$CACHE_DIR"

if [ ! -f "$TARBALL" ]; then
  curl -L --fail --silent --show-error \
    -o "$TARBALL" \
    "https://arxiv.org/src/$ARXIV_ID"
fi
```

**Failure modes to handle:**
- `curl` returns non-zero: network error or rate-limit — surface the error, do not proceed.
- Downloaded file is not a valid gzip (check with `file "$TARBALL"`): arXiv sometimes
  returns a bare `.tex` file with no archive wrapper. In that case rename to
  `$CACHE_DIR/$ARXIV_ID.tex` and skip Part 3.

---

## Part 3: Unpack the Archive

Unpack into `~/.cache/knowledge/{arxiv_id}/`.

```bash
EXTRACT_DIR="$CACHE_DIR/$ARXIV_ID"
mkdir -p "$EXTRACT_DIR"
tar -xzf "$TARBALL" -C "$EXTRACT_DIR"
```

If the tarball contains a single top-level directory, the actual files will be
one level deeper — account for this when locating the entrypoint.

---

## Part 4: Locate the Entrypoint

Apply these heuristics in order — stop at the first match:

1. A file literally named `main.tex` anywhere in the tree.
2. A `.tex` file that contains `\documentclass` (the root document).
3. If multiple files contain `\documentclass`, prefer the one that also contains
   `\begin{document}`.
4. If still ambiguous, pick the largest `.tex` file by byte size.

```bash
# Heuristic search
find "$EXTRACT_DIR" -name "*.tex" | xargs grep -l '\\begin{document}' 2>/dev/null | head -1
```

Record the resolved entrypoint path as `ENTRY_TEX`.

---

## Part 5: Read the Paper

**Read `ENTRY_TEX` in full.**

Then recursively follow every `\input{...}` and `\include{...}` directive found in
any file you read, resolving paths relative to the file that contains them.
Add `.tex` extension if absent. Skip files that do not exist (some sources reference
generated files).

Continue until no unread includes remain.

**Also read** (if present):
- Any `.bib` file referenced by `\bibliography{...}` — skim for key citations.
- Abstract and introduction sections get full attention.
- Skip raw data files, generated figures (`.eps`, `.pdf`, `.png`), and style files
  (`.sty`, `.cls`) unless they contain macro definitions that affect reading the prose.

Do not attempt to render or compile the LaTeX. Read it as structured text.

---

## Part 6: Produce the Summary

### Output path

```
./knowledge/summary_{tag}.md
```

- Use the **local** `knowledge/` directory (relative to the working directory where
  Claude Code is running), not `~/.cache/`.
- Generate a concise, meaningful `tag` from the paper's subject — e.g.,
  `conditional_memory`, `sparse_attention`, `rag_retrieval`, `diffusion_planning`.
- **Check for collisions first**: if `./knowledge/summary_{tag}.md` already exists,
  append a numeric suffix (`_2`, `_3`, …) rather than overwriting.

```bash
mkdir -p ./knowledge
```

### Summary structure

```markdown
# {Full Paper Title}

**arXiv:** {arxiv_id}  
**Authors:** {author list}  
**Published:** {date if available}  
**Tag:** `{tag}`

---

## What It Does

2–4 sentence plain-language summary of the paper's core contribution.
What problem it solves, what the key insight is, what makes it novel.

## How It Works

The mechanism in enough detail to implement or evaluate it.
Key equations, algorithms, or architectural decisions — described in prose,
not reproduced verbatim (copyright). Note any important hyperparameters or
design constraints the authors flag.

## Results & Claims

What the paper demonstrates empirically. Be specific: benchmark names,
metric names, reported numbers. Flag any results that seem cherry-picked
or where ablations are missing.

## Limitations & Failure Modes

What the authors acknowledge as limitations. What you notice that they
may not have foregrounded.

## Relevance to This Project

**This section is the primary value of the summary.**

Before writing it, read the relevant parts of the current project codebase
(check for a README, CLAUDE.md, or equivalent orientation file first).
Then explicitly answer:

- Does this paper's technique apply to anything we are currently building?
- Is there a specific module, component, or open problem this could address?
- What would a concrete experiment or prototype look like?
- Are there warnings — cases where this approach is known to fail — that
  apply to our constraints (latency, context length, data availability, etc.)?

Be direct. "Not relevant" is a valid answer; explain why.

## Key References to Follow

3–5 citations from the paper worth reading next, with one-line rationale for each.
```

### Before writing the Relevance section

1. Read `./CLAUDE.md` or `./README.md` (whichever exists) to orient yourself in
   the project.
2. Read any source files directly related to the paper's domain — e.g., if the
   paper is about retrieval, find and read the retrieval-related modules.
3. Cite specific file paths and function names when making connections.

---

## Operational Notes

- **Do not hallucinate paper content.** If a section is unreadable (encoding issue,
  missing include), note it in the summary explicitly.
- **Do not reproduce extended verbatim passages.** Paraphrase; quote only short
  phrases (< 30 words) to anchor a specific claim.
- **Rate limits:** arXiv may throttle; if the download fails with HTTP 429,
  wait 30 seconds and retry once before surfacing the error.
- **Single-file papers:** some older submissions are a single `.tex` with no
  includes — that's fine, just read it straight through.
