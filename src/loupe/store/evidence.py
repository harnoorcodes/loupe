"""The shared substrate: claims, findings, and run state.

Every agent reads and writes here rather than passing prose to each other.
This is what makes cross-document reasoning possible -- the tension detector
can see claims from documents it never read.

Persistence is JSON on disk. A database would be better at scale; JSON is
inspectable, diffable, and requires no service to run, which matters more
for a system whose outputs must be auditable.

The finding ledger is append-only (threat model T-5). Corrections are new
versioned entries; nothing is edited in place.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from loupe.models.claim import Claim
from loupe.models.document import Document
from loupe.models.finding import Finding, FindingStatus
from loupe.observability.logging import get_logger
from loupe.store.entities import normalise_entity

log = get_logger(__name__)


class EvidenceStore:
    """In-memory substrate with JSON persistence.

    Attributes:
        root: Directory holding the persisted state.
    """

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self._documents: dict[str, Document] = {}
        self._claims: dict[str, Claim] = {}
        self._findings: list[Finding] = []
        self._claims_by_doc: dict[str, list[str]] = defaultdict(list)
        self._processed_docs: set[str] = set()

    # --- documents --------------------------------------------------------

    def add_document(self, document: Document) -> None:
        """Register a document. Idempotent."""
        self._documents[document.document_id] = document

    def get_document(self, document_id: str) -> Document | None:
        return self._documents.get(document_id)

    @property
    def documents(self) -> tuple[Document, ...]:
        return tuple(self._documents.values())

    def source_text(self, document_id: str) -> str:
        """Full extracted text, for span validation."""
        doc = self._documents.get(document_id)
        return doc.text if doc else ""

    # --- claims -----------------------------------------------------------

    def add_claim(self, claim: Claim) -> None:
        """Add a claim. Later writes to the same ID overwrite earlier ones."""
        if claim.claim_id not in self._claims:
            self._claims_by_doc[claim.document_id].append(claim.claim_id)
        self._claims[claim.claim_id] = claim

    def add_claims(self, claims: list[Claim]) -> None:
        for claim in claims:
            self.add_claim(claim)

    @property
    def claims(self) -> tuple[Claim, ...]:
        return tuple(self._claims.values())

    def claims_for_document(self, document_id: str) -> tuple[Claim, ...]:
        ids = self._claims_by_doc.get(document_id, [])
        return tuple(self._claims[i] for i in ids if i in self._claims)

    def claims_about(self, subject: str) -> tuple[Claim, ...]:
        """All claims about one entity, across every document.

        Matching is on the normalised entity key, so "TitanRetail Group"
        and "TitanRetail Group Limited" return the same set. This is the
        retrieval primitive the tension detector runs on, and unmerged
        variants here mean missed cross-document contradictions.
        """
        key = normalise_entity(subject)
        return tuple(
            c for c in self._claims.values() if normalise_entity(c.subject) == key
        )

    def subjects(self) -> tuple[str, ...]:
        """Distinct normalised entity keys, most-claimed first."""
        counts: dict[str, int] = defaultdict(int)
        for claim in self._claims.values():
            counts[normalise_entity(claim.subject)] += 1
        return tuple(sorted(counts, key=lambda s: -counts[s]))

    # --- findings ---------------------------------------------------------

    def add_finding(self, finding: Finding) -> None:
        """Append a finding. Never overwrites -- the ledger is append-only."""
        self._findings.append(finding)

    def replace_finding(self, finding: Finding) -> None:
        """Record a lifecycle transition as a new ledger entry.

        The prior version stays in the ledger. current_findings() returns
        only the latest entry per finding_id, so history is retained without
        polluting output.
        """
        self._findings.append(finding)

    @property
    def all_findings(self) -> tuple[Finding, ...]:
        """Every ledger entry including superseded versions."""
        return tuple(self._findings)

    def current_findings(self) -> tuple[Finding, ...]:
        """Latest version of each finding."""
        latest: dict[str, Finding] = {}
        for finding in self._findings:
            latest[finding.finding_id] = finding
        return tuple(latest.values())

    def confirmed_findings(self) -> tuple[Finding, ...]:
        """Findings that survived adversarial review, worst first.

        Only these reach the memo.
        """
        confirmed = [
            f
            for f in self.current_findings()
            if f.status is FindingStatus.CONFIRMED
        ]
        return tuple(sorted(confirmed, key=lambda f: -f.severity_rank))

    # --- checkpointing ----------------------------------------------------

    def mark_processed(self, document_id: str) -> None:
        """Record that extraction finished for a document."""
        self._processed_docs.add(document_id)

    def is_processed(self, document_id: str) -> bool:
        """True if extraction already completed, so a resume can skip it."""
        return document_id in self._processed_docs

    def save(self) -> None:
        """Persist claims, findings, and progress to disk."""
        self._write("claims.json", [c.model_dump(mode="json") for c in self.claims])
        self._write(
            "findings.json", [f.model_dump(mode="json") for f in self._findings]
        )
        self._write("progress.json", sorted(self._processed_docs))
        log.info(
            "store saved",
            claims=len(self._claims),
            findings=len(self._findings),
            processed=len(self._processed_docs),
        )

    def load(self) -> None:
        """Restore persisted state. Missing files are treated as empty."""
        for raw in self._read("claims.json"):
            self.add_claim(Claim.model_validate(raw))
        for raw in self._read("findings.json"):
            self._findings.append(Finding.model_validate(raw))
        self._processed_docs = set(self._read("progress.json"))
        log.info(
            "store loaded",
            claims=len(self._claims),
            findings=len(self._findings),
            processed=len(self._processed_docs),
        )

    def _write(self, name: str, payload: Any) -> None:
        (self.root / name).write_text(
            json.dumps(payload, indent=2, default=str), encoding="utf-8"
        )

    def _read(self, name: str) -> list[Any]:
        path = self.root / name
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            log.warning("corrupt state file ignored", file=name, error=str(exc))
            return []

    def stats(self) -> dict[str, int]:
        return {
            "documents": len(self._documents),
            "claims": len(self._claims),
            "findings": len(self.current_findings()),
            "confirmed": len(self.confirmed_findings()),
            "processed": len(self._processed_docs),
        }