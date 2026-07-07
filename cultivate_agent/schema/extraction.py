"""The CultivateAgent extraction schema (blocks A-M).

This is a faithful, typed rendering of the schema designed in the project
record. Each block is a Pydantic model; field descriptions carry the record's
"how to interpret / fill" guidance so they can be surfaced verbatim to the LLM
(see :func:`schema_for_prompt`).

Conventions
-----------
* All fields are optional and default to ``None``. The extractor fills an
  explicit null code (``NR`` / ``NA`` / ``UNC``) rather than leaving blanks,
  and may prefix inferred values with ``INF:``.
* Single-value controlled fields are validated against
  :data:`CONTROLLED_VOCAB` (leniently: unknown values are kept but flagged, and
  null codes / inferences always pass). The same registry generates the
  "choose one of ..." hints in the prompt, so the model and the schema can
  never drift apart.
* List fields hold free strings joined by the caller with ``"; "`` when a flat
  representation is needed (matches the record's "separate with '; '" rule).
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .evidence import Evidence, NullCode, is_inference

# --------------------------------------------------------------------------- #
# Controlled vocabularies. Keyed by (globally unique) field name.             #
# Null codes NR/NA/UNC and any ``INF:`` value are always additionally allowed. #
# --------------------------------------------------------------------------- #
CONTROLLED_VOCAB: Dict[str, List[str]] = {
    "triage_category": ["A", "B", "C"],
    "article_type": ["article", "review", "methods", "analysis", "perspective", "dataset", "other"],
    "main_track": [
        "cell", "medium", "scaffold", "bioprocess",
        "structured_tissue", "quality_characterization", "systems_review",
    ],
    "target_product_type": ["muscle", "fat", "muscle-fat hybrid", "seafood", "general/platform"],
    "is_core_for_review": ["yes", "no", "borderline"],
    "is_core_for_modeling": ["yes", "no", "borderline"],
    "primary_or_cell_line": ["primary", "cell line", "mixed", "unclear"],
    "immortalization_status": ["primary mortal", "immortalized", "conditionally immortalized", "unclear"],
    "serum_usage": ["yes", "no", "reduced", "stage-specific", "unclear"],
    "serum_free_status": [
        "serum-free", "xeno-free", "chemically defined",
        "not serum-free", "partially serum-free", "unclear",
    ],
    "scaffold_used": ["yes", "no", "microcarrier only", "native tissue/ECM only", "unclear"],
    "material_origin": ["animal", "plant", "fungal", "synthetic", "hybrid"],
    "edibility_status": ["edible", "partially edible", "not edible", "unclear"],
    "culture_format": ["2D", "3D", "suspension", "microcarrier", "printed construct"],
    "process_mode": ["batch", "fed-batch", "perfusion", "conceptual only", "other"],
    "has_extractable_quant_data": ["yes", "no", "partial"],
    "modeling_value_score": ["low", "medium", "high"],
    "does_it_represent_a_major_direction": ["yes", "no", "partly"],
    "is_it_incremental_or_direction_setting": ["incremental", "direction-setting", "bridge/transition", "unclear"],
    "candidate_for_scoring_framework": ["yes", "no", "maybe"],
    "representative_paper_flag": ["yes", "no", "backup exemplar"],
    "review_usefulness": ["low", "medium", "high"],
    "research_usefulness": ["low", "medium", "high"],
    "data_extraction_usefulness": ["low", "medium", "high"],
    "recommended_action": [
        "must_extract_now", "keep_for_review_synthesis", "keep_for_later", "peripheral",
    ],
}


def normalize_controlled(field: str, value: Optional[str]) -> Optional[str]:
    """Leniently map ``value`` onto the controlled vocab for ``field``.

    Returns the canonical spelling on a case-insensitive match; passes through
    null codes and ``INF:`` inferences unchanged; otherwise returns the value
    as-is (never raises — out-of-vocab values are the extractor's problem to
    flag, not a reason to drop data).
    """
    if value is None:
        return None
    v = value.strip()
    if not v or NullCode.is_code(v) or is_inference(v):
        return v
    vocab = CONTROLLED_VOCAB.get(field)
    if not vocab:
        return v
    lowered = {opt.lower(): opt for opt in vocab}
    return lowered.get(v.lower(), v)


class SchemaBlock(BaseModel):
    """Base for all A-M blocks: lenient controlled-vocab normalization."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    @model_validator(mode="after")
    def _normalize_controlled_fields(self):  # noqa: D401
        for name in type(self).model_fields:
            if name in CONTROLLED_VOCAB:
                val = getattr(self, name)
                if isinstance(val, str):
                    object.__setattr__(self, name, normalize_controlled(name, val))
        return self


