# AI-for-Science Method Review And CultivateAgent Algorithm Roadmap

Status: active method record  
Date: 2026-07-08

Source registry:

- `data/literature/ai_for_science_method_sources.tsv`

## 1. Decision

The most valuable next technical work is **not** to generate wet-lab candidate
formulations yet. The current bottleneck is Stage S3, full-text extraction
reliability.

Immediate priority:

> Build a document-structured, evidence-grounded, section-routed extraction
> workflow for the bovine P1 corpus before advancing to search-space design or
> wet-lab pre-registration.

Why:

- Current live OpenAI/Anthropic extraction was too sparse to count as successful
  model agreement.
- Gemini live comparison is blocked by missing credentials.
- The bovine manifest exists, but the P1 core papers have not yet been
  full-text extracted and human-adjudicated.
- Wet-lab design would be premature without decision-critical formulation,
  dose, endpoint, cost, and identity evidence.

## 2. Literature Lessons

### 2.1 Autonomous labs separate planning, evidence, execution, and review

A-Lab combines computation, literature-derived priors, ML/active learning,
robotic execution, and failure analysis as distinct layers. CultivateAgent
should mirror that separation: literature evidence should define search space,
BO should select batches, wet-lab work should execute committed protocols, and
failure analysis should be explicit.

Coscientist and ChemCrow show the value of tool-augmented LLM systems, but also
support a boundary: do not let the LLM silently make experimental decisions.
Tools, citations, code execution, and safety checks must remain auditable.

Project implication:

- Keep the sequential pipeline: ingest -> triage -> extract -> normalize -> KB
  -> retrieve -> design -> optimize.
- Do not rebrand this as an unconstrained multi-agent system.
- Keep human gates before wet-lab execution.

### 2.2 Scientific literature agents require full-text, citations, and feedback

PaperQA2 and OpenScholar both point to the same design requirement: scientific
RAG needs full-text retrieval, metadata-aware search, citation grounding, and
iterative/self-feedback checks. Abstract-only extraction is not enough for
medium formulation because dose ranges, component tables, and endpoint details
often appear in methods, tables, captions, or supplements.

Project implication:

- The next extractor should work over structured sections and tables, not one
  flat `fulltext.txt`.
- Evidence items should carry local passage identifiers, not only paper IDs.
- Retrieval agreement should be measured over evidence clusters before design.

### 2.3 Scientific information extraction should be schema-bound and evaluated

Recent scientific IE work supports structured outputs, JSON-like records, and
task-specific evaluation. The A-M schema is useful as the overall ontology, but
it is too broad for one monolithic extraction pass over a full paper.

Project implication:

- Keep the A-M schema as the final data model.
- Extract decision-critical subsets first:
  - species/cell type/stage,
  - serum-free and animal-component-free status,
  - component identity,
  - dose/range,
  - endpoint,
  - quote and location.
- Run small field-specific jobs and merge them, rather than asking one model for
  all A-M fields at once.

### 2.4 PDF parsing should be upgraded before prompt tuning

GROBID and S2ORC demonstrate the value of structured paper objects: sections,
references, tables, captions, and citation links. CultivateAgent currently has a
PDF/text ingestion path, but reliable extraction from medium papers should move
toward a local structured-paper representation.

Project implication:

- Add an optional structured-document layer:
  - section title,
  - paragraph ID,
  - text,
  - table ID and caption,
  - figure caption,
  - source page where available.
- Use GROBID as an optional backend when available. CultivateAgent now has a
  no-dependency parser for GROBID TEI XML, JATS/Open Access article XML, and an
  optional standard library REST client for GROBID's `processFulltextDocument`
  service. It saves returned TEI to `fulltext.xml`, auto-detects JATS when
  legally obtained `fulltext.xml` files come from Europe PMC or similar sources,
  and preserves the PyMuPDF/plain-text fallback when no structured XML is
  available.
- Preserve the current PyMuPDF/plain-text fallback.

### 2.5 LLM document pipelines should be modular and operator-evaluated

DocETL-style systems treat document processing as schema-bound operators that
can be rewritten and evaluated. This maps well to CultivateAgent because each
field group can become an operator with its own prompts, coverage, and
grounding metrics.

Project implication:

- Split extraction into operators:
  - `identify_context`,
  - `extract_medium_components`,
  - `extract_dose_ranges`,
  - `extract_endpoints`,
  - `verify_quotes`,
  - `merge_records`.
- Track coverage and errors per operator.
- Do not treat "LLM returned JSON" as success unless field coverage and quote
  grounding pass.

### 2.6 Biology-specific benchmarks matter

