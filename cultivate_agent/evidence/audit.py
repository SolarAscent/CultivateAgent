"""Deterministic wet-lab entry audit for extracted evidence items.

This module does not call an LLM. It inspects already-extracted
``EvidenceItem`` records and asks a narrower question than evidence synthesis:
which claims are close enough to the locked bovine expansion-medium target to be
worth human review, and which gates still block wet-lab entry?
"""

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

from .meta_analysis import EvidenceItem

_TARGET_SPECIES = ("bovine", "cattle", "cow", "hanwoo")
_TARGET_CELLS = ("satellite", "myoblast", "muscle stem", "musc", "myosatellite")
_TARGET_STAGES = ("expansion", "proliferation", "growth", "passage")
_DOSE_RE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:ng/ml|ug/ml|µg/ml|μg/ml|mg/ml|g/l|mm|um|µm|μm|nm|%|x)\b",
    re.IGNORECASE,
)
_NON_MEDIUM_RE = re.compile(
    r"\b("
    r"scaffold|microcarrier|microcarriers|bead|beads|hydrogel|matrix|matrigel|"
    r"collagen|alginate|pdms|plasma|magnetic|temperature|oxygen|hypoxia|"
    r"bioreactor|perfusion|stretch|shockwave|transplant|crispr|engineer(?:ed|ing)?|"
    r"autocrine|immortaliz"
    r")\b",
    re.IGNORECASE,
)


@dataclass
class ComponentAudit:
    component: str
    outcome: str
    item_count: int
    paper_count: int
    direct_target_items: int
    medium_actionable_items: int
    dose_supported_items: int
    quantitative_items: int
    grounded_items: int
    ready_items: int
    paper_ids: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)

    @property
    def ai_review_candidate(self) -> bool:
        return (
            self.ready_items > 0
            and self.grounded_items == self.item_count
        )


@dataclass
class EvidenceAudit:
    outcome: str
    total_items: int
    total_papers: int
    component_count: int
    ai_review_candidates: List[ComponentAudit]
    components: List[ComponentAudit]
    human_open_critical: int = 0
    human_total_critical: int = 0
    min_candidates: int = 3
    decision: str = "NO-GO"
    blockers: List[str] = field(default_factory=list)


