"""Ablation study: measuring what each component contributes.

A system that finds six defects out of fifteen has said nothing about WHY
it finds those six. Removing one component at a time and re-scoring turns
architectural claims into measurements: if disabling the pair detector
halves recall, the pair detector is doing real work; if it changes nothing,
it is decoration.

Most configurations are subsets of the full pipeline, so their model calls
are already in the response cache and cost nothing to re-run. Only the
entity-normalisation ablation produces new prompts, because changing how
claims are grouped changes what each prompt contains.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from typing import NamedTuple

from loupe.agents import critic
from loupe.detect import adjudicate, arithmetic, gaps, pairs, temporal, tension
from loupe.eval.scoring import ScoreCard, score
from loupe.models.finding import Finding, FindingStatus
from loupe.observability.logging import get_logger
from loupe.store import evidence as evidence_module
from loupe.store.evidence import EvidenceStore

log = get_logger(__name__)


@dataclass(frozen=True)
class AblationConfig:
    """One configuration of the detection pipeline.

    Attributes:
        name: Short label for the results table.
        note: What this configuration is testing.
    """

    name: str
    note: str
    use_arithmetic: bool = True
    use_temporal: bool = True
    use_gaps: bool = True
    use_tension: bool = True
    use_pairs: bool = True
    use_critic: bool = True
    use_entity_normalisation: bool = True


CONFIGURATIONS: tuple[AblationConfig, ...] = (
    AblationConfig(
        name="full",
        note="Every component enabled. The baseline.",
    ),
    AblationConfig(
        name="no pair detector",
        note="Targeted pair analysis removed; entity-grouped tension only.",
        use_pairs=False,
    ),
    AblationConfig(
        name="no tension detector",
        note="Entity-grouped analysis removed; targeted pairs only.",
        use_tension=False,
    ),
    AblationConfig(
        name="no entity resolution",
        note="Name variants no longer merged, so claims group by raw subject.",
        use_entity_normalisation=False,
    ),
    AblationConfig(
        name="no adversarial review",
        note="Findings reported without being challenged.",
        use_critic=False,
    ),
    AblationConfig(
        name="deterministic only",
        note="No model calls at all. Arithmetic, dates and gap audit only.",
        use_tension=False,
        use_pairs=False,
        use_critic=False,
    ),
)


class AblationResult(NamedTuple):
    """The outcome of running one configuration."""

    config: AblationConfig
    card: ScoreCard
    proposed: int
    confirmed: int

    @property
    def recall_label(self) -> str:
        return f"{self.card.detected_count}/{self.card.planted_count}"

    @property
    def noise_label(self) -> str:
        return f"{len(self.card.extra_noise)}/{self.card.total_findings}"


def _identity(name: str) -> str:
    """Stand-in for entity normalisation when it is disabled.

    Lowercases only, so "TitanRetail Group" and "TitanRetail Group Limited"
    remain distinct entities, which is the behaviour before normalisation
    was added.
    """
    return name.lower().strip()


class _NormalisationDisabled:
    """Temporarily disable entity normalisation inside the store.

    The evidence store imports normalise_entity into its own namespace, so
    replacing it there changes how claims_about and subjects group claims
    without touching any other caller.
    """

    def __enter__(self) -> None:
        self._original = evidence_module.normalise_entity
        evidence_module.normalise_entity = _identity  # type: ignore[assignment]

    def __exit__(self, *exc: object) -> None:
        evidence_module.normalise_entity = self._original  # type: ignore[assignment]


async def _propose(
    store: EvidenceStore, config: AblationConfig
) -> list[Finding]:
    """Run the enabled detectors and return proposed findings."""
    proposed: list[Finding] = []

    if config.use_arithmetic:
        proposed.extend(arithmetic.detect(store))
    if config.use_temporal:
        proposed.extend(temporal.detect(store))
    if config.use_gaps:
        proposed.extend(gaps.detect(store))
    if config.use_tension:
        proposed.extend(await tension.detect(store))
    if config.use_pairs:
        proposed.extend(await adjudicate.adjudicate(pairs.generate(store)))

    return proposed


def _confirm_without_review(findings: list[Finding]) -> list[Finding]:
    """Move findings to confirmed without a critic.

    Used only by the no-review ablation. The lifecycle still passes through
    challenged, because Finding.confirm rejects an unchallenged finding by
    design -- the ablation removes the reviewer, not the invariant.
    """
    return [
        f.challenge(
            "Adversarial review disabled for this ablation.", by="ablation"
        ).confirm(by="ablation")
        for f in findings
    ]


async def run_one(
    store: EvidenceStore, config: AblationConfig
) -> AblationResult:
    """Run the pipeline under one configuration and score the result."""
    log.info("ablation starting", config=config.name)

    if config.use_entity_normalisation:
        proposed = await _propose(store, config)
    else:
        with _NormalisationDisabled():
            proposed = await _propose(store, config)

    if config.use_critic:
        reviewed = await critic.review_all(proposed, store)
        confirmed = [
            f for f in reviewed if f.status is FindingStatus.CONFIRMED
        ]
    else:
        confirmed = _confirm_without_review(proposed)

    ordered = tuple(sorted(confirmed, key=lambda f: -f.severity_rank))
    card = score(ordered)

    log.info(
        "ablation complete",
        config=config.name,
        proposed=len(proposed),
        confirmed=len(confirmed),
        detected=card.detected_count,
    )
    return AblationResult(config, card, len(proposed), len(confirmed))


async def run_all(
    store: EvidenceStore,
    configurations: tuple[AblationConfig, ...] = CONFIGURATIONS,
) -> list[AblationResult]:
    """Run every configuration in sequence.

    Sequential rather than concurrent, so that later configurations benefit
    from cache entries written by earlier ones.
    """
    results: list[AblationResult] = []
    for config in configurations:
        results.append(await run_one(store, config))
    return results


def render(results: list[AblationResult]) -> str:
    """Format ablation results as a markdown report."""
    if not results:
        return "No ablation results."

    baseline = results[0]

    lines = [
        "# Ablation study",
        "",
        "Each configuration removes one component and re-scores against the",
        "same corpus. The difference from the baseline is what that component",
        "contributes.",
        "",
        "| Configuration | Recall | Noise | Proposed | Confirmed | vs baseline |",
        "| --- | --- | --- | --- | --- | --- |",
    ]

    for result in results:
        delta = result.card.detected_count - baseline.card.detected_count
        if result is baseline:
            change = "baseline"
        elif delta == 0:
            change = "no change"
        else:
            change = f"{delta:+d} defects"

        lines.append(
            f"| {result.config.name} | {result.recall_label} "
            f"({result.card.recall:.0%}) | {result.noise_label} "
            f"({result.card.noise_rate:.0%}) | {result.proposed} | "
            f"{result.confirmed} | {change} |"
        )

    lines.extend(["", "## What each configuration tests", ""])
    for result in results:
        lines.append(f"- **{result.config.name}** — {result.config.note}")

    lines.extend(["", "## Which defects each configuration finds", ""])
    header = "| Defect | " + " | ".join(r.config.name for r in results) + " |"
    lines.append(header)
    lines.append("| --- " * (len(results) + 1) + "|")

    for i, defect_result in enumerate(baseline.card.results):
        row = [defect_result.defect_id]
        for result in results:
            found = result.card.results[i].detected
            row.append("yes" if found else "-")
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    return "\n".join(lines)


def summarise_contributions(results: list[AblationResult]) -> str:
    """One paragraph naming what each removal cost, for a README."""
    if len(results) < 2:
        return ""

    baseline = results[0]
    parts: list[str] = []

    for result in results[1:]:
        delta = baseline.card.detected_count - result.card.detected_count
        if delta > 0:
            parts.append(
                f"removing the {result.config.name.removeprefix('no ')} "
                f"costs {delta} defect{'s' if delta != 1 else ''}"
            )

    if not parts:
        return "No single component accounted for a measurable share of recall."
    return "Against the full system, " + "; ".join(parts) + "."