LAB-Bench is a reminder that generic LLM quality is not enough. CultivateAgent
needs biology-specific evaluation for paper details, figures, tables, protocols,
and literature retrieval.

Project implication:

- Add local eval tasks around the bovine P1 corpus:
  - formulation table QA,
  - dose-range extraction,
  - endpoint identification,
  - table/caption evidence,
  - contradiction checks between papers.

### 2.7 Optimization upgrades are useful later, but not the present blocker

TuRBO, SCBO, JES, and DPP-based batch diversity remain strong candidates for
future optimizer upgrades. They should not be prioritized before extraction and
human review because the current failure is upstream.

Project implication:

- Keep qLogNEHVI as the production-style near-term backend.
- Revisit SCBO after cost, animal-origin, osmolality, and supplier constraints
  become structured fields.
- Revisit TuRBO after the search space grows beyond the current 4-6 variable
  classes.
- Revisit DPP batch diversity once generated wet-lab batches risk near
  duplicates.

## 3. Adopted Algorithm Roadmap

### R1. Structured paper objects

Add an optional representation:

```text
paper_structure.json
  metadata
  sections[]
    section_id
    title
    paragraphs[]
      paragraph_id
      text
      page
  tables[]
    table_id
    caption
    rows_or_csv_path
    page
  figures[]
    figure_id
    caption
    page
```

Acceptance criteria:

- Existing ingestion still works without GROBID. **Implemented for plain-text
  fallback.**
- Structured extraction can address passages by `paper_id:section_id:paragraph_id`.
  **Partially implemented through stable section/paragraph IDs.**
- Tables and captions can be routed to dose/endpoint extraction.
  **Partially implemented for GROBID TEI figure/table captions.**
- PDF-to-TEI generation is optional and does not add a hard dependency.
  **Implemented through `cultivate ingest --grobid-tei`, which calls a running
  GROBID service and writes `fulltext.xml`.**

### R2. Section-routed extraction

Use field-to-section routing:

| Field group | Preferred sections |
|---|---|
| cell source/type/stage | abstract, methods, cell culture |
| medium components | methods, media formulation, supplements, tables |
| doses/ranges | methods, tables, supplementary tables |
| endpoints | results, methods, figures, captions |
| cost/safety | discussion, supplementary cost tables |

Acceptance criteria:

- Extractor reports which sections were searched. **Implemented for structured
  paper section routing metadata.**
- Missing fields are recorded as missing, not inferred.
- Every populated decision-critical field has at least one quote.

### R3. Operator-level extraction

Replace one broad prompt with narrower operators for P1 core papers:

1. context operator;
2. medium component operator;
3. dose/range operator;
4. endpoint operator;
5. quote verification operator;
6. merge/adjudication operator.

Acceptance criteria:

- Each operator reports coverage, failures, and grounding.
- Operators can be rerun independently.
- Human review queue can point to operator outputs.

### R4. Scientific RAG support

Use retrieval before extraction:

- BM25 and embedding retrieval over structured passages.
- Metadata-aware ranking using paper title, year, source type, species, and
  cell type.
- Evidence cluster IDs for human review.

Acceptance criteria:

- Each extraction result links to the retrieved passage cluster.
- BM25/embedding disagreement is logged.
- Human reviewers can inspect the source passage without reading the whole
  paper.

### R5. Evaluation before wet-lab design

Before candidate formulation generation:

- Run extraction evaluation on P1 full-text records.
- Require coverage and grounding gates.
- Run deterministic evidence audit on extracted `EvidenceItem` records.
- Run a small human-adjudicated benchmark.

Acceptance criteria:

- S3 extraction reliability passes.
- `cultivate evidence-audit` is not `NO-GO` for the target outcome.
- S4 human review passes for all non-exploratory first-round variables.
- No wet-lab design packet is generated before S3/S4 pass.

Implementation now available:

- `cultivate evidence-audit --outcome proliferation --out docs/EVIDENCE_AUDIT_PROLIFERATION.md`.
- `cultivate review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md`.
- The audit adapts GRADE-style certainty concerns (indirectness, imprecision,
  inconsistency), PRISMA-style traceability, and NIST AI RMF-style measurement
  and risk documentation into a conservative wet-lab entry guardrail.
- The review packet follows ASReview/SWIFT-Review/RobotReviewer principles:
  prioritize and surface traceable source locations while leaving adjudication
  to human reviewers.
- The adjudication worksheet follows the same human-in-control rule: AI may
  prefill task metadata and locators, but the `decision`, `selected_range`, and
  evidence interpretation fields remain human-entered and validator-checked.
