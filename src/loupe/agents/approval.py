"""Human approval gate.

FR-18: critical-severity findings require explicit human sign-off before
entering the memo.

The gate is deliberately placed AFTER adversarial review, not before. A human
asked to approve twenty unreviewed findings will rubber-stamp them; a human
asked to approve three findings that already survived a hostile critic is
making a real decision with their attention where it matters.

Threat model T-6 (automation complacency): the prompt shows the critic's
objection alongside the finding, so the reviewer sees what was argued against
it rather than only the conclusion.
"""

from __future__ import annotations

from loupe.models.finding import Finding, FindingStatus, Severity
from loupe.observability.logging import get_logger

log = get_logger(__name__)

APPROVER_NAME = "human_reviewer"
GATED_SEVERITIES = (Severity.CRITICAL,)


def requires_approval(finding: Finding) -> bool:
    """True if this finding cannot enter the memo without a human decision."""
    return (
        finding.status is FindingStatus.CONFIRMED
        and finding.severity in GATED_SEVERITIES
    )


def render_for_approval(finding: Finding) -> str:
    """Format a finding for a human decision."""
    lines = [
        "",
        "=" * 70,
        f"APPROVAL REQUIRED  [{finding.severity.value.upper()}]",
        "=" * 70,
        f"{finding.title}",
        "",
        finding.description,
        "",
        "EVIDENCE:",
    ]
    for span in finding.all_spans:
        lines.append(f'  [{span.citation()}] "{span.text[:300]}"')

    if finding.challenge_reason:
        lines.extend(
            [
                "",
                "THE CRITIC ARGUED AGAINST THIS FINDING:",
                f"  {finding.challenge_reason}",
                "",
                "It survived that objection.",
            ]
        )

    lines.extend(["", "=" * 70])
    return "\n".join(lines)


def apply_decision(finding: Finding, approved: bool, note: str = "") -> Finding:
    """Record a human decision on a gated finding.

    Args:
        finding: A confirmed finding awaiting approval.
        approved: The reviewer's decision.
        note: Optional reason, recorded in the ledger.

    Returns:
        The finding with the decision recorded.
    """
    if approved:
        log.info("finding approved by human", finding_id=finding.finding_id)
        return finding.model_copy(
            update={"reviewed_by": (*finding.reviewed_by, APPROVER_NAME)}
        )

    log.info(
        "finding rejected by human",
        finding_id=finding.finding_id,
        note=note[:120],
    )
    return finding.retract(
        note or "Rejected by human reviewer as immaterial.", by=APPROVER_NAME
    )


def gate(findings: list[Finding], interactive: bool = True) -> list[Finding]:
    """Run the approval gate over reviewed findings.

    Args:
        findings: Findings that have completed adversarial review.
        interactive: If False, gated findings are left confirmed but
            unapproved, for non-interactive runs such as the eval harness.

    Returns:
        Findings with human decisions applied.
    """
    gated = [f for f in findings if requires_approval(f)]
    if not gated:
        return findings

    if not interactive:
        log.info("approval gate skipped (non-interactive)", pending=len(gated))
        return findings

    print(f"\n{len(gated)} finding(s) require your approval before reporting.")

    decisions: dict[str, Finding] = {}
    for finding in gated:
        print(render_for_approval(finding))
        answer = input("Include this finding in the memo? [y/n]: ").strip().lower()
        if answer.startswith("y"):
            decisions[finding.finding_id] = apply_decision(finding, True)
        else:
            note = input("Reason for exclusion (optional): ").strip()
            decisions[finding.finding_id] = apply_decision(finding, False, note)

    return [decisions.get(f.finding_id, f) for f in findings]