"""S4 -> S5 bridge: adjudicated evidence table -> EvidenceItems -> summaries -> prior."""

from __future__ import annotations

import csv
import math

from cultivate_agent.evidence.adjudicated_loader import (
    load_adjudicated_items,
    summarize_adjudicated,
)
from cultivate_agent.evidence.adjudication import EVIDENCE_TABLE_COLUMNS


def _write(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=EVIDENCE_TABLE_COLUMNS, delimiter="\t")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in EVIDENCE_TABLE_COLUMNS})


def test_ratio_row_becomes_tier1_and_text_row_becomes_direction(tmp_path):
    p = tmp_path / "evi.tsv"
    _write(p, [
        # recorded fold_change + variance -> tier 1
        {"review_id": "H001", "source_record_id": "R015", "decision": "supported",
         "formulation_or_variable": "FGF2", "endpoint": "proliferation",
         "numeric_effect_metric": "fold_change", "numeric_effect_value": "2.0",
         "numeric_effect_variance": "0.02", "key_finding": "FGF2 increased proliferation"},
        # direction-only supported row (no number) -> tier 3 via text
        {"review_id": "H012", "source_record_id": "R022", "decision": "partial",
         "formulation_or_variable": "soy protein hydrolysate", "endpoint": "proliferation",
         "key_finding": "soy hydrolysate enhanced cell growth"},
        # unsupported -> skipped
        {"review_id": "H007", "source_record_id": "R018", "decision": "unsupported",
         "formulation_or_variable": "TGF-beta1", "key_finding": "no effect shown"},
        # supported but no determinable direction -> skipped + counted
        {"review_id": "H099", "source_record_id": "R099", "decision": "supported",
         "formulation_or_variable": "mystery factor", "key_finding": "was tested at several doses"},
    ])
    items, skipped = load_adjudicated_items(p)
    assert skipped == 1                                  # the neutral 'mystery factor' row
    comps = {it.component: it for it in items}
    assert set(comps) == {"FGF2", "soy protein hydrolysate"}   # unsupported dropped

    fgf2 = comps["FGF2"]
    assert fgf2.tier == 1                                 # effect + variance
    assert math.isclose(fgf2.effect, math.log(2.0), rel_tol=1e-9)
    assert fgf2.variance == 0.02
    assert fgf2.direction == 1

    soy = comps["soy protein hydrolysate"]
    assert soy.tier == 3 and soy.direction == 1           # direction from 'enhanced'
    assert soy.effect is None


def test_detrimental_direction_from_text(tmp_path):
    p = tmp_path / "evi.tsv"
    _write(p, [{"review_id": "H007", "source_record_id": "R018", "decision": "supported",
                "formulation_or_variable": "TGF-beta1", "endpoint": "proliferation",
                "key_finding": "TGF-beta1 suppressed proliferation"}])
    items, _ = load_adjudicated_items(p)
    assert items[0].direction == -1


def test_bridge_reaches_prior(tmp_path):
    from cultivate_agent.normalize import ComponentNormalizer
    from cultivate_agent.optimize import EvidencePrior, default_medium_space
    from pathlib import Path
    onto = Path(__file__).resolve().parents[1] / "config" / "ontology"
    norm = ComponentNormalizer(onto)
    p = tmp_path / "evi.tsv"
    _write(p, [
        {"review_id": "H002", "source_record_id": "R015", "decision": "supported",
         "formulation_or_variable": "bFGF", "endpoint": "proliferation",
         "key_finding": "bFGF increased proliferation"},          # canonicalizes to FGF2
    ])
    summaries = summarize_adjudicated(p, normalizer=norm)
    assert any(s.component == "FGF2" for s in summaries)          # alias resolved
    prior = EvidencePrior.from_summaries(default_medium_space(), summaries)
    assert prior is not None
