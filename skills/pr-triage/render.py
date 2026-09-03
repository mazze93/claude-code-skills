"""
render.py — Output renderers for pr-triage.

Three targets: terminal (default), slack (Block Kit JSON), github (markdown).
All three receive the same PRClassification list and produce target-appropriate output.
The classification logic is identical regardless of render target — only presentation differs.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from classify import ActorType, PRClassification, Severity, StuckType


# ── Symbol tables ─────────────────────────────────────────────────────────────

REVIEW_SYM = {
    "APPROVED":           "✅",
    "CHANGES_REQUESTED":  "🔄",
    "REVIEW_REQUIRED":    "⏳",
    None:                 "—",
}

CI_SYM = {
    "SUCCESS":  "✅",
    "FAILURE":  "❌",
    "PENDING":  "⏳",
    "ERROR":    "❌",
    None:       "—",   # No CI configured — not the same as failing
}

SYNC_SYM = {
    "MERGEABLE":   "✅",
    "CONFLICTING": "⚠️ ",
    "UNKNOWN":     "⏳",
}

STUCK_LABEL = {
    StuckType.BLOCKED_ON_AUTHOR:   "AUTHOR",
    StuckType.BLOCKED_ON_REVIEWER: "REVIEWER",
    StuckType.BLOCKED_ON_CI:       "CI",
    StuckType.BLOCKED_ON_CONFLICT: "CONFLICT",
    StuckType.ABANDONED:           "ABANDONED",
    StuckType.READY_TO_MERGE:      "READY",
    StuckType.HEALTHY:             "OK",
}

SEV_PREFIX = {
    Severity.HIGH:   "❗",
    Severity.MEDIUM: "⚠️ ",
    Severity.NONE:   "  ",
}

_ACTIONABLE = {
    StuckType.ABANDONED,
    StuckType.BLOCKED_ON_CONFLICT,
    StuckType.BLOCKED_ON_CI,
    StuckType.BLOCKED_ON_AUTHOR,
    StuckType.BLOCKED_ON_REVIEWER,
    StuckType.READY_TO_MERGE,
}


# ── Helpers ───────────────────────────────────────────────────────────────────


def _age_str(days: float) -> str:
    if days < 1:
        h = int(days * 24)
        return f"{h}h"
    return f"{int(days)}d"


def _age_days(c: PRClassification) -> float:
    now = datetime.now(timezone.utc)
    return (now - c.pr.created_at).total_seconds() / 86_400


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def _actionable(items: list[PRClassification]) -> list[PRClassification]:
    return sorted(
        [c for c in items if c.stuck_type in _ACTIONABLE],
        key=lambda c: (-c.severity.value, c.staleness_days),
        reverse=False,
    )


# ── Terminal renderer ─────────────────────────────────────────────────────────


def render_terminal(
    classifications: list[PRClassification],
    errors: dict[str, str],
    repo_count: int,
    run_date: str,
) -> str:
    """Fixed-width table for terminal output. Falls back to no-PR confirmation."""

    if not classifications and not errors:
        return f"pr-triage · {run_date}\nNo open PRs across {repo_count} repo(s). ✅"

    lines: list[str] = [f"pr-triage · {repo_count} repo(s) · {run_date}", ""]

    # Column widths
    W_REPO   = 24
    W_NUM    = 5
    W_TITLE  = 38
    W_AUTHOR = 14
    W_AGE    = 5
    W_REV    = 8
    W_CI     = 5
    W_SYNC   = 6
    W_STATUS = 14

    fmt = (
        f"{{:<{W_REPO}}} {{:>{W_NUM}}}  {{:<{W_TITLE}}} {{:<{W_AUTHOR}}} "
        f"{{:>{W_AGE}}}  {{:<{W_REV}}} {{:<{W_CI}}} {{:<{W_SYNC}}} {{:<{W_STATUS}}}"
    )
    sep = "─" * 115

    lines.append(fmt.format(
        "REPO", "#", "TITLE", "AUTHOR", "AGE",
        "REVIEW", "CI", "SYNC", "STATUS",
    ))
    lines.append(sep)

    for c in classifications:
        pr    = c.pr
        age   = _age_days(c)
        lines.append(fmt.format(
            _truncate(pr.repo, W_REPO),
            f"#{pr.number}",
            _truncate(pr.title, W_TITLE),
            _truncate(pr.author, W_AUTHOR),
            _age_str(age),
            REVIEW_SYM.get(pr.review_decision, "—"),
            CI_SYM.get(pr.ci_status, "—"),
            SYNC_SYM.get(pr.mergeable, "—"),
            STUCK_LABEL[c.stuck_type],
        ))

    # Fetch errors
    if errors:
        lines += ["", f"── Fetch errors {'─' * 98}"]
        for repo, msg in sorted(errors.items()):
            lines.append(f"  {repo}: {msg}")

    # Needs-action section — sorted by severity desc, then staleness desc
    flagged = _actionable(classifications)
    if flagged:
        lines += ["", f"── Needs Action {'─' * 98}"]
        for c in flagged:
            pr     = c.pr
            prefix = SEV_PREFIX[c.severity]
            label  = f"[{STUCK_LABEL[c.stuck_type]}]"
            lines.append(
                f"{prefix} {_truncate(pr.repo, W_REPO)} #{pr.number:<5} "
                f"{label:<12} @{_truncate(pr.author, 16):<18} — {c.message}"
            )

    return "\n".join(lines)


# ── Slack Block Kit renderer ──────────────────────────────────────────────────


def render_slack(
    classifications: list[PRClassification],
    errors: dict[str, str],
    repo_count: int,
    run_date: str,
) -> dict:
    """Slack Block Kit payload. Post via webhooks or the Slack API."""

    def mrkdwn(text: str) -> dict:
        return {"type": "mrkdwn", "text": text}

    blocks: list[dict] = [
        {"type": "header", "text": {"type": "plain_text", "text": f"PR Triage · {run_date}"}},
        {"type": "context", "elements": [
            mrkdwn(f"{repo_count} repo(s) · {len(classifications)} open PR(s)"),
        ]},
        {"type": "divider"},
    ]

    if not classifications:
        blocks.append({"type": "section", "text": mrkdwn("✅ No open PRs.")})
        return {"blocks": blocks}

    # Flagged items with direct links
    flagged = _actionable(classifications)
    if flagged:
        blocks.append({"type": "section", "text": mrkdwn("*Needs Action*")})
        for c in flagged:
            pr     = c.pr
            prefix = "❗" if c.severity == Severity.HIGH else ("⚠️" if c.severity == Severity.MEDIUM else "✅")
            label  = STUCK_LABEL[c.stuck_type]
            url    = f"https://github.com/{pr.repo}/pull/{pr.number}"
            blocks.append({"type": "section", "text": mrkdwn(
                f"{prefix} *<{url}|{pr.repo} #{pr.number}>* `[{label}]` @{pr.author} — {c.message}"
            )})
        blocks.append({"type": "divider"})

    # Summary table as plain text
    rows = []
    for c in classifications:
        pr  = c.pr
        age = _age_str(_age_days(c))
        url = f"https://github.com/{pr.repo}/pull/{pr.number}"
        rows.append(
            f"<{url}|{pr.repo} #{pr.number}> {_truncate(pr.title, 45)} · "
            f"@{pr.author} · {age} · "
            f"{REVIEW_SYM.get(pr.review_decision, '—')} "
            f"{CI_SYM.get(pr.ci_status, '—')} "
            f"{SYNC_SYM.get(pr.mergeable, '—')}"
        )

    blocks.append({"type": "section", "text": mrkdwn("\n".join(rows))})

    if errors:
        error_text = "\n".join(f"⚠️ {repo}: {msg}" for repo, msg in errors.items())
        blocks.append({"type": "section", "text": mrkdwn(f"*Fetch errors*\n{error_text}")})

    return {"blocks": blocks}


# ── GitHub markdown renderer ──────────────────────────────────────────────────


def render_github(
    classifications: list[PRClassification],
    errors: dict[str, str],
    repo_count: int,
    run_date: str,
) -> str:
    """GitHub-flavored markdown. Post as a comment or save as a .md report."""

    if not classifications:
        return f"**pr-triage** · {run_date}\n\nNo open PRs across {repo_count} repo(s). ✅"

    lines: list[str] = [
        f"**pr-triage** · {run_date} · {repo_count} repo(s) · {len(classifications)} open PR(s)\n"
    ]

    # Table
    lines += [
        "| Repo | PR | Title | Author | Age | Review | CI | Sync | Status |",
        "|------|-----|-------|--------|-----|--------|-----|------|--------|",
    ]

    for c in classifications:
        pr    = c.pr
        age   = _age_str(_age_days(c))
        url   = f"https://github.com/{pr.repo}/pull/{pr.number}"
        lines.append(
            f"| `{pr.repo}` "
            f"| [{pr.number}]({url}) "
            f"| {_truncate(pr.title, 45)} "
            f"| @{pr.author} "
            f"| {age} "
            f"| {REVIEW_SYM.get(pr.review_decision, '—')} "
            f"| {CI_SYM.get(pr.ci_status, '—')} "
            f"| {SYNC_SYM.get(pr.mergeable, '—')} "
            f"| **{STUCK_LABEL[c.stuck_type]}** |"
        )

    # Needs-action section
    flagged = _actionable(classifications)
    if flagged:
        lines.append("\n**Needs Action**\n")
        for c in flagged:
            pr     = c.pr
            prefix = "❗" if c.severity == Severity.HIGH else ("⚠️" if c.severity == Severity.MEDIUM else "✅")
            url    = f"https://github.com/{pr.repo}/pull/{pr.number}"
            label  = STUCK_LABEL[c.stuck_type]
            lines.append(f"- {prefix} [{pr.repo} #{pr.number}]({url}) `[{label}]` @{pr.author} — {c.message}")

    if errors:
        lines.append("\n**Fetch errors**\n")
        for repo, msg in errors.items():
            lines.append(f"- ⚠️ `{repo}`: {msg}")

    return "\n".join(lines)