- The adjudication export is deliberately narrow: it copies only valid
  human-supported or partial rows into `bovine_evidence_table.tsv`. It does not
  convert literature outcomes into BO training labels.
- The extraction-readiness preflight follows DocETL/PaperMage-style pipeline
  decomposition: before live LLM calls, it checks whether local full text can
  route the `context`, `medium`, `dose`, `endpoints`, and `findings` operators.
  It distinguishes direct section-routed readiness from full-text fallback.
- The current proliferation audit is `NO-GO`: 145 local extracted effect items
  across 40 papers produced 4 AI-review candidates, but all are direction-only
  and 16/16 critical human-review tasks remain open.
- The current H001-H016 packet has local full-text locators for 14/16 critical
  tasks; the missing 2 tasks map to R024 and need institutional or
  human-provided main full text.
- The current H001-H016 extraction-readiness preflight has 14 direct
  section-routed tasks and 0 fallback-ready tasks after adding JATS section and
  `table-wrap` parsing for R023/H014.
- DeepSeek can be used through the OpenAI-compatible client for low-cost
  supervised extraction trials. New runs should use current DeepSeek model names
  (`deepseek-v4-flash` or `deepseek-v4-pro`) rather than the legacy
  `deepseek-chat` compatibility name, and any outputs still require quote
  grounding plus human review.
- The latest H014 DeepSeek-compatible pilot failed at provider authentication
  with the current environment key, so it produced no extraction evidence. The
  CLI now treats total operator `call_error` as a failed extraction and avoids
  writing empty records.

## 4. Explicit Non-Adoptions

These are not adopted now:

- A production web UI. The current deliverable is CLI plus traceable files.
- Fully autonomous wet-lab agents. Human gates remain mandatory.
- Fine-tuning a small IE model. This may become useful after enough adjudicated
  examples exist; it is premature now.
- Treating literature outcomes as training labels for BO. Literature defines
  the search space; wet-lab measurements provide objective values.
- Optimizer upgrades before extraction reliability. Upstream evidence is the
  bottleneck.

## 5. Immediate Implementation Tasks

1. Run optional GROBID service/client invocation on remaining P1 corpus PDFs
   when a service is available, or add legally obtained JATS/Open Access XML as
   `fulltext.xml` when that source is available.
2. Use `cultivate extraction-readiness` before live operator extraction, then
   use `cultivate extract --ids ... --mode operators` for a small targeted pilot
   before scaling to the full H001-H014 ready set.
3. Re-run `cultivate review-packet` after each full-text acquisition pass.
4. Fill `data/literature/bovine_adjudication_H001_H014.tsv` with human
   adjudication and validate it with `cultivate adjudication-validate`.
5. Export valid human-supported or partial rows with `cultivate adjudication-export`.
6. Re-run `cultivate evidence-audit` after each updated extraction/effect export.
7. Build section-routed extraction operators for medium components, dose ranges,
   endpoints, and quotes.
8. Update the evaluation script to report operator-level coverage and grounding.
9. Connect operator outputs to `bovine_human_review_queue.tsv`.

## 6. Human-Only Or Blocked Items

These require human or external action and should be recorded, then skipped if
not available:

- Access to paywalled PDFs or supplements.
- Gemini/Google credentials.
- OpenAI quota restoration.
- Wet-lab cell source, passage limits, assay plan, and reagent availability.
- Final approval of which evidence is acceptable for wet-lab design.

## 7. Reviewed Sources

The source registry in `data/literature/ai_for_science_method_sources.tsv`
contains the reviewed AI-for-science, scientific RAG, scientific IE, document
parsing, document ETL, and optimization sources used for this roadmap.

Key sources include:

- A-Lab: autonomous lab structure and active-learning loop.
- Coscientist and ChemCrow: tool-augmented scientific agents.
- PaperQA2 and OpenScholar: full-text, citation-backed scientific RAG.
- Dagdelen et al. and Shamsabadi et al.: structured scientific IE.
- GROBID, JATS/Europe PMC, and S2ORC: structured scientific document parsing.
  GROBID TEI and JATS XML parsing are now supported for title, abstract, body
  sections, table captions, and figure captions. GROBID service documentation
  supports the optional PDF-to-TEI ingestion client.
- DocETL: modular LLM document processing.
- GRADE, PRISMA, and NIST AI RMF: evidence-to-action gates, traceable review
  records, and AI risk documentation before wet-lab decisions.
- ASReview, SWIFT-Review, and RobotReviewer: transparent human-in-the-loop
  review support and source-location surfacing without replacing reviewers.
- TuRBO, SCBO, JES, and DPP-BBO: later optimization roadmap candidates.
