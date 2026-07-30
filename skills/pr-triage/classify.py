"""
classify.py — Pure PR classification functions.

No I/O. No side effects. Every function is independently testable.
The entire classification taxonomy lives here.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


# ── Taxonomy ─────────────────────────────────────────────────────────────────


class StuckType(Enum):
    """What kind of stuck is this PR in? See references/taxonomy.md for full definitions."""
    ABANDONED          = "ABANDONED"           # No activity for N days — ownership unclear
    BLOCKED_ON_CONFLICT = "BLOCKED_ON_CONFLICT" # Merge conflicts — author must rebase
    BLOCKED_ON_CI      = "BLOCKED_ON_CI"       # Failing checks — author must investigate
    BLOCKED_ON_AUTHOR  = "BLOCKED_ON_AUTHOR"   # Changes requested — author must address
    BLOCKED_ON_REVIEWER = "BLOCKED_ON_REVIEWER" # Awaiting review too long — ping reviewers
    READY_TO_MERGE     = "READY_TO_MERGE"      # Approved + CI passing + no conflicts
    HEALTHY            = "HEALTHY"             # Active, no blockers


class ActorType(Enum):
    """Who needs to act next?"""
    AUTHOR   = "author"
    REVIEWER = "reviewer"
    CI       = "ci"
    UNKNOWN  = "unknown"
    NONE     = "none"


class Severity(Enum):
    """How urgently does this need attention?"""
    HIGH   = 2
    MEDIUM = 1
    NONE   = 0


# ── Data shapes ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PRData:
    """Normalized PR data from the GitHub API. All fields are the result of one
    gh pr list call — no secondary fetches required at classification time."""
    number:          int
    title:           str
    author:          str
    repo:            str
    created_at:      datetime
    updated_at:      datetime
    review_decision: Optional[str]   # APPROVED | CHANGES_REQUESTED | REVIEW_REQUIRED | None
    ci_status:       Optional[str]   # SUCCESS | FAILURE | PENDING | None (no CI configured)
    mergeable:       str             # MERGEABLE | CONFLICTING | UNKNOWN


@dataclass(frozen=True)
class TriageConfig:
    """Thresholds — all configurable, with opinionated defaults.
    These defaults are calibrated for a small-to-medium engineering team.
    Adjust in .claude/pr-triage.json."""
    reviewer_response_hours: int = 48   # Hours before REVIEW_REQUIRED → BLOCKED_ON_REVIEWER
    abandon_days:            int = 5    # Days of inactivity → ABANDONED
    staleness_warning_days:  int = 3    # Days after which severity escalates to HIGH


@dataclass(frozen=True)
class PRClassification:
    pr:           PRData
    stuck_type:   StuckType
    actor:        ActorType
    message:      str       # Actionable one-liner: what + who
    severity:     Severity
    staleness_days: float   # Days since last meaningful event (updated_at proxy)


# ── Classification ────────────────────────────────────────────────────────────


def _staleness(pr: PRData) -> float:
    """Days since updated_at — our proxy for 'last meaningful event'.

    We intentionally use updated_at rather than created_at. A 10-day-old PR with
    daily commits is healthy. A 2-day-old PR with no activity after a review request
    is already stuck. Age tells you history; staleness tells you urgency.
    """
    now = datetime.now(timezone.utc)
    return (now - pr.updated_at).total_seconds() / 86_400


def classify(pr: PRData, config: TriageConfig = TriageConfig()) -> PRClassification:
    """Classify a single PR into a stuck type.

    Priority order matters: conditions higher in the list override lower ones.
    See references/taxonomy.md for the full rationale behind ordering.
    """
    stale = _staleness(pr)

    def result(stuck_type: StuckType, actor: ActorType, message: str, severity: Severity) -> PRClassification:
        return PRClassification(pr, stuck_type, actor, message, severity, stale)

    # 1. ABANDONED — overrides everything. If nothing has happened in N days,
    #    the classification of why is less important than the fact that it's adrift.
    if stale >= config.abandon_days:
        return result(
            StuckType.ABANDONED, ActorType.UNKNOWN,
            f"No activity for {stale:.0f}d — determine ownership and intent",
            Severity.HIGH,
        )

    # 2. BLOCKED_ON_CONFLICT — merge conflicts block all review and CI work.
    #    Author must rebase before reviewers can meaningfully engage.
    if pr.mergeable == "CONFLICTING":
        severity = Severity.HIGH if stale >= config.staleness_warning_days else Severity.MEDIUM
        return result(
            StuckType.BLOCKED_ON_CONFLICT, ActorType.AUTHOR,
            f"Merge conflict — @{pr.author} to rebase or merge base",
            severity,
        )

    # 3. BLOCKED_ON_CI — failing checks block mergeability regardless of review state.
    if pr.ci_status in ("FAILURE", "ERROR"):
        severity = Severity.HIGH if stale >= config.staleness_warning_days else Severity.MEDIUM
        return result(
            StuckType.BLOCKED_ON_CI, ActorType.AUTHOR,
            f"CI failing — @{pr.author} to investigate checks",
            severity,
        )

    # 4. BLOCKED_ON_AUTHOR — changes were requested but no new commits since.
    #    updatedAt as proxy: if updated_at is recent, the author may have just responded.
    if pr.review_decision == "CHANGES_REQUESTED":
        severity = Severity.HIGH if stale >= config.staleness_warning_days else Severity.MEDIUM
        return result(
            StuckType.BLOCKED_ON_AUTHOR, ActorType.AUTHOR,
            f"Changes requested — @{pr.author} to address feedback",
            severity,
        )

    # 5. BLOCKED_ON_REVIEWER — review was requested but no response within threshold.
    #    We only flag this if staleness exceeds the threshold — a fresh review request
    #    is not yet blocked.
    if pr.review_decision == "REVIEW_REQUIRED":
        hours_waiting = stale * 24
        if hours_waiting >= config.reviewer_response_hours:
            severity = Severity.HIGH if hours_waiting >= config.reviewer_response_hours * 2 else Severity.MEDIUM
            return result(
                StuckType.BLOCKED_ON_REVIEWER, ActorType.REVIEWER,
                f"Awaiting review {hours_waiting:.0f}h — ping requested reviewers",
                severity,
            )

    # 6. READY_TO_MERGE — all green. The only reason it's not merged is that nobody
    #    has pressed the button. This surfaces as actionable in the output.
    if (
        pr.review_decision == "APPROVED"
        and pr.ci_status in ("SUCCESS", None)
        and pr.mergeable != "CONFLICTING"
    ):
        return result(
            StuckType.READY_TO_MERGE, ActorType.AUTHOR,
            f"Approved + CI passing — @{pr.author} to merge",
            Severity.NONE,
        )

    # 7. HEALTHY — active, no blockers, normal flow.
    return result(
        StuckType.HEALTHY, ActorType.NONE,
        "Active, no blockers",
        Severity.NONE,
    )


# ── Sorting and filtering ─────────────────────────────────────────────────────


def sort_by_staleness(items: list[PRClassification]) -> list[PRClassification]:
    """Oldest last-activity first — the most stagnant PRs appear at top."""
    return sorted(items, key=lambda c: c.staleness_days, reverse=True)


def filter_needs_action(items: list[PRClassification]) -> list[PRClassification]:
    """PRs that require a human decision right now."""
    actionable = {
        StuckType.ABANDONED,
        StuckType.BLOCKED_ON_CONFLICT,
        StuckType.BLOCKED_ON_CI,
        StuckType.BLOCKED_ON_AUTHOR,
        StuckType.BLOCKED_ON_REVIEWER,
        StuckType.READY_TO_MERGE,
    }
    return [c for c in items if c.stuck_type in actionable]
