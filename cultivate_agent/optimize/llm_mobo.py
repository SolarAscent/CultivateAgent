"""Evidence-grounded, LLM-warm-started multi-objective Bayesian optimization.

This is CultivateAgent's core algorithmic contribution — a synthesis of three
lines of recent work, adapted to cultivated-meat medium design:

* multi-objective BO with hypervolume acquisition (Daulton et al., NeurIPS 2020;
  qNEHVI),
* LLMs as optimizers / proposers (OPRO, Yang et al. 2023; LLMs-as-evolutionary-
  optimizers, Liu et al. 2023; LLAMBO, Daxberger et al. 2024),
* literature-grounded priors from a knowledge base (this project).

**The loop.** The knowledge base defines the search space and which components
matter (a literature prior a cold-start optimizer lacks). The LLM design agent
proposes *evidence-cited* candidate formulations, giving the optimizer good
regions to consider. The BO surrogate + acquisition then score those candidates
against principled exploration and return a small, **pre-registerable** batch of
experiments on the cost/performance Pareto front. Measured results are told back
to the optimizer, closing the loop.

Why this is defensible (per the record's critique): the batch is committed
before running (pre-registration); cost is always one of the objectives, so it
is reported as a Pareto trade-off, never an isolated win; and every LLM-seeded
candidate keeps its evidence citations for traceability.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .mobo import MultiObjectiveBO, Suggestion
from .space import MediumDesignSpace

_NUM_RE = re.compile(r"[-+]?\d*\.?\d+")
_REMOVAL = ("remove", "without", "eliminate", "-free", "reduce", "lower", "decrease", "drop")


@dataclass
class BatchItem:
    formulation: Dict[str, object]
    source: str                       # "llm" | "bo" | "space-filling"
    acq_score: Optional[float] = None
    rationale: str = ""
    cited_paper_ids: List[str] = field(default_factory=list)


@dataclass
class OptimizationProposal:
    batch: List[BatchItem]
    pareto_front: List[dict] = field(default_factory=list)
    hypervolume: float = 0.0
    n_observed: int = 0
    llm_caveats: List[str] = field(default_factory=list)
    evidence: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "batch": [
                {"formulation": b.formulation, "source": b.source,
                 "acq_score": b.acq_score, "rationale": b.rationale,
                 "cited_paper_ids": b.cited_paper_ids}
                for b in self.batch
            ],
            "pareto_front": self.pareto_front,
            "hypervolume": self.hypervolume,
            "n_observed": self.n_observed,
            "llm_caveats": self.llm_caveats,
            "evidence": self.evidence,
        }


def _extract_number(text: str) -> Optional[float]:
    m = _NUM_RE.search(text or "")
    return float(m.group()) if m else None


class EvidenceGuidedMOBO:
    def __init__(self, mobo: MultiObjectiveBO, recommender=None, *, normalizer=None):
        self.mobo = mobo
        self.recommender = recommender
        self.normalizer = normalizer
        self.space = mobo.space

    # ------------------------------------------------------------------ #
    # Map an LLM candidate (qualitative changes) -> a concrete formulation
    # ------------------------------------------------------------------ #
    def _candidate_to_formulation(self, candidate) -> Dict[str, object]:
        f: Dict[str, object] = {}
        for ch in getattr(candidate, "changes", []) or []:
            if not getattr(ch, "is_actionable", True):
                continue
            text = f"{ch.variable} {ch.change}"
            is_removal = any(k in ch.change.lower() for k in _REMOVAL)

            # serum knob (FBS has no digits, so no name-stripping needed)
            if ch.variable == "serum_level" or "fbs" in text.lower() or "serum" in text.lower():
                p = self._param("FBS")
                if p:
                    num = _extract_number(re.sub(r"(?i)fbs|serum", " ", ch.change))
                    f[p.name] = num if num is not None else (0.0 if is_removal else 5.0)
                continue

            # basal medium
            if ch.variable == "basal_medium":
                p = self._param("basal_medium")
                if p:
                    for choice in p.choices:
                        if choice.lower() in ch.change.lower():
                            f[p.name] = choice
                continue

            # component-level: match any space parameter named/aliased in the text.
            # Strip the parameter name before reading the number so component names
            # that contain digits (FGF2, Y-27632) don't corrupt the value.
            for p in self.space.parameters:
                if p.name in ("basal_medium", "FBS"):
                    continue
                if self._mentions(p.name, ch.change):
                    num = _extract_number(re.sub(re.escape(p.name), " ", ch.change, flags=re.I))
                    if p.kind == "continuous":
                        f[p.name] = num if num is not None else (0.0 if is_removal else (p.low + p.high) * 0.25)
                    elif p.kind == "binary":
                        f[p.name] = not is_removal
        return f

    def _param(self, name: str):
        for p in self.space.parameters:
            if p.name == name:
                return p
        return None

    def _mentions(self, param_name: str, text: str) -> bool:
        t = text.lower()
        if param_name.lower() in t:
            return True
        if self.normalizer is not None:
            # canonicalize each token span and compare
            canon = self.normalizer.canonicalize(text).canonical
            if canon and canon.lower() == param_name.lower():
                return True
        return False

    # ------------------------------------------------------------------ #
    # Propose the next batch                                             #
    # ------------------------------------------------------------------ #
    def propose(
        self,
        weights,
        context,
        *,
        batch_size: int = 4,
        n_llm_candidates: int = 4,
        observed_formulations: Optional[List[Dict[str, object]]] = None,
        observed_values: Optional[List[Dict[str, float]]] = None,
    ) -> OptimizationProposal:
        # 1) fold in any measured results
        if observed_formulations and observed_values:
            self.mobo.tell(observed_formulations, observed_values)

        # 2) LLM proposes evidence-cited candidate formulations
        llm_forms: List[Dict[str, object]] = []
        llm_meta: List[dict] = []
        caveats: List[str] = []
        evidence: List[dict] = []
        if self.recommender is not None:
            rec = self.recommender.recommend(weights, context, n_candidates=n_llm_candidates)
            caveats = list(rec.caveats)
            evidence = [{"index": e.index, "paper_id": e.paper_id, "title": e.title} for e in rec.evidence]
            for cand in rec.candidates:
                form = self._candidate_to_formulation(cand)
                if form:
                    llm_forms.append(form)
                    cites = sorted({pid for ch in cand.changes for pid in ch.cited_paper_ids} | set(cand.cited_paper_ids))
                    llm_meta.append({"name": cand.name, "rationale": cand.summary, "cited_paper_ids": cites})

        pref = weights.normalized if hasattr(weights, "normalized") else dict(weights)

        # 3) BO scores LLM candidates alongside principled exploration
        suggestions: List[Suggestion] = self.mobo.ask(
            batch_size, preference_weights=pref, extra_candidates=llm_forms or None,
        )

        # 4) annotate LLM-derived items with their citations/rationale
        batch: List[BatchItem] = []
        for s in suggestions:
            item = BatchItem(formulation=s.formulation, source=s.source,
                             acq_score=s.acq_score, rationale=s.note)
            if s.source == "llm":
                meta = _closest_meta(s.formulation, llm_forms, llm_meta)
                if meta:
                    item.rationale = meta.get("rationale", item.rationale)
                    item.cited_paper_ids = meta.get("cited_paper_ids", [])
            batch.append(item)

        pf = [{"formulation": f, "objectives": v} for f, v in self.mobo.pareto()]
        return OptimizationProposal(
            batch=batch, pareto_front=pf, hypervolume=self.mobo.hypervolume(),
            n_observed=self.mobo.n_observed, llm_caveats=caveats, evidence=evidence,
        )


def _closest_meta(formulation, llm_forms, llm_meta):
    """Match a returned formulation back to the LLM candidate it came from."""
    for form, meta in zip(llm_forms, llm_meta):
        if all(formulation.get(k) == v for k, v in form.items()):
            return meta
    return llm_meta[0] if llm_meta else None
