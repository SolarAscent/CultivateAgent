"""Goal-conditioned, evidence-grounded medium recommender.

Given user objectives (+weights) and a read-only context, the recommender:

1. builds a retrieval query and pulls supporting papers from the knowledge base,
2. assembles a *numbered evidence pack* (each item ties back to a paper_id),
3. asks the LLM for candidate medium formulations that (a) only touch actionable
   variables, (b) cite evidence items, and (c) report cost jointly with
   performance (a Pareto view, never "cost win" in isolation),
4. validates the output and flags any change to a non-actionable variable.

The guardrails in the system prompt are lifted directly from the project
record's critique: cite everything, don't overclaim, mark novel combinations as
untested, keep the design medium-centered.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from ..llm.base import LLMClient, LLMError, extract_json
from ..retrieve.retriever import Hit, Retriever
from .objectives import (
    DEFAULT_ACTIONABLE_VARIABLES,
    OBJECTIVE_METRICS,
    DesignContext,
    ObjectiveWeights,
)


# --------------------------------------------------------------------------- #
# Structured output                                                           #
# --------------------------------------------------------------------------- #
class VariableChange(BaseModel):
    variable: str
    change: str = Field(..., description="Proposed value/direction, e.g. 'reduce FBS 10% -> 2%', 'add FGF2'.")
    rationale: str = ""
    cited_paper_ids: List[str] = Field(default_factory=list)
    is_actionable: bool = True   # set False by the validator if out of whitelist


class MediumCandidate(BaseModel):
    name: str
    summary: str = ""
    changes: List[VariableChange] = Field(default_factory=list)
    expected_effects: Dict[str, str] = Field(default_factory=dict)  # objective -> expected effect
    cost_vs_performance: str = Field("", description="Joint (Pareto) statement, not an isolated cost claim.")
    feasibility_notes: str = ""
    risks_and_unknowns: str = ""
    doe_suggestion: str = ""
    cited_paper_ids: List[str] = Field(default_factory=list)


class EvidenceItem(BaseModel):
    index: int
    paper_id: str
    title: str
    snippet: str


class Recommendation(BaseModel):
    objectives: Dict[str, float]
    context: str
    candidates: List[MediumCandidate] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    caveats: List[str] = Field(default_factory=list)
    model: Optional[str] = None


# --------------------------------------------------------------------------- #
# Prompts                                                                     #
# --------------------------------------------------------------------------- #
_SYSTEM = """
You are a cultivated-meat culture-medium design assistant. You propose
medium-formulation changes grounded in the provided evidence pack. Hard rules:

- MEDIUM-CENTERED: you may only propose changes to the ACTIONABLE VARIABLES
  listed. Scaffold, cell type, perfusion, and 3D structure are CONTEXT you
  condition on, never variables you change.
- CITE EVIDENCE: every proposed change must cite one or more evidence items by
  their paper_id. If the evidence pack does not support a change, say so and
  mark it as an untested hypothesis rather than asserting it.
- NO OVERCLAIMING: combinations of components drawn from different papers are
  NOVEL and UNTESTED even when each part is cited. State this in
  risks_and_unknowns.
- COST IS A TRADE-OFF: never report a cost reduction as a standalone win.
  Always state cost jointly with the performance it may sacrifice
  (a Pareto statement).