# --------------------------------------------------------------------------- #
# A. Basic info                                                               #
# --------------------------------------------------------------------------- #
class BasicInfo(SchemaBlock):
    paper_id: Optional[str] = Field(None, description="Stable local ID for the paper.")
    title: Optional[str] = Field(None, description="Official paper title exactly as published.")
    authors: Optional[List[str]] = Field(None, description="Author list; at minimum first + corresponding author.")
    year: Optional[int] = Field(None, description="Publication year.")
    journal: Optional[str] = Field(None, description="Journal or source title.")
    doi: Optional[str] = Field(None, description="DOI in standard form; use NR rather than inventing one.")
    article_type: Optional[str] = Field(
        None, description="Best-fit type. Choose 'article' only for original experimental data."
    )


# --------------------------------------------------------------------------- #
# B. Fast triage                                                              #
# --------------------------------------------------------------------------- #
class FastTriage(SchemaBlock):
    main_track: Optional[str] = Field(None, description="Dominant contribution lane (choose one).")
    subtrack: Optional[str] = Field(None, description="More specific placement, e.g. 'serum-free medium', 'perfusion'.")
    species: Optional[List[str]] = Field(None, description="Species discussed/tested (bovine, porcine, chicken, fish...).")
    target_product_type: Optional[str] = Field(None, description="Product direction the work mainly supports.")
    is_core_for_review: Optional[str] = Field(None, description="Central enough to cite/discuss in the main review argument?")
    is_core_for_modeling: Optional[str] = Field(None, description="Likely to yield structured variables / quantitative relations?")
    overall_priority_note: Optional[str] = Field(None, description="Dense triage note: why it matters and what to do next.")


# --------------------------------------------------------------------------- #
# C. Research objective                                                       #
# --------------------------------------------------------------------------- #
class ResearchObjective(SchemaBlock):
    problem_statement: Optional[str] = Field(None, description="Practical/scientific problem framed by the paper (1-3 dense sentences).")
    technical_bottleneck_targeted: Optional[List[str]] = Field(
        None, description="Specific bottlenecks explicitly targeted (low proliferation, high media cost, oxygen limitation...)."
    )
    proposed_solution: Optional[str] = Field(None, description="Core solution route the authors built/compared/optimized.")
    claimed_novelty: Optional[str] = Field(None, description="What the authors say is new (keep author claims even if incremental).")


# --------------------------------------------------------------------------- #
# D. Cell information                                                         #
# --------------------------------------------------------------------------- #
class CellInfo(SchemaBlock):
    cell_source: Optional[str] = Field(None, description="Immediate source: biopsy, slaughterhouse tissue, commercial line, iPSC...")
    cell_type: Optional[List[str]] = Field(None, description="Cell identity: satellite cells, myoblasts, FAPs, adipocytes, iPSC...")
    primary_or_cell_line: Optional[str] = Field(None, description="Primary, established line, mixture, or unclear.")
    immortalization_status: Optional[str] = Field(None, description="Absent / present / conditional / unclear.")
    tissue_of_origin: Optional[str] = Field(None, description="Anatomical source: skeletal muscle, subcutaneous adipose, fin...")
    species_detail: Optional[str] = Field(None, description="Granular taxonomic / breed / source detail if relevant.")
    passage_info: Optional[str] = Field(None, description="Passage number, doubling history, senescence note, expansion window.")
    cell_isolation_method: Optional[str] = Field(None, description="Isolation/enrichment: enzymatic digestion, pre-plating, FACS, MACS, explant.")
    expansion_conditions_summary: Optional[str] = Field(None, description="Dense description of proliferation-stage culture (medium, substrate, serum, O2, timing).")
    differentiation_conditions_summary: Optional[str] = Field(None, description="Dense description of myogenic/adipogenic/maturation conditions and triggers.")


