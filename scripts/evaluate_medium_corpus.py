#!/usr/bin/env python3
"""Evaluate extraction and provider agreement on a tiny medium-paper corpus.

This script is intentionally offline and deterministic. It uses hand-annotated
gold records for four real cultivated-meat medium papers, plus three mock
provider profiles that mimic common extraction failure modes. Real provider
runs can reuse the same gold records by replacing ``provider_predictions`` with
outputs produced by ``cultivate extract --provider ...``.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from cultivate_agent.evaluate import evaluate_corpus
from cultivate_agent.evaluate.extraction_eval import normalize_value
from cultivate_agent.schema.evidence import Confidence, Evidence
from cultivate_agent.schema.extraction import PaperExtraction, _BLOCK_ATTR


@dataclass(frozen=True)
class PaperFixture:
    paper_id: str
    title: str
    reference: str
    sources: List[str]
    source_text: str
    gold_fields: Dict[str, object]
    evidence_quotes: Dict[str, str]
    provider_fields: Dict[str, Dict[str, object]]
    provider_evidence: Dict[str, Dict[str, str]]


def _set_field(ext: PaperExtraction, path: str, value: object) -> None:
    block_letter, field = path.split(".", 1)
    block = getattr(ext, _BLOCK_ATTR[block_letter])
    setattr(block, field, value)


def _make_extraction(
    paper: PaperFixture,
    fields: Dict[str, object],
    evidence_quotes: Dict[str, str],
    *,
    model: str,
) -> PaperExtraction:
    ext = PaperExtraction(paper_id=paper.paper_id)
    _set_field(ext, "A.paper_id", paper.paper_id)
    _set_field(ext, "A.title", paper.title)
    for path, value in fields.items():
        _set_field(ext, path, value)

    verified = 0
    for path, quote in evidence_quotes.items():
        ev = Evidence(quote=quote, location="fixture excerpt", source="abstract", confidence=Confidence.high)
        if ev.verify_against(paper.source_text):
            verified += 1
        else:
            ev.confidence = Confidence.low
            ev.location = "fixture excerpt [UNVERIFIED: quote not found in source]"
        ext.evidence[path] = ev
    total = len(evidence_quotes)
    ext.extraction_meta = {
        "passes": [{
            "model": model,
            "blocks": sorted({p.split(".", 1)[0] for p in fields}),
            "evidence_total": total,
            "evidence_verified": verified,
            "grounding_rate": round(verified / total, 3) if total else None,
        }]
    }
    return ext


def _fixtures() -> List[PaperFixture]:
    return [
        PaperFixture(
            paper_id="stout2022_beefy9",
            title="Simple and effective serum-free medium for sustained expansion of bovine satellite cells for cell cultured meat",
            reference="Stout et al., Communications Biology 5, 466 (2022)",
            sources=[
                "https://www.nature.com/articles/s42003-022-03423-8",
                "https://pubmed.ncbi.nlm.nih.gov/35654948/",
            ],
            source_text=(
                "B8 is adapted for bovine satellite cells through the addition of a single component, "
                "recombinant albumin. This new media (Beefy-9) maintains cell growth over seven passages. "
                "The average doubling time was 39 h. The paper frames the result as serum-free expansion "
                "without sacrificing myogenicity."
            ),
            gold_fields={
                "B.main_track": "medium",
                "B.species": ["bovine"],
                "B.target_product_type": "muscle",
                "D.cell_type": ["satellite cells"],
                "E.serum_free_status": "serum-free",
                "E.growth_factors": ["recombinant albumin"],
                "E.medium_optimization_strategy": "B8 adapted with recombinant albumin",
                "I.proliferation_metrics": ["doubling time"],
                "J.has_extractable_quant_data": "yes",
                "J.key_numeric_results": ["39 h doubling time"],
                "M.recommended_action": "must_extract_now",
            },
            evidence_quotes={
                "E.growth_factors": "addition of a single component, recombinant albumin",
                "J.key_numeric_results": "average doubling time was 39 h",
            },
            provider_fields={
                "mock_gpt": {
                    "B.main_track": "medium",
                    "B.species": ["bovine"],
                    "D.cell_type": ["satellite cells"],
                    "E.serum_free_status": "serum-free",
                    "E.growth_factors": ["recombinant albumin"],
                    "J.has_extractable_quant_data": "yes",
                    "J.key_numeric_results": ["39 h doubling time"],
                    "M.recommended_action": "must_extract_now",
                },
                "mock_claude": {
                    "B.main_track": "medium",
                    "B.species": ["bovine"],
                    "E.serum_free_status": "serum-free",
                    "E.growth_factors": ["albumin"],
                    "J.has_extractable_quant_data": "partial",
                    "M.recommended_action": "must_extract_now",
                },
                "mock_gemini": {
                    "B.main_track": "cell",
                    "B.species": ["bovine"],
                    "E.serum_free_status": "chemically defined",
                    "E.growth_factors": ["FGF2", "recombinant albumin"],
                    "J.has_extractable_quant_data": "yes",
                    "J.key_numeric_results": ["39 h doubling time"],
                    "M.recommended_action": "must_extract_now",
                },
            },
            provider_evidence={
                "mock_gpt": {
                    "E.growth_factors": "addition of a single component, recombinant albumin",
                    "J.key_numeric_results": "average doubling time was 39 h",
                },
                "mock_claude": {"E.growth_factors": "recombinant albumin"},
                "mock_gemini": {
                    "E.growth_factors": "addition of a single component, recombinant albumin",
                    "E.serum_free_status": "chemically defined Beefy-9 medium",
                },
            },
        ),
        PaperFixture(
            paper_id="messmer2022_differentiation",
            title="A serum-free media formulation for cultured meat production supports bovine satellite cell differentiation in the absence of serum starvation",
            reference="Messmer et al., Nature Food 3, 74-85 (2022)",
            sources=[
                "https://www.nature.com/articles/s43016-021-00419-1",
                "https://pubmed.ncbi.nlm.nih.gov/37118488/",
            ],
            source_text=(
                "The study reports a serum-free media formulation for cultured meat production. "
                "Bovine satellite cells undergoing myogenic differentiation were comparable to serum starvation. "
                "The serum-free differentiation media supported three-dimensional bioartificial muscle constructs."
            ),
            gold_fields={
                "B.main_track": "medium",
                "B.species": ["bovine"],
                "B.target_product_type": "muscle",
                "D.cell_type": ["satellite cells"],
                "E.serum_free_status": "serum-free",
                "E.medium_optimization_strategy": "serum-free differentiation formulation",
                "H.structured_product_goal": "bioartificial muscle constructs",
                "I.differentiation_metrics": ["myogenic differentiation"],
                "J.has_extractable_quant_data": "partial",
                "M.recommended_action": "must_extract_now",
            },
            evidence_quotes={
                "E.serum_free_status": "serum-free media formulation",
                "H.structured_product_goal": "three-dimensional bioartificial muscle constructs",
            },
            provider_fields={
                "mock_gpt": {
                    "B.main_track": "medium",
                    "B.species": ["bovine"],
                    "D.cell_type": ["satellite cells"],
                    "E.serum_free_status": "serum-free",
                    "I.differentiation_metrics": ["myogenic differentiation"],
                    "J.has_extractable_quant_data": "partial",
                    "M.recommended_action": "must_extract_now",
                },
                "mock_claude": {
                    "B.main_track": "medium",
                    "B.species": ["bovine"],
                    "E.serum_free_status": "serum-free",
                    "J.has_extractable_quant_data": "no",
                    "M.recommended_action": "keep_for_review_synthesis",
                },
                "mock_gemini": {
                    "B.main_track": "structured_tissue",
                    "B.species": ["bovine"],
                    "E.serum_free_status": "chemically defined",
                    "H.structured_product_goal": "bioartificial muscle constructs",
                    "J.has_extractable_quant_data": "partial",
                    "M.recommended_action": "must_extract_now",
                },
            },
            provider_evidence={
                "mock_gpt": {"E.serum_free_status": "serum-free media formulation"},
                "mock_claude": {"E.serum_free_status": "serum-free media formulation"},
                "mock_gemini": {"H.structured_product_goal": "three-dimensional bioartificial muscle constructs"},
            },
        ),
        PaperFixture(
            paper_id="oneill2022_spent_media",
            title="Spent media analysis suggests cultivated meat media will require species and cell type optimization",
            reference="O'Neill et al., npj Science of Food 6, 46 (2022)",
            sources=[
                "https://www.nature.com/articles/s41538-022-00157-z",
                "https://pmc.ncbi.nlm.nih.gov/articles/PMC11663224/",
            ],
            source_text=(
                "Spent media analysis suggests cultivated meat media will require species and cell type optimization. "
                "The study reports differences in specific consumption rates for several key nutrients. "
                "No one medium is likely ideal and cost effective to culture multiple cell types."
            ),
            gold_fields={
                "B.main_track": "medium",
                "B.species": ["bovine", "chicken", "fish"],
                "E.serum_free_status": "unclear",
                "E.medium_optimization_strategy": "spent media analysis",
                "J.has_extractable_quant_data": "yes",
                "J.extractable_variables": ["nutrient consumption rates"],
                "K.core_findings": "media requirements vary by species and cell type",
                "M.recommended_action": "keep_for_review_synthesis",
            },
            evidence_quotes={
                "E.medium_optimization_strategy": "Spent media analysis suggests",
                "J.extractable_variables": "specific consumption rates for several key nutrients",
            },
            provider_fields={
                "mock_gpt": {
                    "B.main_track": "medium",
                    "B.species": ["bovine", "chicken"],
                    "E.serum_free_status": "unclear",
                    "E.medium_optimization_strategy": "spent media analysis",
                    "J.has_extractable_quant_data": "yes",
                    "J.extractable_variables": ["nutrient consumption rates"],
                    "M.recommended_action": "keep_for_review_synthesis",
                },
                "mock_claude": {
                    "B.main_track": "medium",
                    "B.species": ["bovine", "chicken", "fish"],
                    "E.serum_free_status": "unclear",
                    "J.has_extractable_quant_data": "yes",
                    "M.recommended_action": "keep_for_review_synthesis",
                },
                "mock_gemini": {
                    "B.main_track": "systems_review",
                    "B.species": ["bovine", "chicken", "fish"],
                    "E.serum_free_status": "NR",
                    "J.has_extractable_quant_data": "yes",
                    "J.extractable_variables": ["media cost"],
                    "M.recommended_action": "keep_for_later",
                },
            },
            provider_evidence={
                "mock_gpt": {"J.extractable_variables": "specific consumption rates for several key nutrients"},
                "mock_claude": {"E.medium_optimization_strategy": "Spent media analysis suggests"},
                "mock_gemini": {"J.extractable_variables": "media cost was reduced by 90%"},
            },
        ),
        PaperFixture(
            paper_id="kolkmann2023_microalga",
            title="Development of serum-free and grain-derived-nutrient-free medium using microalga-derived nutrients and mammalian cell-secreted growth factors for sustainable cultured meat production",
            reference="Kolkmann et al., Scientific Reports 13, 498 (2023)",
            sources=[
                "https://www.nature.com/articles/s41598-023-27629-w",
                "https://pubmed.ncbi.nlm.nih.gov/36627406/",
            ],
            source_text=(
                "The supernatant, containing the RL34 cell-secreted growth factors, was used as the conditioned medium. "
                "This medium used CVE added as a nutrient source. The serum-free and grain-derived-nutrient-free medium "
                "promoted the proliferation of bovine myoblasts."
            ),
            gold_fields={
                "B.main_track": "medium",
                "B.species": ["bovine"],
                "D.cell_type": ["myoblasts"],
                "E.serum_free_status": "serum-free",
                "E.hydrolysates_or_extracts": ["CVE"],
                "E.conditioned_medium_or_recycling": "RL34 conditioned medium",
                "J.has_extractable_quant_data": "partial",
                "M.recommended_action": "must_extract_now",
            },
            evidence_quotes={
                "E.conditioned_medium_or_recycling": "RL34 cell-secreted growth factors",
                "E.hydrolysates_or_extracts": "CVE added as a nutrient source",
            },
            provider_fields={
                "mock_gpt": {
                    "B.main_track": "medium",
                    "B.species": ["bovine"],
                    "D.cell_type": ["myoblasts"],
                    "E.serum_free_status": "serum-free",
                    "E.hydrolysates_or_extracts": ["CVE"],
                    "E.conditioned_medium_or_recycling": "RL34 conditioned medium",
                    "J.has_extractable_quant_data": "partial",
                    "M.recommended_action": "must_extract_now",
                },
                "mock_claude": {
                    "B.main_track": "medium",
                    "B.species": ["bovine"],
                    "D.cell_type": ["myoblasts"],
                    "E.serum_free_status": "serum-free",
                    "E.hydrolysates_or_extracts": ["microalga-derived nutrients"],
                    "J.has_extractable_quant_data": "partial",
                    "M.recommended_action": "must_extract_now",
                },
                "mock_gemini": {
                    "B.main_track": "medium",
                    "B.species": ["bovine"],
                    "E.serum_free_status": "serum-free",
                    "E.conditioned_medium_or_recycling": "conditioned medium",
                    "J.has_extractable_quant_data": "yes",
                    "M.recommended_action": "must_extract_now",
                },
            },
            provider_evidence={
                "mock_gpt": {"E.conditioned_medium_or_recycling": "RL34 cell-secreted growth factors"},
                "mock_claude": {"E.hydrolysates_or_extracts": "microalga-derived nutrients"},
                "mock_gemini": {"E.conditioned_medium_or_recycling": "conditioned medium"},
            },
        ),
    ]


def _values_for_provider(papers: Sequence[PaperFixture], provider: str) -> List[PaperExtraction]:
    return [
        _make_extraction(p, p.provider_fields[provider], p.provider_evidence.get(provider, {}), model=provider)
        for p in papers
    ]


def _gold_values(papers: Sequence[PaperFixture]) -> List[PaperExtraction]:
    return [_make_extraction(p, p.gold_fields, p.evidence_quotes, model="hand_gold") for p in papers]


def _value(ext: PaperExtraction, path: str) -> str:
    block_letter, field = path.split(".", 1)
    block = getattr(ext, _BLOCK_ATTR[block_letter])
    val = getattr(block, field)
    if val is None:
        return "<missing>"
    if isinstance(val, list):
        return "; ".join(sorted(normalize_value(v) for v in val)) or "<missing>"
    return normalize_value(str(val))


def cohen_kappa(labels_a: Sequence[str], labels_b: Sequence[str]) -> float:
    if len(labels_a) != len(labels_b):
        raise ValueError("label sequences must be aligned")
    n = len(labels_a)
    if n == 0:
        return 0.0
    observed = sum(a == b for a, b in zip(labels_a, labels_b)) / n
    labels = sorted(set(labels_a) | set(labels_b))
    expected = 0.0
    for label in labels:
        pa = labels_a.count(label) / n
        pb = labels_b.count(label) / n
        expected += pa * pb
    return round((observed - expected) / (1 - expected), 4) if expected < 1 else 1.0


def pairwise_agreement(
    predictions: Dict[str, List[PaperExtraction]],
    fields: Sequence[str],
) -> List[Dict[str, object]]:
    providers = sorted(predictions)
    rows = []
    for field in fields:
        kappas = []
        exacts = []
        for i, a in enumerate(providers):
            for b in providers[i + 1:]:
                avals = [_value(ext, field) for ext in predictions[a]]
                bvals = [_value(ext, field) for ext in predictions[b]]
                kappas.append(cohen_kappa(avals, bvals))
                exacts.append(sum(x == y for x, y in zip(avals, bvals)) / len(avals))
        rows.append({
            "field": field,
            "mean_kappa": round(sum(kappas) / len(kappas), 4),
            "mean_exact": round(sum(exacts) / len(exacts), 4),
        })
    return rows


def markdown_table(rows: Iterable[Dict[str, object]], columns: Sequence[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(c, "")) for c in columns) + " |")
    return "\n".join(lines)


def write_reports(out_dir: Path, provider: str = "mock_gpt") -> Tuple[Path, Path]:
    papers = _fixtures()
    golds = _gold_values(papers)
    provider_names = sorted(papers[0].provider_fields)
    predictions = {name: _values_for_provider(papers, name) for name in provider_names}

    report = evaluate_corpus(predictions[provider], golds)
    rows = report.to_rows()
    agreement_fields = ["B.main_track", "E.serum_free_status", "J.has_extractable_quant_data", "M.recommended_action"]
    agreement_rows = pairwise_agreement(predictions, agreement_fields)
    least_reliable = sorted(agreement_rows, key=lambda r: (r["mean_kappa"], r["mean_exact"]))[:2]

    out_dir.mkdir(parents=True, exist_ok=True)
    eval_path = out_dir / "EVAL_RESULTS.md"
    agreement_path = out_dir / "MODEL_AGREEMENT.md"

    eval_path.write_text(
        "# Extraction Evaluation Results\n\n"
        "Status: offline hand-annotated fixture over four real medium papers. "
        "This is a smoke benchmark for `evaluate.evaluate_corpus`, not a claim of full-paper production accuracy.\n\n"
        f"Evaluated provider profile: `{provider}`\n\n"
        f"- Papers: {report.n_papers}\n"
        f"- Mean grounding rate: {report.mean_grounding()}\n"
        f"- Overall: {report.overall()}\n\n"
        "## Per-Field Scores\n\n"
        + markdown_table(rows, ["field", "tp", "fp", "fn", "precision", "recall", "f1"])
        + "\n\n## Corpus\n\n"
        + "\n".join(
            f"- {p.reference}. Sources: " + ", ".join(p.sources)
            for p in papers
        )
        + "\n\n## Error Analysis\n\n"
        "- The A-M schema is broad enough that sparse abstracts under-score fields that require methods/tables; this fixture should be treated as a lower-bound protocol check.\n"
        "- Medium fields are the most stable when the source explicitly names serum-free status or a component. Growth-factor and extract names still need synonym canonicalization before scoring.\n"
        "- Quantitative fields are brittle: `partial` versus `yes` often depends on whether the paper has machine-readable tables, not only whether the abstract mentions numbers.\n"
        "- Grounding failures are correctly counted when a provider supplies a plausible but absent quote.\n",
        encoding="utf-8",
    )

    agreement_path.write_text(
        "# Provider Agreement Report\n\n"
        "Status: offline cross-provider simulation (`mock_gpt`, `mock_claude`, `mock_gemini`). "
        "The script is wired so real provider outputs can replace these fixtures, but no API-backed GPT/Claude/Gemini run was performed in this environment.\n\n"
        "## Agreement By Categorical Field\n\n"
        + markdown_table(agreement_rows, ["field", "mean_kappa", "mean_exact"])
        + "\n\n## Least Reliable Fields\n\n"
        + "\n".join(f"- `{r['field']}`: mean kappa {r['mean_kappa']}, exact agreement {r['mean_exact']}" for r in least_reliable)
        + "\n\n## Interpretation\n\n"
        "- `E.serum_free_status` is vulnerable to overclaiming chemically defined status from a serum-free claim.\n"
        "- `J.has_extractable_quant_data` mixes article-level data availability with abstract-level visibility; it needs a stricter rubric.\n"
        "- `B.main_track` splits when papers are both medium and structured-tissue demonstrations; medium-centered downstream code should keep acting only on medium variables.\n",
        encoding="utf-8",
    )
    return eval_path, agreement_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="docs", help="directory for markdown reports")
    parser.add_argument("--provider", default="mock_gpt", help="fixture provider profile to score")
    args = parser.parse_args()

    eval_path, agreement_path = write_reports(Path(args.out_dir), provider=args.provider)
    print(f"+ wrote {eval_path}")
    print(f"+ wrote {agreement_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