- Output STRICT JSON only.
""".strip()


def _build_user_prompt(
    weights: ObjectiveWeights,
    context: DesignContext,
    actionable: List[str],
    evidence: List[EvidenceItem],
    n_candidates: int,
) -> str:
    metrics = {o: OBJECTIVE_METRICS.get(o, []) for o in weights.normalized}
    ev_block = "\n".join(
        f"[{e.index}] paper_id={e.paper_id} | {e.title}\n    {e.snippet}" for e in evidence
    ) or "(no evidence retrieved — you must mark all suggestions as untested hypotheses)"

    schema = """
{
  "candidates": [
    {
      "name": "short label",
      "summary": "one-sentence description",
      "changes": [
        {"variable": "<one of the actionable variables>",
         "change": "concrete change",
         "rationale": "why, tied to evidence",
         "cited_paper_ids": ["<paper_id>", ...]}
      ],
      "expected_effects": {"proliferation": "...", "cost": "...", "differentiation_retention": "...", "tissue_readiness": "..."},
      "cost_vs_performance": "joint Pareto statement",
      "feasibility_notes": "...",
      "risks_and_unknowns": "state novelty/untested combination risks",
      "doe_suggestion": "a minimal design-of-experiments to test this candidate",
      "cited_paper_ids": ["<paper_id>", ...]
    }
  ],
  "caveats": ["..."]
}
""".strip()

    return f"""OBJECTIVES (normalized weights): {weights.describe()}
OBJECTIVE METRICS: {metrics}

CONTEXT (read-only constraints): {context.describe()}

ACTIONABLE VARIABLES (the only things you may change): {actionable}

EVIDENCE PACK:
{ev_block}

Propose {n_candidates} distinct candidate media, ranked by fit to the weighted
objectives. Return STRICT JSON in exactly this shape:

{schema}
"""


# --------------------------------------------------------------------------- #
# Recommender                                                                 #
# --------------------------------------------------------------------------- #
class MediumRecommender:
    def __init__(
        self,
        client: LLMClient,
        retriever: Retriever,
        kb=None,
        *,
        actionable_variables: Optional[List[str]] = None,
        top_k: int = 12,
    ):
        self.client = client
        self.retriever = retriever
        self.kb = kb
        self.actionable = actionable_variables or list(DEFAULT_ACTIONABLE_VARIABLES)
        self.top_k = top_k

    def _query(self, weights: ObjectiveWeights, context: DesignContext) -> str:
        top_obj = sorted(weights.normalized.items(), key=lambda t: -t[1])
        terms = [o for o, _ in top_obj]
        for o, _ in top_obj:
            terms += OBJECTIVE_METRICS.get(o, [])[:2]
        terms += [context.cell_type or "", context.species or "", context.starting_medium or "", "culture medium serum-free"]
        return " ".join(t for t in terms if t)

    def recommend(
        self,
        weights: ObjectiveWeights,
        context: DesignContext,
        *,
        n_candidates: int = 3,
    ) -> Recommendation:
        hits: List[Hit] = self.retriever.search(self._query(weights, context), top_k=self.top_k)
        evidence = [
            EvidenceItem(index=i + 1, paper_id=h.doc_id, title=h.title, snippet=h.snippet)
            for i, h in enumerate(hits)
        ]

        prompt = _build_user_prompt(weights, context, self.actionable, evidence, n_candidates)
        rec = Recommendation(
            objectives=weights.normalized, context=context.describe(),
            evidence=evidence, model=self.client.model,
        )
        try:
            data = self.client.complete_json(_SYSTEM, prompt)
        except LLMError as e:
            rec.caveats.append(f"LLM call failed: {e}")
            return rec

        if isinstance(data, dict):
            for c in data.get("candidates", []) or []:
                try:
                    cand = MediumCandidate.model_validate(c)
                except Exception:  # noqa: BLE001
                    continue
                self._enforce_actionable(cand)
                rec.candidates.append(cand)
            rec.caveats.extend(str(x) for x in (data.get("caveats", []) or []))

        rec.caveats.append(
            "Recommendations are literature-grounded hypotheses, not validated formulations. "
            "Any multi-source combination is untested; confirm in a pre-registered head-to-head "
            "against a strong serum-free baseline before drawing conclusions."
        )
        return rec

    def _enforce_actionable(self, cand: MediumCandidate) -> None:
        allowed = set(self.actionable)
        for ch in cand.changes:
            ch.is_actionable = ch.variable in allowed
            if not ch.is_actionable:
                ch.rationale = (ch.rationale + " [FLAGGED: not an actionable medium variable; ignored]").strip()