# --------------------------------------------------------------------------- #
# E. Medium information  (the actionable core of the project)                 #
# --------------------------------------------------------------------------- #
class MediumInfo(SchemaBlock):
    basal_medium: Optional[List[str]] = Field(None, description="Base platform(s): DMEM, DMEM/F12, Ham's F-10, custom defined base.")
    serum_usage: Optional[str] = Field(None, description="Serum used at any stage? If stage-specific, say where and at what level.")
    serum_free_status: Optional[str] = Field(None, description="Strongest label the data justify; do not overclaim 'chemically defined'.")
    growth_factors: Optional[List[str]] = Field(None, description="Named protein supplements: FGF2, IGF-1, insulin, transferrin, TGF-beta inhibitors...")
    small_molecules: Optional[List[str]] = Field(None, description="Non-protein signaling/differentiation additives.")
    hydrolysates_or_extracts: Optional[List[str]] = Field(None, description="Yeast extract, plant/algal hydrolysates, peptones...")
    conditioned_medium_or_recycling: Optional[str] = Field(None, description="Conditioned-medium reuse, spent-medium recycling, circular-medium strategy.")
    medium_optimization_strategy: Optional[str] = Field(None, description="How the paper optimizes medium: screening, DoE, replacement, cost trimming...")
    cost_reduction_relevance: Optional[str] = Field(None, description="Why this medium work matters (or not) for practical cost reduction.")


# --------------------------------------------------------------------------- #
# F. Scaffold and carrier information                                         #
# --------------------------------------------------------------------------- #
class ScaffoldInfo(SchemaBlock):
    scaffold_used: Optional[str] = Field(None, description="Whether an explicit scaffold/carrier system is used and in what sense.")
    material_type: Optional[List[str]] = Field(None, description="Materials: alginate, gelatin, collagen, cellulose, chitosan, dECM, soy protein...")
    material_origin: Optional[str] = Field(None, description="Broad origin class; use 'hybrid' when combined.")
    edibility_status: Optional[str] = Field(None, description="Intended to remain in food, or clearly research-only.")
    fabrication_method: Optional[List[str]] = Field(None, description="Casting, freeze-drying, electrospinning, 3D printing, extrusion, crosslinking, decellularization...")
    structure_features: Optional[List[str]] = Field(None, description="Porous, aligned, anisotropic, fibrous, layered, perfusable, microchanneled...")
    mechanical_or_microstructure_features: Optional[str] = Field(None, description="Mechanical props, pore size, fiber diameter, swelling, rheology...")
    microcarrier_usage: Optional[str] = Field(None, description="Microcarrier type, material, detachability, edibility, stage of use.")
    scaffold_role: Optional[List[str]] = Field(None, description="Expansion support, alignment cue, texture building, mass-transfer aid, edible final matrix...")


# --------------------------------------------------------------------------- #
# G. Process information                                                      #
# --------------------------------------------------------------------------- #
class ProcessInfo(SchemaBlock):
    culture_format: Optional[str] = Field(None, description="Dominant process format for the key result.")
    bioreactor_type: Optional[str] = Field(None, description="Spinner flask, stirred tank, rocking bag, hollow fiber, perfusion chamber, or none.")
    process_mode: Optional[str] = Field(None, description="How media/culture flow are operated.")
    scale_level: Optional[str] = Field(None, description="Well plate, flask, mL bioreactor, liter scale, pilot concept...")
    process_control_variables: Optional[List[str]] = Field(None, description="pH, DO, agitation, shear, flow rate, seeding density, feed schedule...")
    scale_up_relevance: Optional[str] = Field(None, description="What genuinely informs scale-up vs. rhetorical mention.")
    manufacturing_relevance_note: Optional[str] = Field(None, description="Manufacturable, fragile, expensive, or conceptual only?")


# --------------------------------------------------------------------------- #
# H. Tissue information                                                       #
# --------------------------------------------------------------------------- #
class TissueInfo(SchemaBlock):
    structured_product_goal: Optional[str] = Field(None, description="Fiber bundle, steak-like tissue, fat inclusion, layered construct...")
    muscle_formation_strategy: Optional[str] = Field(None, description="Differentiation, alignment cues, fusion support, strain, electrical cues...")
    fat_integration_strategy: Optional[str] = Field(None, description="How fat is introduced, matured, co-cultured, layered, blended.")
    co_culture_or_assembly_strategy: Optional[str] = Field(None, description="How multiple cell types / tissue parts are assembled.")
    alignment_or_texture_strategy: Optional[str] = Field(None, description="Grooves, fibers, strain, printing path, molding...")
    post_processing_if_any: Optional[str] = Field(None, description="Harvesting, compression, cooking tests, blending, seasoning, enzymatic treatment...")


