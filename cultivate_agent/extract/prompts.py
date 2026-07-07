"""Domain-specific prompts for triage and schema extraction.

Structured after **ReactionSeek's four-part prompt architecture** (Li et al.,
*Nat. Commun.* 2026, Methods), which they in turn adapted from MOF data-mining
work. The paper reports F1 > 0.98 from this design with only a handful of
few-shot examples and *no fine-tuning*. The four parts are:

1. **Task description** — global objective + explicit constraints, including
   *negative constraints* that suppress hallucination ("use only the provided
   text").
2. **Task requirements** — exact fields + strict output format. ReactionSeek
   notes this block should be *repeated near the end* to counter "memory decay"
   on long inputs, so we re-state a terse format reminder after the paper text.
3. **Processing suggestions** — domain-expert heuristics in natural language.
4. **Processing cases** — few-shot input→verified-output pairs.

CultivateAgent adds one thing ReactionSeek did not: a mandatory verbatim
`evidence` quote per value, verified downstream against the source.
"""

from __future__ import annotations

from typing import List

from ..schema.extraction import schema_for_prompt
from ..schema.paper import PaperRef

# --------------------------------------------------------------------------- #
# Part 1 — Task description (with anti-hallucination negative constraints)     #
# --------------------------------------------------------------------------- #
TASK_DESCRIPTION = """
TASK DESCRIPTION
You extract structured, evidence-grounded records from a cultivated-meat
(cell-cultured meat) research paper into a fixed schema. Your output feeds a
knowledge base used for culture-medium optimization, so correctness and
traceability matter more than completeness.

Hard constraints (negative constraints included to prevent hallucination):
- Use ONLY the provided text. Do NOT use outside knowledge to fill values.
- Do NOT invent DOIs, numbers, cell lines, or component names. If it is not in
  the text, it is NR (not reported).
- False positives are worse than false negatives: when unsure, use a null code.
- Copy quotes VERBATIM; never paraphrase inside a `quote`.
""".strip()

# --------------------------------------------------------------------------- #
# Part 2 — Task requirements (grounding + null codes + output format)          #
# --------------------------------------------------------------------------- #
TASK_REQUIREMENTS = """
TASK REQUIREMENTS
1. GROUND EVERY VALUE with a verbatim `quote` that is an exact substring of the
   text. If you cannot find support, use a null code instead of guessing.
2. NULL CODES: "NR" (not reported), "NA" (not applicable), "UNC" (unclear).
3. INFERENCES: prefix inferred values with "INF:" and lower confidence.
4. PRESERVE original numbers and units exactly (e.g. "39 h", "0.8 mg/mL", "10% FBS").
5. SEPARATE claims from evidence: author novelty claims go in `claimed_novelty`.
6. CONTROLLED FIELDS: pick exactly one listed value (or a null code).
7. Output STRICT JSON only, no prose before or after.
""".strip()

_OUTPUT_FORMAT = """
OUTPUT FORMAT — a single JSON object with exactly two keys:
{
  "blocks":   { "<LETTER>": { "<field>": <value>, ... }, ... },
  "evidence": { "<LETTER>.<field>": {"quote": "<verbatim>", "location": "<e.g. Methods>",
                                     "confidence": "low|medium|high", "is_inference": false}, ... }
}
Provide an `evidence` entry for every field whose value is not a null code.
""".strip()

# A short reminder re-stated AFTER the paper text (memory-decay mitigation).
_FORMAT_REMINDER = (
    "REMINDER: return ONLY the JSON object with keys `blocks` and `evidence`; "
    "every non-null value needs a verbatim `quote`; preserve original units; "
    "unsupported values must be NR/NA/UNC."
)

# --------------------------------------------------------------------------- #
# Part 3 — Processing suggestions (domain-expert heuristics)                   #
# --------------------------------------------------------------------------- #
PROCESSING_SUGGESTIONS = """
PROCESSING SUGGESTIONS (domain heuristics)
- Medium (block E) is the priority. Distinguish EXPANSION vs DIFFERENTIATION
  stages: serum level, growth factors, and small molecules often differ by stage.
- "10% FBS", "serum-free", "chemically defined", "xeno-free" are NOT synonyms;
  use the strongest label the data justify, no stronger.
- Growth factors (FGF2/bFGF, IGF-1, insulin, transferrin) and recombinant
  proteins usually dominate cost; capture concentrations when reported.
- Basal media appear as trade names (DMEM, DMEM/F12, Ham's F-10) or as B8/Beefy-9
  style formulations; record the base separately from supplements.
- Quantitative results (block J) usually live in tables and figure captions;
  keep the comparison group (control vs treatment) with each number.
- Species and cell identity (bovine/porcine/chicken/fish; satellite cells,
  myoblasts, FAPs, iPSC) frequently sit in sub-headings — read them.
""".strip()

