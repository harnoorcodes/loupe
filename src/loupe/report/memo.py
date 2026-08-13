"""Write confirmed findings into an investment committee memo.

The memo is a RENDERING of the finding ledger, never a separate act of
writing. It cannot introduce a claim that is not already in the ledger, and
every statement carries the citation the finding carried. That is what makes
the document checkable: a reader can follow any line back to a page.

Generation is deterministic. No model is called, so the memo cannot
hallucinate, cannot vary between runs, and costs nothing.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from loupe.models.finding import Finding, FindingType, Severity
from loupe.observability.logging import get_logger
from loupe.store.evidence import EvidenceStore

log = get_logger(__name__)

_SEVERITY_LABEL = {
    Severity.CRITICAL: "Critical",
    Severity.HIGH: "High",
    Severity.MEDIUM: "Medium",
    Severity.LOW: "Low",
}


def _summary_line(findings: tuple[Finding, ...]) -> str:
    """One sentence stating what was found, for the top of the memo."""
    if not findings:
        return "No confirmed findings. The data room raised no material issues."

    counts: dict[Severity, int] = {}
    for finding in findings:
        counts[finding.severity] = counts.get(finding.severity, 0) + 1

    parts = [
        f"{counts[sev]} {_SEVERITY_LABEL[sev].lower()}"
        for sev in (Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW)
        if sev in counts
    ]
    cross = sum(1 for f in findings if f.is_cross_document)
    tail = (
        f" {cross} of these required evidence from more than one document."
        if cross
        else ""
    )
    return f"{len(findings)} confirmed findings: {', '.join(parts)}.{tail}"


def _render_finding(finding: Finding, number: int) -> list[str]:
    """Render one finding as markdown."""
    scope = "cross-document" if finding.is_cross_document else "single document"
    lines = [
        f"### {number}. {finding.title}",
        "",
        f"**Severity:** {_SEVERITY_LABEL[finding.severity]}  ",
        f"**Type:** {finding.finding_type.value.replace('_', ' ')}  ",
        f"**Scope:** {scope}  ",
        f"**Raised by:** {finding.raised_by}",
        "",
        finding.description,
        "",
    ]

    if finding.all_spans:
        lines.append("**Evidence**")
        lines.append("")
        for span in finding.all_spans:
            quote = span.text.replace("\n", " ").strip()
            lines.append(f"- `{span.citation()}` — \"{quote[:300]}\"")
        lines.append("")
    else:
        lines.extend(
            [
                "**Evidence**",
                "",
                "- None. This finding concerns a document that is absent from "
                "the data room.",
                "",
            ]
        )

    if finding.challenge_reason:
        lines.extend(
            [
                "**Adversarial review**",
                "",
                f"The reviewing agent argued: _{finding.challenge_reason}_",
                "",
                "The finding was reported notwithstanding that objection.",
                "",
            ]
        )

    return lines


def build(store: EvidenceStore, deal_name: str = "Northwind Analytics Inc.") -> str:
    """Assemble the memo from confirmed findings.

    Args:
        store: The evidence store for the run.
        deal_name: Target company name, for the header.

    Returns:
        The memo as markdown.
    """
    confirmed = store.confirmed_findings()
    retracted = [
        f
        for f in store.current_findings()
        if f.status.value == "retracted"
    ]
    stats = store.stats()
    generated = datetime.now(UTC).strftime("%d %B %Y")

    lines = [
        f"# Due Diligence Findings — {deal_name}",
        "",
        f"Generated {generated} by Loupe.",
        "",
        "---",
        "",
        "## Summary",
        "",
        _summary_line(confirmed),
        "",
        f"Reviewed {stats['documents']} documents and extracted "
        f"{stats['claims']} claims. Every finding below was challenged by an "
        f"adversarial reviewing agent before being reported, and every "
        f"citation was verified against its source document.",
        "",
        "---",
        "",
        "## Findings",
        "",
    ]

    if confirmed:
        for index, finding in enumerate(confirmed, start=1):
            lines.extend(_render_finding(finding, index))
    else:
        lines.extend(["No confirmed findings.", ""])

    gaps = [
        f for f in confirmed if f.finding_type is FindingType.MISSING_DOCUMENT
    ]
    if gaps:
        lines.extend(
            [
                "---",
                "",
                "## Documents to request from the seller",
                "",
                "The following were expected but not provided.",
                "",
            ]
        )
        for finding in gaps:
            lines.append(f"- {finding.title.removeprefix('Missing: ')}")
        lines.append("")

    if retracted:
        lines.extend(
            [
                "---",
                "",
                "## Findings considered and withdrawn",
                "",
                "These were proposed by a detector and then withdrawn during "
                "adversarial review. They are listed so the reader can see "
                "what was considered, not only what was reported.",
                "",
            ]
        )
        for finding in retracted:
            lines.append(f"**{finding.title}**")
            lines.append("")
            lines.append(f"Withdrawn because: {finding.challenge_reason}")
            lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## Method and limitations",
            "",
            "Claims were extracted from every document with a page and "
            "character reference. Contradictions were detected by comparing "
            "claims about the same entity drawn from different documents. "
            "Absent documents were identified by comparing the corpus against "
            "a standard diligence request list.",
            "",
            "This report identifies issues for human review. It does not "
            "provide legal advice, does not value the business, and does not "
            "recommend whether to proceed.",
            "",
        ]
    )

    return "\n".join(lines)


def write(
    store: EvidenceStore,
    path: Path,
    deal_name: str = "Northwind Analytics Inc.",
) -> Path:
    """Write the memo to disk and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build(store, deal_name), encoding="utf-8")
    log.info("memo written", path=str(path))
    return path