# --------------------------------------------------------------------------- #
# I. Measurements information                                                 #
# --------------------------------------------------------------------------- #
class Measurements(SchemaBlock):
    main_readouts: Optional[List[str]] = Field(None, description="Top-level measurements the paper revolves around.")
    proliferation_metrics: Optional[List[str]] = Field(None, description="Cell count, DNA, metabolic assay, doubling time, EdU/Ki67, VCD...")
    differentiation_metrics: Optional[List[str]] = Field(None, description="Fusion index, adipogenic staining, marker genes, differentiation rate...")
    maturation_metrics: Optional[List[str]] = Field(None, description="Late markers, sarcomere organization, contractility, lipid maturation...")
    scaffold_performance_metrics: Optional[List[str]] = Field(None, description="Mechanical tests, pore analysis, degradation, attachment, infiltration depth...")
    texture_or_quality_metrics: Optional[List[str]] = Field(None, description="TPA, chewiness, color, WHC, sensory proxies, flavor-relevant outputs...")
    omics_or_systems_data: Optional[List[str]] = Field(None, description="Transcriptomics, proteomics, metabolomics, systems modeling...")
    food_relevant_metrics: Optional[List[str]] = Field(None, description="Edibility, safety, composition, nutrition, sensory, consumer translation.")


# --------------------------------------------------------------------------- #
# J. Quantitative data for modeling                                           #
# --------------------------------------------------------------------------- #
class QuantData(SchemaBlock):
    has_extractable_quant_data: Optional[str] = Field(None, description="Numbers that can realistically be tabulated for modeling?")
    extractable_variables: Optional[List[str]] = Field(None, description="growth rate, stiffness, pore size, serum %, GF concentration, lipid content...")
    key_numeric_results: Optional[List[str]] = Field(None, description="Most important numeric findings, with comparison context. Preserve original units.")
    units_reported: Optional[List[str]] = Field(None, description="Units exactly as reported in the paper.")
    experimental_comparison_groups: Optional[str] = Field(None, description="Control vs treatment logic, benchmark groups, dose/time groups.")
    sample_size_or_replicate_info: Optional[str] = Field(None, description="n, biological vs technical replicates, independent experiments, or 'vague'.")
    statistical_strength_note: Optional[str] = Field(None, description="Solid / minimal / weak / unclear judgment.")
    modeling_value_score: Optional[str] = Field(None, description="Overall utility for later quantitative modeling.")


# --------------------------------------------------------------------------- #
# K. Main findings and limitations                                            #
# --------------------------------------------------------------------------- #
class FindingsLimitations(SchemaBlock):
    core_findings: Optional[str] = Field(None, description="Dense, evidence-based takeaway.")
    authors_reported_limitations: Optional[str] = Field(None, description="Limitations explicitly acknowledged by the authors.")
    hidden_or_practical_limitations: Optional[str] = Field(None, description="Practical weaknesses you infer from design/data/scale/materials/missing controls.")
    scalability_constraints: Optional[str] = Field(None, description="Specific constraints on scale-up / industrial deployment.")
    cost_constraints: Optional[str] = Field(None, description="Where cost likely bites: medium, GFs, fabrication complexity, throughput, yield.")
    food_translation_constraints: Optional[str] = Field(None, description="Where translation to food is blocked: non-edibility, safety, format, missing quality data.")


# --------------------------------------------------------------------------- #
# L. Review synthesis fields                                                  #
# --------------------------------------------------------------------------- #
class ReviewSynthesis(SchemaBlock):
    best_fit_big_category: Optional[str] = Field(None, description="Top-level review chapter / domain bucket.")
    best_fit_small_category: Optional[str] = Field(None, description="Subsection placement inside the big category.")
    why_it_belongs_here: Optional[str] = Field(None, description="Short argument for the placement (useful when papers overlap themes).")
    does_it_represent_a_major_direction: Optional[str] = Field(None, description="Stands for a major line of work vs. isolated case.")
    is_it_incremental_or_direction_setting: Optional[str] = Field(None, description="Fine-tunes an existing lane vs. redirects the field.")
    candidate_for_scoring_framework: Optional[str] = Field(None, description="Should it enter a later scoring matrix / evidence framework?")
    representative_paper_flag: Optional[str] = Field(None, description="One you'd naturally cite as representative in the final review?")


# --------------------------------------------------------------------------- #
# M. Final judgment                                                           #
# --------------------------------------------------------------------------- #
class FinalJudgment(SchemaBlock):
    review_usefulness: Optional[str] = Field(None, description="Usefulness for the review narrative / evidence map.")
    research_usefulness: Optional[str] = Field(None, description="Usefulness for shaping your own future experiments/hypotheses.")
    data_extraction_usefulness: Optional[str] = Field(None, description="Usefulness specifically as a source of extractable structured info.")
    recommended_action: Optional[str] = Field(None, description="Workflow triage tag.")
    one_paragraph_reader_summary: Optional[str] = Field(None, description="One dense paragraph recovering the paper's value in ~20s.")