# --------------------------------------------------------------------------- #
# Part 4 — Processing cases (few-shot)                                         #
# --------------------------------------------------------------------------- #
PROCESSING_CASES = """
PROCESSING CASE (few-shot example)
Text (excerpt):
'''We adapted the serum-free B8 medium for bovine satellite cells by adding a
single component, recombinant albumin, yielding "Beefy-9". Beefy-9 supported
proliferation over seven passages with an average doubling time of ~39 h while
maintaining myogenicity (MYOD and MYOG expression). Basal medium was DMEM/F12.'''

Expected JSON:
{
  "blocks": {
    "E": {"basal_medium": ["DMEM/F12"], "serum_usage": "no", "serum_free_status": "serum-free",
          "growth_factors": ["recombinant albumin"],
          "medium_optimization_strategy": "Single-component addition (recombinant albumin) to adapt B8 into Beefy-9."}
  },
  "evidence": {
    "E.serum_free_status": {"quote": "serum-free B8 medium", "location": "Methods", "confidence": "high", "is_inference": false},
    "E.basal_medium": {"quote": "Basal medium was DMEM/F12", "location": "Methods", "confidence": "high", "is_inference": false},
    "E.growth_factors": {"quote": "adding a single component, recombinant albumin", "location": "Methods", "confidence": "high", "is_inference": false}
  }
}
""".strip()


SYSTEM_EXTRACTION = (
    "You are a meticulous scientific data-extraction assistant for a cultivated-"
    "meat knowledge base. You are conservative: you would rather mark a value NR "
    "than hallucinate it.\n\n" + TASK_DESCRIPTION + "\n\n" + TASK_REQUIREMENTS
)


def build_extraction_prompt(ref: PaperRef, text: str, blocks: List[str]) -> str:
    """Assemble the four-part user prompt for the requested schema blocks."""
    field_guide = schema_for_prompt(blocks)
    header = (
        f"PAPER: {ref.title or ref.paper_id}\n"
        f"AUTHORS: {', '.join(ref.authors[:6])}{' et al.' if len(ref.authors) > 6 else ''}\n"
        f"YEAR: {ref.year or 'NR'}   JOURNAL: {ref.journal or 'NR'}   DOI: {ref.doi or 'NR'}\n"
    )
    return f"""{header}
{PROCESSING_SUGGESTIONS}

SCHEMA FIELDS TO EXTRACT:
{field_guide}

{_OUTPUT_FORMAT}

{PROCESSING_CASES}

TEXT TO EXTRACT FROM:
'''{text}'''

{_FORMAT_REMINDER}
"""


# --------------------------------------------------------------------------- #
# Triage (A / B / C relevance tiering)                                        #
# --------------------------------------------------------------------------- #
SYSTEM_TRIAGE = (
    "You are triaging papers for a cultivated-meat, culture-medium-centered "
    "review and knowledge base. You assign a relevance tier and a short, "
    "evidence-backed rationale. Be strict: representativeness and extractable "
    "value matter more than mere topical overlap. Use only the provided text."
)

_TRIAGE_DEFINITIONS = """
Tier definitions (from the project's screening protocol):
- A = core literature DIRECTLY relevant to the main line of cultivated-meat
      technology, representative of the classification framework, and worth
      in-depth reading and information extraction.
- B = relevant and worth retaining, but SUPPLEMENTARY: lacks representativeness
      or extractable value; not in the core in-depth set.
- C = peripheral or only indirectly relevant (consumer perspectives, ethics,
      policy, market narratives, general extensions), limited help for the
      technological roadmap or extraction.

Because this project is MEDIUM-CENTERED, weight papers on culture medium, serum
reduction, growth factors, small molecules, and food-grade supplements toward A
when they carry extractable quantitative or mechanistic detail.
""".strip()


def build_triage_prompt(ref: PaperRef, text: str) -> str:
    """User prompt for A/B/C triage with a fast-triage (block B) summary."""
    abstract = ref.abstract or ""
    body = text[:8000]
    return f"""PAPER: {ref.title or ref.paper_id}
ABSTRACT: {abstract}

{_TRIAGE_DEFINITIONS}

Assess the paper below and return STRICT JSON:
{{
  "triage_category": "A|B|C",
  "rationale": "<one or two sentences>",
  "evidence_quote": "<verbatim span supporting the decision, or NR>",
  "main_track": "<cell|medium|scaffold|bioprocess|structured_tissue|quality_characterization|systems_review>",
  "target_product_type": "<muscle|fat|muscle-fat hybrid|seafood|general/platform>",
  "is_core_for_modeling": "yes|no|borderline"
}}

TEXT (excerpt):
'''{body}'''
"""