def load_effect_items_json(path: str | Path) -> List[EvidenceItem]:
    """Load a JSON list produced from ``EvidenceItem.__dict__`` records."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("effect-item JSON must contain a list")
    items: List[EvidenceItem] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        items.append(EvidenceItem(
            component=str(row.get("component", "")).strip(),
            outcome=str(row.get("outcome", "")).strip(),
            paper_id=str(row.get("paper_id", "")).strip(),
            effect=_to_float(row.get("effect")),
            variance=_to_float(row.get("variance")),
            direction=_to_int(row.get("direction")),
            context={str(k): str(v) for k, v in (row.get("context") or {}).items() if v},
            quote=str(row.get("quote", "")).strip(),
        ))
    return [it for it in items if it.component and it.paper_id]


def audit_effect_items(
    items: Iterable[EvidenceItem],
    *,
    outcome: str = "proliferation",
    human_review_path: str | Path | None = None,
    min_candidates: int = 3,
) -> EvidenceAudit:
    selected = [it for it in items if not outcome or it.outcome == outcome]
    grouped: dict[tuple[str, str], list[EvidenceItem]] = {}
    for it in selected:
        grouped.setdefault((_norm_component_key(it.component), it.outcome), []).append(it)

    components = [_audit_component(group) for group in grouped.values()]
    components.sort(key=lambda c: (
        not c.ai_review_candidate,
        -c.paper_count,
        -c.direct_target_items,
        c.component.lower(),
    ))
    candidates = [c for c in components if c.ai_review_candidate]
    human_open, human_total = _human_critical_open(human_review_path)

    blockers: List[str] = []
    if len(candidates) < min_candidates:
        blockers.append(
            f"Only {len(candidates)} AI-review candidate(s); require at least {min_candidates} "
            "with direct bovine target evidence, medium-only actionability, dose support, and grounded quotes."
        )
    if human_total == 0:
        blockers.append("No critical human-review queue was supplied or detected.")
    elif human_open > 0:
        blockers.append(f"{human_open}/{human_total} critical human-review tasks remain open.")
    weak_quant = sum(1 for c in candidates if c.quantitative_items == 0)
    if candidates and weak_quant == len(candidates):
        blockers.append("All AI-review candidates are direction-only; no candidate has quantitative effect evidence.")

    return EvidenceAudit(
        outcome=outcome,
        total_items=len(selected),
        total_papers=len({it.paper_id for it in selected}),
        component_count=len(components),
        ai_review_candidates=candidates,
        components=components,
        human_open_critical=human_open,
        human_total_critical=human_total,
        min_candidates=min_candidates,
        decision="GO" if not blockers else "NO-GO",
        blockers=blockers,
    )


def write_evidence_audit_markdown(audit: EvidenceAudit, path: str | Path) -> Path:
    """Write a compact Markdown report suitable for project handoff/review."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Evidence Audit: {audit.outcome}",
        "",
        "Status: generated from extracted evidence items; requires human review before wet-lab use.",
        "",
        "## Decision",
        "",
        f"**Wet-lab entry gate: {audit.decision}.**",
        "",
        "| Metric | Value |",
        "|---|---:|",
        f"| Evidence items audited | {audit.total_items} |",
        f"| Source papers represented | {audit.total_papers} |",
        f"| Components/interventions represented | {audit.component_count} |",
        f"| AI-review candidates | {len(audit.ai_review_candidates)} |",
        f"| Critical human-review tasks open | {audit.human_open_critical}/{audit.human_total_critical} |",
        "",
    ]
    if audit.blockers:
        lines += ["## Blocking Reasons", ""]
        lines += [f"- {b}" for b in audit.blockers]
        lines.append("")

    lines += [
        "## Criteria",
        "",
        "A component is only an **AI-review candidate** when all of these are true:",
        "",
        "- at least one item matches the locked bovine satellite-cell/myoblast expansion target;",
        "- at least one item is medium-actionable rather than scaffold, microcarrier, process, or genetic-engineering coupled;",
        "- at least one item contains a dose or concentration cue in the component text or quote;",
        "- all items have grounded quotes in the extracted record.",
        "",
        "This audit is intentionally stricter than evidence synthesis. It is a go/no-go guardrail, "
        "not a ranking of biological promise.",
        "",
        "## AI-Review Candidates",
        "",
        "| Component | Papers | Ready items | Direct target items | Dose-supported items | Quantitative items | Flags |",
        "|---|---:|---:|---:|---:|---:|---|",
    ]
    if audit.ai_review_candidates:
        for c in audit.ai_review_candidates:
            lines.append(
                f"| {c.component} | {c.paper_count} | {c.ready_items} | "
                f"{c.direct_target_items} | {c.dose_supported_items} | {c.quantitative_items} | {_join_flags(c.flags)} |"
            )
    else:
        lines.append("| None | 0 | 0 | 0 | 0 | 0 | no_candidate_passed_gate |")

    lines += [
        "",
        "## Top Rejected Or Weak Items",
        "",
        "| Component | Papers | Direct target items | Medium-actionable items | Dose-supported items | Flags |",
        "|---|---:|---:|---:|---:|---|",
    ]
    weak = [c for c in audit.components if not c.ai_review_candidate][:20]
    for c in weak:
        lines.append(
            f"| {c.component} | {c.paper_count} | {c.direct_target_items} | "
            f"{c.medium_actionable_items} | {c.dose_supported_items} | {_join_flags(c.flags)} |"
        )
    if not weak:
        lines.append("| None | 0 | 0 | 0 | 0 | none |")

    lines += [
        "",
        "## Next Actions",
        "",
        "1. Complete the open critical human-review tasks before any wet-lab design packet.",
        "2. For each AI-review candidate, extract exact formulation, dose, endpoint, passage, and quote into the adjudicated evidence table.",
        "3. Keep rejected process/scaffold/genetic-engineering items out of the first medium-only search space unless a scope-change decision record is created.",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def _audit_component(items: list[EvidenceItem]) -> ComponentAudit:
    first = items[0]
    direct = sum(1 for it in items if _is_direct_target(it))
    medium = sum(1 for it in items if _is_medium_actionable(it.component))
    dose = sum(1 for it in items if _has_dose(it))
    quant = sum(1 for it in items if it.effect is not None or it.variance is not None)
    grounded = sum(1 for it in items if bool(it.quote))
    ready = sum(1 for it in items if _is_direct_target(it) and _is_medium_actionable(it.component)
                and _has_dose(it) and bool(it.quote))
    flags: List[str] = []
    if direct == 0:
        flags.append("indirect_species_or_cell")
    if medium == 0:
        flags.append("not_medium_only")
    if dose == 0:
        flags.append("no_dose_cue")
    if quant == 0:
        flags.append("direction_only")
    if grounded < len(items):
        flags.append("missing_quote")
    return ComponentAudit(
        component=first.component,
        outcome=first.outcome,
        item_count=len(items),
        paper_count=len({it.paper_id for it in items}),
        direct_target_items=direct,
        medium_actionable_items=medium,
        dose_supported_items=dose,
        quantitative_items=quant,
        grounded_items=grounded,
        ready_items=ready,
        paper_ids=sorted({it.paper_id for it in items}),
        flags=flags or ["candidate_for_human_review"],
    )


def _human_critical_open(path: str | Path | None) -> tuple[int, int]:
    if not path or not Path(path).exists():
        return 0, 0
    critical_total = 0
    critical_open = 0
    with Path(path).open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            rid = row.get("review_id", "")
            try:
                n = int(rid.lstrip("H"))
            except ValueError:
                continue
            if row.get("priority") == "P1" and n <= 16:
                critical_total += 1
                if row.get("status", "").strip().lower() in {"", "open", "todo", "pending"}:
                    critical_open += 1
    return critical_open, critical_total


def _is_direct_target(item: EvidenceItem) -> bool:
    text = " ".join([item.context.get("species", ""), item.context.get("cell_type", ""), item.context.get("stage", "")]).lower()
    species_ok = any(s in text for s in _TARGET_SPECIES)
    cell_ok = any(c in text for c in _TARGET_CELLS)
    stage = item.context.get("stage", "").lower()
    stage_ok = not stage or any(s in stage for s in _TARGET_STAGES)
    return species_ok and cell_ok and stage_ok


def _is_medium_actionable(component: str) -> bool:
    return not _NON_MEDIUM_RE.search(component or "")


def _has_dose(item: EvidenceItem) -> bool:
    text = f"{item.component} {item.quote}"
    return bool(_DOSE_RE.search(text))


def _norm_component_key(component: str) -> str:
    return re.sub(r"\s+", " ", component.strip().lower())


def _join_flags(flags: list[str]) -> str:
    return ", ".join(flags) if flags else "none"


def _to_float(x) -> Optional[float]:
    try:
        return float(x) if x is not None else None
    except (TypeError, ValueError):
        return None


def _to_int(x) -> Optional[int]:
    try:
        return int(x) if x is not None else None
    except (TypeError, ValueError):
        return None