# Registry: block letter -> (model, human title). Order matters for prompts.
BLOCKS: Dict[str, tuple] = {
    "A": (BasicInfo, "Basic info"),
    "B": (FastTriage, "Fast triage"),
    "C": (ResearchObjective, "Research objective"),
    "D": (CellInfo, "Cell information"),
    "E": (MediumInfo, "Medium information"),
    "F": (ScaffoldInfo, "Scaffold and carrier information"),
    "G": (ProcessInfo, "Process information"),
    "H": (TissueInfo, "Tissue information"),
    "I": (Measurements, "Measurements information"),
    "J": (QuantData, "Quantitative data for modeling"),
    "K": (FindingsLimitations, "Main findings and limitations"),
    "L": (ReviewSynthesis, "Review synthesis fields"),
    "M": (FinalJudgment, "Final judgment"),
}

_BLOCK_ATTR = {
    "A": "basic_info", "B": "fast_triage", "C": "research_objective",
    "D": "cell_info", "E": "medium_info", "F": "scaffold_info",
    "G": "process_info", "H": "tissue_info", "I": "measurements",
    "J": "quant_data", "K": "findings_limitations", "L": "review_synthesis",
    "M": "final_judgment",
}


class PaperExtraction(BaseModel):
    """Full structured record for one paper: all blocks + provenance."""

    model_config = ConfigDict(extra="ignore")

    paper_id: str
    triage_category: Optional[str] = Field(None, description="A / B / C relevance tier.")

    basic_info: BasicInfo = Field(default_factory=BasicInfo)
    fast_triage: FastTriage = Field(default_factory=FastTriage)
    research_objective: ResearchObjective = Field(default_factory=ResearchObjective)
    cell_info: CellInfo = Field(default_factory=CellInfo)
    medium_info: MediumInfo = Field(default_factory=MediumInfo)
    scaffold_info: ScaffoldInfo = Field(default_factory=ScaffoldInfo)
    process_info: ProcessInfo = Field(default_factory=ProcessInfo)
    tissue_info: TissueInfo = Field(default_factory=TissueInfo)
    measurements: Measurements = Field(default_factory=Measurements)
    quant_data: QuantData = Field(default_factory=QuantData)
    findings_limitations: FindingsLimitations = Field(default_factory=FindingsLimitations)
    review_synthesis: ReviewSynthesis = Field(default_factory=ReviewSynthesis)
    final_judgment: FinalJudgment = Field(default_factory=FinalJudgment)

    # Provenance: "<block>.<field>" -> Evidence.
    evidence: Dict[str, Evidence] = Field(default_factory=dict)

    # Extraction metadata (which model produced this, when, cost proxy).
    extraction_meta: Dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _propagate_triage(self):
        if self.triage_category:
            self.triage_category = normalize_controlled("triage_category", self.triage_category)
        return self

    def get_block(self, letter: str) -> SchemaBlock:
        return getattr(self, _BLOCK_ATTR[letter.upper()])

    def set_block(self, letter: str, block: SchemaBlock) -> None:
        setattr(self, _BLOCK_ATTR[letter.upper()], block)


def block_model(letter: str):
    """Return the Pydantic model class for a schema block letter."""
    return BLOCKS[letter.upper()][0]


def schema_for_prompt(blocks: List[str]) -> str:
    """Render a compact, LLM-readable field guide for the requested blocks.

    Used by the extractor so the prompt and the schema are generated from the
    same source of truth. Output lists, per field: name, type, allowed values
    (for controlled fields), and the interpretation guidance.
    """
    lines: List[str] = []
    for letter in blocks:
        letter = letter.upper()
        if letter not in BLOCKS:
            continue
        model, title = BLOCKS[letter]
        lines.append(f"### Block {letter}. {title}")
        for name, info in model.model_fields.items():
            ann = info.annotation
            is_list = "List" in str(ann)
            base = "list[str]" if is_list else ("int" if "int" in str(ann) else "str")
            allowed = CONTROLLED_VOCAB.get(name)
            allowed_str = f" | choose one of: {allowed}" if allowed else ""
            desc = info.description or ""
            lines.append(f"- {name} ({base}){allowed_str}: {desc}")
        lines.append("")
    return "\n".join(lines)
