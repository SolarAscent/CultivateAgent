# Claude → Codex work sync (results only)

Purpose: a short, result-level handoff so Codex knows what Claude landed and does not
duplicate it. Not a process log. Claude owns `normalize/`, `evidence/meta_analysis.py`,
and the synthesis side; Codex owns `ingest/`, `evidence/tables.py`, and extraction. The
frozen seam `numeric_effect_from_group_stats` is unchanged.

## Landed on main (code)

- `normalize/components.py`: strip leading dose prefixes ("5% FBS-PSFC" → "FBS-PSFC",
  "5 ng/mL bFGF" → FGF2) so dose variants pool; guarded against "2i"/"M199"/"18-crown-6".
  Raises k before scale-up.
- `evidence/meta_analysis.py`: the DL random-effects branch now also runs the direction
  conflict check, so ≥2 tier-1 items can no longer mask a split of direction-only studies
  (context_dependent stays honest). Magnitude still pooled from tier-1 only — no fake fusion.
- `evidence/effect_operator.py` (inference guards only): reject concentrations ("30% FBS")
  and dispersions ("2.2 ± 0.4-fold") as effect magnitudes; percentages need an explicit
  change word. Did not touch the seam or table path.
- End-to-end verified: JATS table → `numeric_effect_from_table_pointers` → tier-1 →
  `meta_analyze` produces a single_study/DL summary with CI. Both halves connect.

## DeepSeek delegation (my lane, low-risk, spot-checked — NOT adjudicated truth)

- **Corpus relevance triage (171 → 67 core)**: `data/literature/corpus_relevance_triage.tsv`
  (A/B/C + is_core, temp=0, per-row provenance, `quote_grounded` flag). Spot-check: all 9
  human-adjudication papers → A; C exclusions correct. Categories reliable; quotes ~26%
  verbatim (flagged). Use to focus extraction; not evidence.
- **Zotero 14k funnel (in progress)**: title/abstract relevance screen of the user's
  `CulturedMeat` export — 14,247 rows → 6,072 unique → relevance (yes/maybe/no) keeping the
  has_pdf flag. Goal: find missing core serum-free-expansion papers + build a targeted PDF
  acquisition list (only ~14% of refs have PDFs). Will land as
  `data/literature/zotero_relevance_screen.tsv` once spot-checked. First-pass funnel only.

## Norms in force for DeepSeek

Narrow batched tasks; temperature=0; key only from `.env`; per-row provenance; deterministic
checks; output to auditable TSVs, never the shared KB; pilot-before-scale; Claude spot-checks.
DeepSeek returns classifications/pointers, never fabricated numbers.

## Corpus (local, untracked — per-worktree)

- Zotero funnel outputs committed: `data/literature/zotero_relevance_screen.tsv` (6,072 unique
  → 275 yes / 741 maybe) and `data/literature/zotero_acquire_list.tsv` (236 relevant papers
  without a PDF — targeted download list).
- Ingested 10 genuinely-new relevant papers (serum-free / proliferation, muscle/satellite/stem
  across bovine/pig/chicken/fish) into the local `data/papers/` (171 → 181). These are local to
  the claude worktree; if the canonical corpus/manifest should include them, that is Codex's
  ingest lane — the source PDFs are in the user's Zotero storage (paths derivable from the CSV).

## Ontology + S4→S5 bridge (my lane, landed)

- **Ontology grown from DeepSeek mining (Claude-curated)**: +6 real components (IL-6, LIF,
  horse-serum, sodium-pyruvate, linoleic-acid, fetuin) + alias fixes (TGF-β, PDGF, DMEM,
  Ham's F-10, B8, sodium selenite, yeast extract); 15 orphan names now pool. Rejected all
  buffer/antibiotic/coating/category noise. Candidate queue: `data/literature/component_mining_candidates.tsv`.
- **S4→S5 bridge**: `evidence/adjudicated_loader.py` turns the adjudicated evidence table
  (`bovine_evidence_table.tsv`) into EvidenceItems → summaries → `EvidencePrior`. So a finished
  human review flows straight into search-space priors / the design recommender. New module;
  I did NOT touch `adjudication.py` or `evidence/__init__.py`.

## Recommendation for Codex (your adjudication schema)

The worksheet / `EVIDENCE_TABLE_COLUMNS` has no explicit **direction** field, so the bridge
must infer sign from `numeric_effect` (ratio metrics) or from `key_finding` polarity words, and
skips rows where neither is determinable. Consider adding an explicit `effect_direction`
column (increase / decrease / no-change) the human fills, so direction is recorded, not
inferred. Low-effort, and it removes the one fragile step in the S4→S5 path.
