"""CultivateAgent command-line interface.

Subcommands map onto the pipeline stages::

    cultivate init      # create config.yaml / .env from examples
    cultivate ingest    # BibTeX + PDFs -> per-paper folders
    cultivate triage    # A/B/C relevance tiering -> KB
    cultivate extract   # evidence-grounded schema extraction -> KB
    cultivate export    # screening table / components / evidence / JSONL
    cultivate stats     # knowledge-base summary
    cultivate evidence-audit
    cultivate extraction-readiness
    cultivate review-packet
    cultivate adjudication-template
    cultivate adjudication-validate
    cultivate adjudication-export
    cultivate design    # goal-conditioned medium recommendation
    cultivate schema    # print the field guide or JSON schema
    cultivate smoke     # offline end-to-end self-test (mock LLM, no API key)

Run ``cultivate <cmd> -h`` for per-command options.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import List, Optional

from .config import Config, load_config


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #
def _kb(cfg: Config, with_normalizer: bool = True):
    from .kb import KnowledgeBase
    from .normalize import ComponentNormalizer

    normalizer = ComponentNormalizer(cfg.ontology_dir) if with_normalizer else None
    return KnowledgeBase(cfg.kb_file, normalizer=normalizer)


def _apply_overrides(cfg: Config, args) -> Config:
    if getattr(args, "provider", None):
        cfg.llm.provider = args.provider
    if getattr(args, "model", None):
        cfg.llm.model = args.model
    return cfg


def _print_json(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


# --------------------------------------------------------------------------- #
# Commands                                                                    #
# --------------------------------------------------------------------------- #
def cmd_init(args) -> int:
    root = Path(args.root)
    pairs = [
        (root / "config" / "config.example.yaml", root / "config" / "config.yaml"),
        (root / ".env.example", root / ".env"),
    ]
    for src, dst in pairs:
        if not src.exists():
            print(f"! missing template {src}")
            continue
        if dst.exists():
            print(f"= exists, skipped {dst}")
        else:
            shutil.copy2(src, dst)
            print(f"+ created {dst}")
    print("\nNext: edit config/config.yaml and put API keys in .env, then run `cultivate ingest`.")
    return 0


def cmd_ingest(args) -> int:
    cfg = _apply_overrides(load_config(root=args.root), args)
    from .ingest import ingest_library, iter_ingested, parse_bibtex

    bibtex = args.bibtex or cfg.ingest.bibtex_path
    bibtex_path = Path(cfg.root) / bibtex if not Path(bibtex).is_absolute() else Path(bibtex)
    if not bibtex_path.exists():
        print(f"BibTeX not found: {bibtex_path}\nExport your Zotero library to BibTeX and set ingest.bibtex_path.")
        return 1

    refs = parse_bibtex(bibtex_path)
    if args.limit:
        refs = refs[: args.limit]
    print(f"Parsed {len(refs)} references from {bibtex_path.name}")

    def progress(i, total, res):
        flag = "ok " if res.ok else "no-text"
        print(f"[{i}/{total}] {flag}  {res.slug}")

    results = ingest_library(
        refs, cfg.papers_dir,
        extract_page_images=cfg.ingest.extract_page_images and not args.no_images,
        extract_figures=cfg.ingest.extract_figures and not args.no_images,
        extract_tables=cfg.ingest.extract_tables,
        page_image_dpi=cfg.ingest.page_image_dpi,
        grobid_tei=args.grobid_tei,
        grobid_url=args.grobid_url,
        grobid_timeout=args.grobid_timeout,
        force=args.force,
        on_progress=progress,
    )
    with_text = sum(1 for r in results if r.status.has_fulltext)
    with_tei = sum(1 for r in results if r.status.has_structured_fulltext)
    print(
        f"\nIngested {len(results)} papers into {cfg.papers_dir} "
        f"({with_text} with full text, {with_tei} with structured TEI)."
    )

    kb = _kb(cfg)
    for _, meta in iter_ingested(cfg.papers_dir):
        kb.upsert_paper(meta.ref, triage_category=meta.triage_category, ingested_at=meta.status.ingested_at)
    kb.close()
    return 0


def cmd_triage(args) -> int:
    cfg = _apply_overrides(load_config(root=args.root), args)
    from .ingest import iter_ingested
    from .triage import classify_paper

    client = cfg.make_llm_client(triage=True)
    kb = _kb(cfg)
    n = 0
    for paths, meta in iter_ingested(cfg.papers_dir):
        if args.limit and n >= args.limit:
            break
        text = paths.read_fulltext()
        res = classify_paper(client, meta.ref, text)
        kb.upsert_paper(meta.ref, ingested_at=meta.status.ingested_at)
        kb.upsert_triage(res)
        meta.triage_category = res.triage_category
        paths.save_metadata(meta)
        print(f"[{res.triage_category or '?'}] {meta.ref.paper_id}  — {res.rationale[:80]}")
        n += 1
    kb.close()
    print(f"\nTriaged {n} papers.")
    return 0


def cmd_extract(args) -> int:
    cfg = _apply_overrides(load_config(root=args.root), args)
    from .extract import OperatorExtractor, extract_paper
    from .ingest import iter_ingested
    from .schema import structured_paper_from_grobid_tei_path

    client = cfg.make_llm_client()
    mode = getattr(args, "mode", "blocks")
    operator_extractor = OperatorExtractor(client, verify_evidence=cfg.extract.require_evidence) if mode == "operators" else None
    kb = _kb(cfg)
    n = 0
    failed = 0
    ingested = list(iter_ingested(cfg.papers_dir))
    selected_paper_ids: Optional[set[str]] = None
    if getattr(args, "ids", None):
        selected_paper_ids = _resolve_extract_paper_ids(
            args.ids,
            cfg,
            ingested,
            review_queue=getattr(args, "review_queue", None),
            manifest=getattr(args, "manifest", None),
        )
        if not selected_paper_ids:
            print(f"! no ingested papers matched --ids {args.ids!r}", file=sys.stderr)
            kb.close()
            return 2

    for paths, meta in ingested:
        if selected_paper_ids is not None and meta.ref.paper_id not in selected_paper_ids:
            continue
        if args.tier and (meta.triage_category or "").upper() != args.tier.upper():
            continue
        if args.limit and n >= args.limit:
            break
        text = paths.read_fulltext()
        structured_paper = None
        if paths.fulltext_xml.exists():
            try:
                structured_paper = structured_paper_from_grobid_tei_path(
                    meta.ref.paper_id,
                    paths.fulltext_xml,
                    title=meta.ref.title or None,
                )
                if not text.strip():
                    text = structured_paper.all_text()
            except Exception as e:  # noqa: BLE001
                print(f"! TEI parse failed for {meta.ref.paper_id}; using plain text fallback: {e}")
        if not text.strip():
            print(f"- skip (no text): {meta.ref.paper_id}")
            continue
        if operator_extractor is not None:
            ext = operator_extractor.extract(meta.ref, structured_paper or text)
            ext.triage_category = meta.triage_category
        else:
            ext = extract_paper(
                client, meta.ref, text,
                triage_blocks=cfg.extract.triage_blocks,
                full_blocks=cfg.extract.full_blocks,
                full=not args.triage_only,
                max_context_chars=cfg.extract.max_context_chars,
                verify_evidence=cfg.extract.require_evidence,
                triage_category=meta.triage_category,
                structured_paper=structured_paper,
            )
        if _is_total_operator_call_failure(ext):
            failed += 1
            print(
                f"! extraction failed for {meta.ref.paper_id} "
                "(all operators had provider call_error; not writing extraction)",
                file=sys.stderr,
            )
            continue
        kb.upsert_paper(meta.ref, triage_category=meta.triage_category)
        kb.upsert_extraction(ext)
        g = (ext.extraction_meta or {}).get("grounding_rate")
        if g is None:
            for p in (ext.extraction_meta or {}).get("passes", []) or []:
                if p.get("grounding_rate") is not None:
                    g = p["grounding_rate"]
                    break
        print(f"+ extracted {meta.ref.paper_id}  (mode={mode}, grounding={g})")
        n += 1
    kb.close()
    print(f"\nExtracted {n} papers into {cfg.kb_file}")
    if failed:
        print(f"Failed extractions: {failed}", file=sys.stderr)
        return 2
    return 0


def cmd_export(args) -> int:
    cfg = load_config(root=args.root)
    from .kb import (
        export_components_csv,
        export_evidence_csv,
        export_extractions_jsonl,
        export_screening_csv,
    )

    out = Path(args.out or (cfg.data_path / "exports"))
    out.mkdir(parents=True, exist_ok=True)
    kb = _kb(cfg)
    files = [
        export_screening_csv(kb, out / "screening_table.csv"),
        export_components_csv(kb, out / "medium_components.csv"),
        export_evidence_csv(kb, out / "evidence.csv"),
        export_extractions_jsonl(kb, out / "extractions.jsonl"),
    ]
    kb.close()
    for f in files:
        print(f"+ {f}")
    return 0


def cmd_stats(args) -> int:
    cfg = load_config(root=args.root)
    kb = _kb(cfg)
    _print_json(kb.stats())
    print("\nTop growth factors:")
    for name, count in kb.component_counts(role="growth_factor")[:10]:
        print(f"  {count:3d}  {name}")
    kb.close()
    return 0


def cmd_evidence(args) -> int:
    """Extract quoted directional effects over the corpus, synthesize, store + export."""
    cfg = _apply_overrides(load_config(root=args.root), args)
    from .evidence import extract_effects, synthesize
    from .ingest import iter_ingested
    from .normalize import ComponentNormalizer

    client = cfg.make_llm_client()
    normalizer = ComponentNormalizer(cfg.ontology_dir)
    kb = _kb(cfg)
    items = []
    n = 0
    for paths, meta in iter_ingested(cfg.papers_dir):
        if args.limit and n >= args.limit:
            break
        text = paths.read_fulltext()
        if not text.strip():
            continue
        found = extract_effects(client, meta.ref, text, args.outcome, normalizer=normalizer,
                                verify_evidence=cfg.extract.require_evidence)
        items.extend(found)
        n += 1
        print(f"  {meta.ref.paper_id}: {len(found)} directional effect(s)")

    out_dir = Path(args.out or (cfg.data_path / "exports"))
    out_dir.mkdir(parents=True, exist_ok=True)
    items_out = out_dir / f"effect_items_{args.outcome}.json"
    items_out.write_text(json.dumps([it.__dict__ for it in items], ensure_ascii=False, indent=1), encoding="utf-8")

    summaries = synthesize(items)
    kb.upsert_evidence_summaries(summaries)

    out = out_dir / f"evidence_{args.outcome}.csv"
    import csv as _csv
    with out.open("w", newline="", encoding="utf-8") as f:
        w = _csv.writer(f)
        w.writerow(["component", "outcome", "context", "k", "method", "p_beneficial",
                    "ci_low", "ci_high", "i_squared", "context_dependent", "paper_ids", "note"])
        for s in summaries:
            w.writerow([s.component, s.outcome, s.context_key, s.k, s.method, s.p_beneficial,
                        s.ci_low, s.ci_high, s.i_squared, s.context_dependent,
                        ";".join(s.paper_ids), s.note])
    kb.close()
    print(f"\nSynthesized {len(summaries)} (component,outcome,context) summaries from {len(items)} "
          f"effects over {n} papers -> {out}")
    print(f"Raw effect items -> {items_out}")
    for s in summaries[:12]:
        flag = "  [context-dependent: TEST DIRECTLY]" if s.context_dependent else ""
        print(f"  {s.component:24s} p_beneficial={s.p_beneficial:.2f} (k={s.k}, {s.method}){flag}")
    return 0


def cmd_evidence_audit(args) -> int:
    """Audit extracted evidence items against wet-lab entry gates."""
    cfg = load_config(root=args.root)
    from .evidence import audit_effect_items, load_effect_items_json, write_evidence_audit_markdown

    items_path = Path(args.items or (cfg.data_path / "exports" / f"effect_items_{args.outcome}.json"))
    human_review = Path(args.human_review or (cfg.data_path / "literature" / "bovine_human_review_queue.tsv"))
    if not items_path.exists():
        print(f"! missing effect-item export: {items_path}", file=sys.stderr)
        print("  Run `cultivate evidence` or another extraction script that writes EvidenceItem JSON first.", file=sys.stderr)
        return 2
    items = load_effect_items_json(items_path)
    audit = audit_effect_items(
        items,
        outcome=args.outcome,
        human_review_path=human_review,
        min_candidates=args.min_candidates,
    )
    if args.out:
        out = write_evidence_audit_markdown(audit, args.out)
        print(f"+ wrote {out}")
    print(f"Evidence audit: {audit.decision}")
    print(f"  items={audit.total_items} papers={audit.total_papers} components={audit.component_count}")
    print(f"  AI-review candidates={len(audit.ai_review_candidates)}")
    print(f"  critical human-review open={audit.human_open_critical}/{audit.human_total_critical}")
    for blocker in audit.blockers:
        print(f"  BLOCKER: {blocker}")
    return 1 if args.fail_on_no_go and audit.decision != "GO" else 0


def cmd_extraction_readiness(args) -> int:
    """Audit local full text before section-routed operator extraction."""
    cfg = load_config(root=args.root)
    from .extract import (
        build_extraction_readiness,
        write_extraction_readiness_markdown,
        write_extraction_readiness_tsv,
    )

    ids = _expand_review_ids(args.ids)
    rows = build_extraction_readiness(
        review_queue_path=args.review_queue or (cfg.data_path / "literature" / "bovine_human_review_queue.tsv"),
        manifest_path=args.manifest or (cfg.data_path / "literature" / "bovine_corpus_manifest.tsv"),
        papers_dir=cfg.papers_dir,
        review_ids=ids,
        path_base=cfg.root,
    )
    md = write_extraction_readiness_markdown(rows, args.out)
    tsv = write_extraction_readiness_tsv(rows, args.tsv)
    ready = sum(1 for row in rows if row.status == "ready_for_operator_extraction")
    fallback = sum(1 for row in rows if row.status == "ready_with_fulltext_fallback")
    partial = sum(1 for row in rows if row.status == "partial_operator_ready")
    print(f"+ wrote {md}")
    print(f"+ wrote {tsv}")
    print(
        f"Extraction readiness: {ready} ready, {fallback} fallback-ready, "
        f"{partial} partial, {len(rows) - ready - fallback - partial} not ready"
    )
    return 0


def cmd_review_packet(args) -> int:
    """Build a human-review packet with local passage locators."""
    cfg = load_config(root=args.root)
    from .evidence import build_review_packet, write_review_packet_markdown

    ids = _expand_review_ids(args.ids)
    items = build_review_packet(
        review_queue_path=args.review_queue or (cfg.data_path / "literature" / "bovine_human_review_queue.tsv"),
        manifest_path=args.manifest or (cfg.data_path / "literature" / "bovine_corpus_manifest.tsv"),
        papers_dir=cfg.papers_dir,
        review_ids=ids,
        top_k=args.top_k,
        path_base=cfg.root,
    )
    out = write_review_packet_markdown(items, args.out)
    ready = sum(1 for i in items if i.status == "ready_for_human_review")
    print(f"+ wrote {out}")
    print(f"Review packet: {ready}/{len(items)} tasks have local full-text locators")
    return 0


def cmd_adjudication_template(args) -> int:
    """Create a TSV worksheet for human evidence adjudication."""
    cfg = load_config(root=args.root)
    from .evidence import write_adjudication_template

    ids = _expand_review_ids(args.ids)
    out = write_adjudication_template(
        review_queue_path=args.review_queue or (cfg.data_path / "literature" / "bovine_human_review_queue.tsv"),
        manifest_path=args.manifest or (cfg.data_path / "literature" / "bovine_corpus_manifest.tsv"),
        papers_dir=cfg.papers_dir,
        review_ids=ids,
        out_path=args.out,
        top_k=args.top_k,
        include_missing=args.include_missing,
        path_base=cfg.root,
    )
    print(f"+ wrote {out}")
    return 0


def cmd_adjudication_validate(args) -> int:
    """Validate a filled human-adjudication TSV worksheet."""
    from .evidence import validate_adjudication_worksheet, write_validation_markdown

    result = validate_adjudication_worksheet(args.worksheet)
    if args.out:
        out = write_validation_markdown(result, args.out)
        print(f"+ wrote {out}")
    print(f"Adjudication worksheet: {'PASS' if result.ok else 'FAIL'} ({len(result.issues)} issues, {result.rows} rows)")
    for issue in result.issues[:20]:
        print(f"  row {issue.row_number} {issue.review_id} {issue.field}: {issue.message}")
    return 1 if args.fail_on_issues and not result.ok else 0


def cmd_adjudication_status(args) -> int:
    """Summarize human-adjudication worksheet progress."""
    from .evidence import (
        format_adjudication_status_markdown,
        summarize_adjudication_worksheet,
        write_adjudication_status_markdown,
    )

    status = summarize_adjudication_worksheet(args.worksheet)
    if args.out:
        out = write_adjudication_status_markdown(status, args.out)
        print(f"+ wrote {out}")
    else:
        print(format_adjudication_status_markdown(status))
    print(
        "Adjudication status: "
        f"{status.resolved}/{status.rows} resolved, "
        f"{status.evidence_bearing} evidence-bearing, "
        f"{status.validation_issues} validation issues"
    )
    return 1 if args.fail_on_incomplete and (status.blank or status.validation_issues) else 0


def cmd_adjudication_passages(args) -> int:
    """Preview worksheet passage ranges for human adjudication."""
    cfg = load_config(root=args.root)
    from .evidence import (
        build_adjudication_passage_previews,
        format_adjudication_passages_markdown,
        write_adjudication_passages_markdown,
    )

    ids = _expand_review_ids(args.ids) if args.ids else []
    previews = build_adjudication_passage_previews(
        args.worksheet,
        review_ids=ids,
        path_base=cfg.root,
        max_ranges=args.max_ranges,
        context_chars=args.context_chars,
    )
    if args.out:
        out = write_adjudication_passages_markdown(previews, args.out)
        print(f"+ wrote {out}")
    else:
        print(format_adjudication_passages_markdown(previews))
    ok = sum(1 for p in previews if p.status == "ok")
    print(f"Adjudication passage previews: {ok}/{len(previews)} ranges readable")
    return 0 if ok or not previews else 1


def cmd_adjudication_export(args) -> int:
    """Export human-supported decisions into the adjudicated evidence table."""
    from .evidence import count_evidence_rows, export_adjudicated_evidence

    try:
        out = export_adjudicated_evidence(
            worksheet_path=args.worksheet,
            out_path=args.out,
            include_partial=not args.supported_only,
            require_valid=not args.skip_validation,
        )
    except ValueError as e:
        print(f"! {e}", file=sys.stderr)
        return 2
    rows = count_evidence_rows(out)
    print(f"+ wrote {out}")
    print(f"Adjudicated evidence rows exported: {rows}")
    return 0


def _expand_review_ids(spec: str) -> List[str]:
    out: List[str] = []
    for part in (spec or "").split(","):
        part = part.strip()
        if not part:
            continue
        m = re.fullmatch(r"([A-Za-z]+)(\d+)-(?:(?:[A-Za-z]+)?)(\d+)", part)
        if m:
            prefix, start_s, end_s = m.groups()
            start = int(start_s)
            end = int(end_s)
            width = max(len(start_s), len(end_s))
            out.extend(f"{prefix}{i:0{width}d}" for i in range(start, end + 1))
        else:
            out.append(part)
    return out


def _resolve_extract_paper_ids(
    spec: str,
    cfg: Config,
    ingested: list,
    *,
    review_queue: Optional[str] = None,
    manifest: Optional[str] = None,
) -> set[str]:
    """Resolve extract targets from paper IDs, review IDs, or source record IDs."""
    requested = set(_expand_review_ids(spec))
    selected: set[str] = set()
    for paths, meta in ingested:
        aliases = {
            meta.ref.paper_id,
            meta.ref.slug,
            paths.paper_id,
            paths.slug,
            paths.dir.name,
        }
        if requested & aliases:
            selected.add(meta.ref.paper_id)

    from .evidence.review_packet import _best_paper_match, load_manifest, load_review_tasks

    review_queue_path = review_queue or (cfg.data_path / "literature" / "bovine_human_review_queue.tsv")
    manifest_path = manifest or (cfg.data_path / "literature" / "bovine_corpus_manifest.tsv")
    if Path(review_queue_path).exists() and Path(manifest_path).exists():
        records = load_manifest(manifest_path)
        tasks = load_review_tasks(review_queue_path)
        source_ids = set()
        for task in tasks:
            if task.review_id in requested or task.source_record_id in requested:
                source_ids.add(task.source_record_id)
        source_ids.update(rid for rid in requested if rid in records)
        for source_id in source_ids:
            match = _best_paper_match(records.get(source_id), ingested)
            if match:
                _paths, meta = match
                selected.add(meta.ref.paper_id)
    return selected


def _is_total_operator_call_failure(ext) -> bool:
    meta = getattr(ext, "extraction_meta", None) or {}
    if meta.get("mode") != "operators":
        return False
    operators = meta.get("operators") or []
    return bool(operators) and all((op.get("status") == "call_error") for op in operators)


def _parse_weights(spec: str) -> dict:
    weights = {}
    for part in spec.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            weights[k.strip()] = float(v)
    return weights


def cmd_design(args) -> int:
    cfg = _apply_overrides(load_config(root=args.root), args)
    from .design import DesignContext, MediumRecommender, ObjectiveWeights
    from .retrieve import BM25Retriever, build_corpus_from_kb

    if args.preset:
        weights = ObjectiveWeights.from_preset(cfg.design.presets, args.preset)
    elif args.weights:
        weights = ObjectiveWeights(weights=_parse_weights(args.weights))
    else:
        weights = ObjectiveWeights(weights={"proliferation": 0.7, "cost": 0.2, "differentiation_retention": 0.1})

    context = DesignContext(
        cell_type=args.cell, species=args.species, stage=args.stage,
        scaffold=args.scaffold, target_product_type=args.product, starting_medium=args.starting_medium,
    )

    kb = _kb(cfg)
    retriever = BM25Retriever()
    retriever.index(build_corpus_from_kb(kb))
    client = cfg.make_llm_client()
    rec = MediumRecommender(
        client, retriever, kb,
        actionable_variables=cfg.design.actionable_variables or None,
        top_k=cfg.retrieve.top_k,
        verify_citations=args.verify_citations,
    ).recommend(weights, context, n_candidates=args.n)
    kb.close()

    if args.json:
        _print_json(json.loads(rec.model_dump_json()))
    else:
        _print_recommendation_md(rec)
    return 0


def _print_recommendation_md(rec) -> None:
    print(f"# Medium recommendation\n")
    print(f"**Objectives:** {rec.objectives}")
    print(f"**Context:** {rec.context}")
    print(f"**Model:** {rec.model}\n")
    if not rec.candidates:
        print("_No candidates produced (empty KB or offline mock). Ingest + extract papers first._\n")
    for i, c in enumerate(rec.candidates, 1):
        print(f"## Candidate {i}: {c.name}\n{c.summary}\n")
        for ch in c.changes:
            mark = "" if ch.is_actionable else "  ⚠️ non-actionable"
            cites = f"  [{', '.join(ch.cited_paper_ids)}]" if ch.cited_paper_ids else ""
            print(f"- **{ch.variable}** → {ch.change}{mark}{cites}\n    {ch.rationale}")
        if c.cost_vs_performance:
            print(f"\n_Cost vs performance:_ {c.cost_vs_performance}")
        if c.risks_and_unknowns:
            print(f"\n_Risks / unknowns:_ {c.risks_and_unknowns}")
        if c.doe_suggestion:
            print(f"\n_DoE:_ {c.doe_suggestion}")
        print()
    if rec.evidence:
        print("## Evidence")
        for e in rec.evidence:
            print(f"- [{e.index}] {e.paper_id}: {e.title}")
    if rec.caveats:
        print("\n## Caveats")
        for cav in rec.caveats:
            print(f"- {cav}")


def _optimize_demo(args) -> int:
    """Offline closed-loop demo on the synthetic benchmark (no KB / API key)."""
    from .optimize import MultiObjectiveBO, SyntheticMediumObjective, default_medium_space

    space = default_medium_space()
    obj = SyntheticMediumObjective(noise=0.02)
    mobo = MultiObjectiveBO(space, obj.objectives, backend=args.backend, seed=0)
    init = space.sample(5, seed=0)
    mobo.tell(init, obj.evaluate_many(init))

    print("Closed-loop MOBO on a synthetic proliferation/cost objective")
    print(f"{'round':>5} {'n_obs':>6} {'hypervolume':>12} {'|Pareto|':>9}")
    print(f"{0:>5} {mobo.n_observed:>6} {mobo.hypervolume():>12.3f} {len(mobo.pareto()):>9}")
    for r in range(args.rounds):
        sugg = mobo.ask(args.batch, preference_weights={"proliferation": 0.6, "cost": 0.4})
        forms = [s.formulation for s in sugg]
        mobo.tell(forms, obj.evaluate_many(forms))
        print(f"{r+1:>5} {mobo.n_observed:>6} {mobo.hypervolume():>12.3f} {len(mobo.pareto()):>9}")

    print("\nFinal Pareto-optimal formulations (proliferation vs cost trade-off):")
    front = sorted(mobo.pareto(), key=lambda t: t[1]["cost"])
    for f, v in front[:6]:
        knobs = {k: f[k] for k in ("basal_medium", "FGF2", "recombinant-albumin", "FBS") if k in f}
        print(f"  prolif={v['proliferation']:.3f}  cost={v['cost']:.2f}  {knobs}")
    return 0


def cmd_optimize(args) -> int:
    cfg = _apply_overrides(load_config(root=args.root), args)
    if args.demo:
        return _optimize_demo(args)

    from .design import DesignContext, MediumRecommender, ObjectiveWeights
    from .normalize import ComponentNormalizer
    from .optimize import (
        EvidenceGuidedMOBO,
        MultiObjectiveBO,
        Objective,
        default_medium_space,
        space_from_kb,
    )
    from .retrieve import BM25Retriever, build_corpus_from_kb

    kb = _kb(cfg)
    has_papers = kb.stats()["papers"] > 0
    space = space_from_kb(kb) if has_papers else default_medium_space()
    objectives = [
        Objective("proliferation", "max"), Objective("cost", "min"),
        Objective("differentiation_retention", "max"), Objective("tissue_readiness", "max"),
    ]

    if args.preset:
        weights = ObjectiveWeights.from_preset(cfg.design.presets, args.preset)
    elif args.weights:
        weights = ObjectiveWeights(weights=_parse_weights(args.weights))
    else:
        weights = ObjectiveWeights(weights={"proliferation": 0.6, "cost": 0.3, "differentiation_retention": 0.1})

    context = DesignContext(cell_type=args.cell, species=args.species, stage=args.stage,
                            scaffold=args.scaffold, starting_medium=args.starting_medium)

    retriever = BM25Retriever()
    retriever.index(build_corpus_from_kb(kb))
    client = cfg.make_llm_client()
    recommender = MediumRecommender(client, retriever, kb,
                                    actionable_variables=cfg.design.actionable_variables or None,
                                    top_k=cfg.retrieve.top_k,
                                    verify_citations=args.verify_citations)
    mobo = MultiObjectiveBO(space, objectives, backend=args.backend)
    egm = EvidenceGuidedMOBO(mobo, recommender, normalizer=ComponentNormalizer(cfg.ontology_dir))

    evidence_prior = None
    if args.evidence_prior:
        from .optimize import EvidencePrior
        # Highest-weighted objective drives the prior's evidence direction.
        primary = max(weights.normalized, key=weights.normalized.get)
        evidence_prior = EvidencePrior.from_kb(kb, space, primary)
        if evidence_prior.raw_beliefs:
            print(f"Evidence prior ({primary}):\n{evidence_prior.describe()}\n")

    proposal = egm.propose(weights, context, batch_size=args.batch, evidence_prior=evidence_prior)
    kb.close()

    if args.json:
        _print_json(proposal.to_dict())
    else:
        print(f"# Next experiment batch (n_observed={proposal.n_observed}, HV={proposal.hypervolume:.3f})\n")
        print(f"Objectives: {weights.describe()}   Space: {space.dim}-dim ({len(space.parameters)} params)\n")
        for i, b in enumerate(proposal.batch, 1):
            cites = f"  cites={b.cited_paper_ids}" if b.cited_paper_ids else ""
            print(f"## Experiment {i}  [{b.source}]{cites}")
            print(f"   {b.formulation}")
            if b.rationale:
                print(f"   rationale: {b.rationale}")
        if proposal.llm_caveats:
            print("\nCaveats:")
            for c in proposal.llm_caveats:
                print(f"- {c}")
        print("\nThis batch is pre-registerable: commit it before running, then feed results "
              "back with the ask/tell API to continue the loop.")
    return 0


def cmd_schema(args) -> int:
    from .schema.extraction import BLOCKS, PaperExtraction, schema_for_prompt

    if args.json:
        _print_json(PaperExtraction.model_json_schema())
    else:
        blocks = list(args.blocks) if args.blocks else list(BLOCKS.keys())
        print(schema_for_prompt(blocks))
    return 0


def cmd_smoke(args) -> int:
    """Run the whole pipeline offline with a mock LLM (no API key, no cost)."""
    from .design import DesignContext, MediumRecommender, ObjectiveWeights
    from .extract import extract_paper
    from .kb import KnowledgeBase
    from .llm import get_client
    from .normalize import ComponentNormalizer
    from .retrieve import BM25Retriever, build_corpus_from_kb
    from .schema.paper import PaperRef

    root = Path(args.root)
    canned_extract = json.dumps({
        "blocks": {
            "E": {
                "basal_medium": ["DMEM/F12"],
                "serum_usage": "no",
                "serum_free_status": "serum-free",
                "growth_factors": ["bFGF", "recombinant albumin"],
                "medium_optimization_strategy": "single-component addition of recombinant albumin",
            },
            "B": {"main_track": "medium", "target_product_type": "muscle", "is_core_for_modeling": "yes"},
        },
        "evidence": {
            "E.serum_free_status": {"quote": "serum-free B8 medium", "location": "Methods", "confidence": "high"},
            "E.basal_medium": {"quote": "Basal medium was DMEM/F12", "location": "Methods", "confidence": "high"},
        },
    })
    canned_design = json.dumps({
        "candidates": [{
            "name": "Serum-reduced + albumin + FGF2",
            "summary": "Reduce FBS and compensate with recombinant albumin and FGF2.",
            "changes": [
                {"variable": "serum_level", "change": "reduce FBS 10% -> 2%",
                 "rationale": "cost + lot variability", "cited_paper_ids": ["smoke-001"]},
                {"variable": "growth_factors", "change": "add FGF2",
                 "rationale": "proliferation support", "cited_paper_ids": ["smoke-001"]},
                {"variable": "scaffold", "change": "switch to gelatin",
                 "rationale": "(should be flagged: not a medium variable)", "cited_paper_ids": []},
            ],
            "expected_effects": {"proliferation": "up", "cost": "down"},
            "cost_vs_performance": "lower cost; watch proliferation & myogenicity",
            "risks_and_unknowns": "multi-source combination is untested",
            "doe_suggestion": "2x2 FBS x FGF2 factorial",
            "cited_paper_ids": ["smoke-001"],
        }],
        "caveats": ["illustrative mock output"],
    })
    client = get_client("mock", "mock-model", responses=[canned_extract, canned_extract, canned_design])

    ref = PaperRef(
        paper_id="smoke-001",
        title="Serum-free B8/Beefy-9 medium for bovine satellite cells",
        authors=["A. Researcher"], year=2022, journal="Test J",
    )
    text = (
        "We adapted the serum-free B8 medium for bovine satellite cells by adding a single "
        "component, recombinant albumin, yielding Beefy-9. Basal medium was DMEM/F12. "
        "bFGF supported proliferation with a doubling time of ~39 h while maintaining myogenicity."
    )

    normalizer = ComponentNormalizer(root / "config" / "ontology")
    print(f"Ontology loaded: {normalizer.n_terms} surface terms")

    ext = extract_paper(client, ref, text, full=True, verify_evidence=True)
    passes = (ext.extraction_meta or {}).get("passes", [])
    print(f"Extraction OK. serum_free_status={ext.medium_info.serum_free_status!r}  "
          f"growth_factors={ext.medium_info.growth_factors}  grounding={passes[0].get('grounding_rate') if passes else None}")

    kb = KnowledgeBase(root / "data" / "smoke_kb.sqlite", normalizer=normalizer)
    kb.upsert_paper(ref)
    kb.upsert_extraction(ext)
    print(f"KB stats: {kb.stats()}")
    print("Normalized components:", [(c, n) for c, n in kb.component_counts()])

    retriever = BM25Retriever()
    retriever.index(build_corpus_from_kb(kb))
    hits = retriever.search("serum-free proliferation bovine FGF2", top_k=3)
    print(f"Retrieval hits: {[(h.doc_id, round(h.score, 2)) for h in hits]}")

    rec = MediumRecommender(client, retriever, kb).recommend(
        ObjectiveWeights(weights={"proliferation": 0.7, "cost": 0.3}),
        DesignContext(cell_type="bovine satellite cells", species="bovine"),
    )
    print(f"Recommender ran. candidates={len(rec.candidates)}, evidence={len(rec.evidence)}, caveats={len(rec.caveats)}")
    if rec.candidates:
        flagged = [c.variable for c in rec.candidates[0].changes if not c.is_actionable]
        print(f"  whitelist enforcement: non-actionable changes flagged = {flagged}")
    kb.close()
    print("\n✅ Smoke test passed: ingest→extract→normalize→KB→retrieve→design all wired up.")
    return 0


# --------------------------------------------------------------------------- #
# Parser                                                                      #
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cultivate", description="CultivateAgent CLI")
    p.add_argument("--root", default=".", help="project root (default: cwd)")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_llm_flags(sp):
        sp.add_argument("--provider", help="override llm.provider (openai|anthropic|gemini|mock)")
        sp.add_argument("--model", help="override llm.model")

    sp = sub.add_parser("init", help="create config.yaml / .env from examples")
    sp.set_defaults(func=cmd_init)

    sp = sub.add_parser("ingest", help="parse BibTeX + build per-paper folders")
    sp.add_argument("--bibtex", help="path to .bib (default: config)")
    sp.add_argument("--limit", type=int, help="only first N refs")
    sp.add_argument("--no-images", action="store_true", help="skip page-image / figure rendering")
    sp.add_argument("--grobid-tei", action="store_true", help="also call GROBID and save fulltext.xml TEI")
    sp.add_argument("--grobid-url", default="http://localhost:8070", help="GROBID service URL")
    sp.add_argument("--grobid-timeout", type=float, default=60.0, help="seconds to wait for one GROBID PDF request")
    sp.add_argument("--force", action="store_true", help="re-run even if outputs exist")
    add_llm_flags(sp)
    sp.set_defaults(func=cmd_ingest)

    sp = sub.add_parser("triage", help="A/B/C relevance tiering")
    sp.add_argument("--limit", type=int)
    add_llm_flags(sp)
    sp.set_defaults(func=cmd_triage)

    sp = sub.add_parser("extract", help="evidence-grounded schema extraction")
    sp.add_argument("--tier", help="only papers in this tier (A/B/C)")
    sp.add_argument(
        "--ids",
        help="only extract selected paper IDs, review IDs, or source record IDs; e.g. H001-H014,R023,my-paper-id",
    )
    sp.add_argument("--review-queue", help="review queue TSV for resolving H review IDs")
    sp.add_argument("--manifest", help="bovine corpus manifest TSV for resolving R source IDs")
    sp.add_argument("--limit", type=int)
    sp.add_argument("--triage-only", action="store_true", help="run only fast-triage blocks")
    sp.add_argument("--mode", choices=["blocks", "operators"], default="blocks",
                    help="extraction strategy: 'blocks' (2 large passes) or 'operators' "
                         "(several small, section-routed operators; more reliable with real LLMs)")
    add_llm_flags(sp)
    sp.set_defaults(func=cmd_extract)

    sp = sub.add_parser("export", help="export screening / components / evidence / jsonl")
    sp.add_argument("--out", help="output directory")
    sp.set_defaults(func=cmd_export)

    sp = sub.add_parser("stats", help="knowledge-base summary")
    sp.set_defaults(func=cmd_stats)

    sp = sub.add_parser("evidence", help="synthesize literature evidence into priors (P(component beneficial))")
    sp.add_argument("--outcome", default="proliferation",
                    help="outcome to synthesize evidence for (e.g. proliferation)")
    sp.add_argument("--limit", type=int, help="only first N papers")
    sp.add_argument("--out", help="output directory")
    add_llm_flags(sp)
    sp.set_defaults(func=cmd_evidence)

    sp = sub.add_parser("evidence-audit", help="audit extracted evidence items before wet-lab design")
    sp.add_argument("--outcome", default="proliferation",
                    help="outcome to audit (default: proliferation)")
    sp.add_argument("--items", help="EvidenceItem JSON export (default: data/exports/effect_items_<outcome>.json)")
    sp.add_argument("--human-review", help="human review queue TSV (default: data/literature/bovine_human_review_queue.tsv)")
    sp.add_argument("--out", help="write Markdown audit report")
    sp.add_argument("--min-candidates", type=int, default=3,
                    help="minimum AI-review candidates required before the gate can pass")
    sp.add_argument("--fail-on-no-go", action="store_true",
                    help="exit nonzero when the audit decision is NO-GO")
    sp.set_defaults(func=cmd_evidence_audit)

    sp = sub.add_parser("extraction-readiness", help="audit local full text before section-routed extraction")
    sp.add_argument("--ids", default="H001-H016", help="review IDs, e.g. H001-H016 or H001,H004")
    sp.add_argument("--review-queue", help="review queue TSV")
    sp.add_argument("--manifest", help="bovine corpus manifest TSV")
    sp.add_argument("--out", default="docs/EXTRACTION_READINESS_H001_H016.md",
                    help="Markdown output path")
    sp.add_argument("--tsv", default="data/literature/bovine_extraction_readiness_H001_H016.tsv",
                    help="machine-readable TSV output path")
    sp.set_defaults(func=cmd_extraction_readiness)

    sp = sub.add_parser("review-packet", help="build human-review passage locators for review tasks")
    sp.add_argument("--ids", default="H001-H016", help="review IDs, e.g. H001-H016 or H001,H004")
    sp.add_argument("--review-queue", help="review queue TSV")
    sp.add_argument("--manifest", help="bovine corpus manifest TSV")
    sp.add_argument("--out", default="docs/HUMAN_REVIEW_PACKET_H001_H016.md",
                    help="Markdown output path")
    sp.add_argument("--top-k", type=int, default=5, help="candidate passages per review task")
    sp.set_defaults(func=cmd_review_packet)

    sp = sub.add_parser("adjudication-template", help="create a TSV worksheet for human evidence adjudication")
    sp.add_argument("--ids", default="H001-H014", help="review IDs, e.g. H001-H014 or H001,H004")
    sp.add_argument("--review-queue", help="review queue TSV")
    sp.add_argument("--manifest", help="bovine corpus manifest TSV")
    sp.add_argument("--out", default="data/literature/bovine_adjudication_H001_H014.tsv",
                    help="TSV output path")
    sp.add_argument("--top-k", type=int, default=3, help="candidate ranges per review task")
    sp.add_argument("--include-missing", action="store_true", help="include rows without local full text")
    sp.set_defaults(func=cmd_adjudication_template)

    sp = sub.add_parser("adjudication-validate", help="validate a filled human evidence-adjudication worksheet")
    sp.add_argument("--worksheet", default="data/literature/bovine_adjudication_H001_H014.tsv",
                    help="human-adjudication TSV worksheet")
    sp.add_argument("--out", help="optional Markdown validation report")
    sp.add_argument("--fail-on-issues", action="store_true", help="exit nonzero if validation finds issues")
    sp.set_defaults(func=cmd_adjudication_validate)

    sp = sub.add_parser("adjudication-status", help="summarize human-adjudication worksheet progress")
    sp.add_argument("--worksheet", default="data/literature/bovine_adjudication_H001_H014.tsv",
                    help="human-adjudication TSV worksheet")
    sp.add_argument("--out", help="optional Markdown status report")
    sp.add_argument("--fail-on-incomplete", action="store_true",
                    help="exit nonzero if blank decisions or validation issues remain")
    sp.set_defaults(func=cmd_adjudication_status)

    sp = sub.add_parser("adjudication-passages", help="preview worksheet passage ranges for human review")
    sp.add_argument("--worksheet", default="data/literature/bovine_adjudication_H001_H014.tsv",
                    help="human-adjudication TSV worksheet")
    sp.add_argument("--ids", help="optional review IDs, e.g. H001-H003 or H014")
    sp.add_argument("--out", help="optional Markdown output path; omit to print to stdout")
    sp.add_argument("--max-ranges", type=int, default=3, help="suggested ranges to show per row")
    sp.add_argument("--context-chars", type=int, default=260, help="maximum characters per short snippet")
    sp.set_defaults(func=cmd_adjudication_passages)

    sp = sub.add_parser("adjudication-export", help="export human-supported adjudication rows to evidence table")
    sp.add_argument("--worksheet", default="data/literature/bovine_adjudication_H001_H014.tsv",
                    help="human-adjudication TSV worksheet")
    sp.add_argument("--out", default="data/literature/bovine_evidence_table.tsv",
                    help="adjudicated evidence TSV output")
    sp.add_argument("--supported-only", action="store_true", help="exclude partial decisions")
    sp.add_argument("--skip-validation", action="store_true", help="do not validate worksheet before exporting")
    sp.set_defaults(func=cmd_adjudication_export)

    sp = sub.add_parser("design", help="goal-conditioned medium recommendation")
    sp.add_argument("--preset", help="objective-weight preset from config")
    sp.add_argument("--weights", help="e.g. 'proliferation=0.7,cost=0.2,differentiation_retention=0.1'")
    sp.add_argument("--cell", help="cell type context")
    sp.add_argument("--species", help="species context")
    sp.add_argument("--stage", help="expansion|differentiation|both")
    sp.add_argument("--scaffold", help="scaffold context (read-only)")
    sp.add_argument("--product", help="target product type")
    sp.add_argument("--starting-medium", help="current formulation to improve on")
    sp.add_argument("--n", type=int, default=3, help="number of candidates")
    sp.add_argument("--verify-citations", action="store_true", help="run a second LLM verifier over candidate citations")
    sp.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    add_llm_flags(sp)
    sp.set_defaults(func=cmd_design)

    sp = sub.add_parser("optimize", help="propose next experiment batch (evidence-grounded MOBO)")
    sp.add_argument("--demo", action="store_true", help="offline closed-loop demo on a synthetic objective")
    sp.add_argument("--preset", help="objective-weight preset from config")
    sp.add_argument("--weights", help="e.g. 'proliferation=0.6,cost=0.3,differentiation_retention=0.1'")
    sp.add_argument("--cell", help="cell type context")
    sp.add_argument("--species", help="species context")
    sp.add_argument("--stage", help="expansion|differentiation|both")
    sp.add_argument("--scaffold", help="scaffold context (read-only)")
    sp.add_argument("--starting-medium", help="current formulation to improve on")
    sp.add_argument("--batch", type=int, default=4, help="experiments per batch")
    sp.add_argument("--rounds", type=int, default=6, help="rounds (demo mode)")
    sp.add_argument("--backend", default="gp", help="gp | botorch | botorch-log")
    sp.add_argument("--verify-citations", action="store_true", help="run a second LLM verifier over LLM-seeded candidate citations")
    sp.add_argument("--evidence-prior", action="store_true",
                    help="bias the batch with literature evidence priors (run `cultivate evidence` first)")
    sp.add_argument("--json", action="store_true", help="emit JSON")
    add_llm_flags(sp)
    sp.set_defaults(func=cmd_optimize)

    sp = sub.add_parser("schema", help="print field guide or JSON schema")
    sp.add_argument("--blocks", help="block letters, e.g. ABE")
    sp.add_argument("--json", action="store_true", help="print full JSON schema")
    sp.set_defaults(func=cmd_schema)

    sp = sub.add_parser("smoke", help="offline end-to-end self-test (mock LLM)")
    sp.set_defaults(func=cmd_smoke)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
