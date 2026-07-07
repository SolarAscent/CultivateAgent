#!/usr/bin/env python3
"""End-to-end capstone: the full novel pipeline, offline, with a mock LLM.

Composes every Session-2 piece into one runnable narrative:

    operator extraction  ->  evidence synthesis  ->  KB  ->  evidence prior  ->  prior-guided MOBO

No API key, no wet lab. The mock LLM returns text-grounded answers so the run is
deterministic. This proves the pieces compose; real runs swap the mock for a real
provider and the synthetic objective for wet-lab measurements.

Run: python scripts/demo_full_pipeline.py
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cultivate_agent.evidence import extract_effects, synthesize                      # noqa: E402
from cultivate_agent.extract import OperatorExtractor                                 # noqa: E402
from cultivate_agent.kb import KnowledgeBase                                          # noqa: E402
from cultivate_agent.llm import get_client                                           # noqa: E402
from cultivate_agent.normalize import ComponentNormalizer                            # noqa: E402
from cultivate_agent.optimize import (                                               # noqa: E402
    EvidencePrior, MultiObjectiveBO, SyntheticMediumObjective, default_medium_space,
)
from cultivate_agent.schema.paper import PaperRef                                     # noqa: E402

# Two tiny "papers" (title + text). The mock answers are grounded in these texts.
PAPERS = [
    (PaperRef(paper_id="stout2022", title="Serum-free B8/Beefy-9 for bovine satellite cells", year=2022),
     "Abstract\nWe expanded bovine satellite cells in serum-free medium.\n\n"
     "Methods\nBasal medium was DMEM/F12 with FGF2. Recombinant albumin was added (Beefy-9).\n\n"
     "Results\nFGF2 increased proliferation; removing FBS (serum-free) did not reduce growth and cut cost."),
    (PaperRef(paper_id="kolkmann2023", title="Serum-free, grain-free medium for bovine myoblasts", year=2023),
     "Abstract\nA serum-free medium supported bovine myoblast proliferation.\n\n"
     "Methods\nDMEM/F12 base with FGF2 and microalgae extract.\n\n"
     "Results\nFGF2 raised proliferation; high FBS was unnecessary and increased cost."),
]


def _handler(msgs):
    """Route mock answers by operator name / effect-extraction request."""
    u = msgs[-1].content
    if "OUTCOME OF INTEREST" in u:  # effect-extraction operator
        ev = [{"component": "FGF2", "direction": 1, "effect": 0.8, "variance": 0.05,
               "context": {"species": "bovine"}, "quote": "FGF2 increased proliferation"
               if "increased proliferation" in u else "FGF2 raised proliferation"}]
        if "removing FBS" in u or "high FBS" in u:
            q = "removing FBS (serum-free) did not reduce growth" if "removing FBS" in u else "high FBS was unnecessary and increased cost"
            ev.append({"component": "FBS", "direction": -1, "effect": -0.6, "variance": 0.05,
                       "context": {"species": "bovine"}, "quote": q})
        return json.dumps({"evidence": ev})
    if "Operator: medium" in u:
        return json.dumps({"fields": {"E.basal_medium": ["DMEM/F12"], "E.serum_free_status": "serum-free",
                                      "E.growth_factors": ["FGF2"]},
                           "evidence": {"E.basal_medium": {"quote": "Basal medium was DMEM/F12"
                                        if "Basal medium was DMEM/F12" in u else "DMEM/F12 base",
                                        "location": "Methods", "confidence": "high"}}})
    if "Operator: context" in u:
        return json.dumps({"fields": {"B.species": ["bovine"], "B.main_track": "medium"}, "evidence": {}})
    return "{}"


def main() -> int:
    client = get_client("mock", "demo", handler=_handler)
    normalizer = ComponentNormalizer(ROOT / "config" / "ontology")
    kb = KnowledgeBase(Path(tempfile.mkdtemp()) / "demo_kb.sqlite", normalizer=normalizer)

    print("STEP 1  Operator extraction (section-routed, small prompts)")
    op = OperatorExtractor(client)
    for ref, text in PAPERS:
        ext = op.extract(ref, text)
        kb.upsert_paper(ref)
        kb.upsert_extraction(ext)
        cov = ext.extraction_meta["operators"]
        print(f"   {ref.paper_id}: serum_free={ext.medium_info.serum_free_status}, "
              f"GFs={ext.medium_info.growth_factors}, ops_ok={sum(o['status']=='ok' for o in cov)}/{len(cov)}")

    print("\nSTEP 2  Evidence synthesis (random-effects meta-analysis over quoted effects)")
    items = []
    for ref, text in PAPERS:
        items += extract_effects(client, ref, text, "proliferation", normalizer=normalizer)
    summaries = synthesize(items)
    kb.upsert_evidence_summaries(summaries)
    for s in summaries:
        print(f"   {s.component:12s} P(beneficial|proliferation)={s.p_beneficial:.2f} "
              f"(k={s.k}, {s.method}){'  [context-dependent]' if s.context_dependent else ''}")

    print("\nSTEP 3  Build πBO prior from the KB and steer the optimizer")
    space = default_medium_space()
    prior = EvidencePrior.from_kb(kb, space, "proliferation")
    print("   evidence beliefs:\n     " + prior.describe().replace("\n", "\n     "))

    obj = SyntheticMediumObjective(noise=0.0)
    mobo = MultiObjectiveBO(space, obj.objectives, seed=0)
    init = space.sample(6, seed=0)
    mobo.tell(init, obj.evaluate_many(init))
    batch = mobo.ask(4, preference_weights={"proliferation": 0.7, "cost": 0.3}, evidence_prior=prior)

    print("\nSTEP 4  Next pre-registerable batch (prior-guided):")
    for i, s in enumerate(batch, 1):
        knobs = {k: s.formulation[k] for k in ("FGF2", "FBS", "recombinant-albumin") if k in s.formulation}
        print(f"   exp{i} [{s.source}]  {knobs}")
    kb.close()
    print("\nOK: operators -> evidence synthesis -> KB -> evidence prior -> prior-guided MOBO all composed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
