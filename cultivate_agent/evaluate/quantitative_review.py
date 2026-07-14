"""Identity-bound, pointer-only dual review for quantitative PDF evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from ..schema.paper import slugify
from .gold_review import _cohen_kappa, _schema_sha256


FORMAT_VERSION = 1
SELECTOR_VERSION = "pdf-stat-block-v1"
LINKED_FIELDS = (
    "J.key_numeric_results",
    "J.experimental_comparison_groups",
    "J.sample_size_or_replicate_info",
)
DECISIONS = {"tier1_ready", "tier2_only", "reject", "not_recoverable"}
SOURCE_KINDS = {"prose", "caption", "figure", "table", "mixed"}
DISPERSION_TYPES = {"sd", "sem", "se", "ci", "other", "missing"}
REPLICATE_TYPES = {"biological", "technical", "mixed", "unclear", "not_applicable"}
SAMPLE_SIZE_STATUSES = {"exact_per_group", "exact_shared", "lower_bound", "missing", "unclear"}
SAME_COMPARISON = {"yes", "no", "unclear"}

BASE_COLUMNS = [
    "benchmark_version",
    "candidate_id",
    "record_id",
    "paper_id",
    "title",
    "doi",
    "pdf_path",
    "pdf_sha256",
    "pdf_page",
    "block_index",
    "bbox_points",
    "block_text_sha256",
    "signals",
    "linked_fields",
]
REVIEW_COLUMNS = [
    "decision",
    "source_kind",
    "treatment_label",
    "control_label",
    "outcome",
    "timepoint",
    "effect_pointer",
    "treatment_mean_pointer",
    "control_mean_pointer",
    "treatment_dispersion_pointer",
    "control_dispersion_pointer",
    "dispersion_type",
    "treatment_n_pointer",
    "control_n_pointer",
    "sample_size_status",
    "replicate_type",
    "same_comparison",
    "reviewer",
    "date",
    "notes",
]
COLUMNS = BASE_COLUMNS + REVIEW_COLUMNS

_EXPLICIT_DISPERSION_RE = re.compile(r"\d(?:[\d.,]*\d)?\s*(?:±|\+/-)\s*\d", re.I)
_NAMED_DISPERSION_VALUE_RE = re.compile(
    r"\b(?:SD|s\.d\.|SEM|s\.e\.m\.|SE|standard deviation|standard error)\s*=\s*\d",
    re.I,
)
_SAMPLE_SIZE_RE = re.compile(r"\bn\s*(?:=|>|≥)\s*\d", re.I)
_SD_RE = re.compile(r"\b(?:SD|s\.d\.|standard deviation)\b", re.I)
_SEM_RE = re.compile(r"\b(?:SEM|s\.e\.m\.|standard error)\b", re.I)
_OUTCOME_RE = re.compile(
    r"prolifer|growth|doubling|cell count|cell density|viab|fusion|differenti|myogenic",
    re.I,
)
_MEDIUM_RE = re.compile(r"medium|media|serum|FBS|B8|Beefy|VN40|lysate", re.I)
_FIGURE_RE = re.compile(r"^\s*(?:Fig(?:ure)?\.?|Extended Data Fig)", re.I)
_MEAN_RE = re.compile(r"\bmean\b|\baverage\b", re.I)
_ERROR_POLICY_RE = re.compile(r"error bars|graphical data", re.I)


@dataclass(frozen=True)
class QuantitativeValidation:
    rows: int
    expected_rows: int
    completed: int
    issues: list[str]

    @property
    def complete(self) -> bool:
        return not self.issues and self.rows == self.expected_rows and self.completed == self.rows


@dataclass(frozen=True)
class QuantitativeComparison:
    rows: int
    reviewer_a_completed: int
    reviewer_b_completed: int
    issues: list[str]
    decision_exact_rate: Optional[float]
    decision_kappa: Optional[float]
    agreed_tier1: int

    @property
    def gate_pass(self) -> bool:
        agreement_pass = (
            self.decision_kappa is not None and self.decision_kappa >= 0.8
        ) or (
            self.decision_kappa is None and self.decision_exact_rate == 1.0
        )
        return (
            not self.issues
            and self.reviewer_a_completed == self.rows
            and self.reviewer_b_completed == self.rows
            and agreement_pass
            and self.agreed_tier1 >= 10
        )


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _signals(text: str) -> list[str]:
    checks = (
        ("explicit_dispersion", _EXPLICIT_DISPERSION_RE),
        ("named_dispersion_value", _NAMED_DISPERSION_VALUE_RE),
        ("sample_size", _SAMPLE_SIZE_RE),
        ("sd", _SD_RE),
        ("sem", _SEM_RE),
        ("outcome", _OUTCOME_RE),
        ("medium", _MEDIUM_RE),
        ("figure_caption", _FIGURE_RE),
        ("mean", _MEAN_RE),
        ("error_policy", _ERROR_POLICY_RE),
    )
    return [name for name, pattern in checks if pattern.search(text)]


def _score(signals: Sequence[str]) -> int:
    weights = {
        "explicit_dispersion": 6,
        "named_dispersion_value": 6,
        "sample_size": 4,
        "sd": 3,
        "sem": 3,
        "outcome": 3,
        "medium": 2,
        "figure_caption": 3,
        "mean": 1,
        "error_policy": 1,
    }
    return sum(weights[signal] for signal in signals)


def _read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def create_quantitative_review(
    source_spec_path: Path,
    *,
    corpus_manifest_path: Path,
    papers_dir: Path,
    repo_root: Path,
    benchmark_version: str,
    manifest_path: Path,
    reviewer_template_path: Path,
    fitz_module=None,
) -> tuple[Path, Path]:
    """Select bounded statistical blocks and create a pointer-only review sheet."""
    if fitz_module is None:
        try:
            import fitz as fitz_module  # type: ignore[no-redef]
        except ImportError as exc:  # pragma: no cover - optional dependency path
            raise RuntimeError("PyMuPDF is required to build the quantitative review") from exc

    specs = _read_tsv(source_spec_path)
    required = {"record_id", "target_count"}
    if not specs or required - set(specs[0]):
        raise ValueError("source spec requires record_id and target_count columns")
    if len({row["record_id"] for row in specs}) != len(specs):
        raise ValueError("source spec contains duplicate record_id values")
    corpus = {row["record_id"]: row for row in _read_tsv(corpus_manifest_path)}

    sources: list[dict[str, object]] = []
    candidates: list[dict[str, object]] = []
    for spec in specs:
        record_id = spec["record_id"]
        canonical = corpus.get(record_id)
        if canonical is None:
            raise ValueError(f"{record_id} is absent from the corpus manifest")
        paper_id = slugify(canonical["title"])
        paper_dir = papers_dir / paper_id
        pdfs = sorted(paper_dir.glob("*.pdf"))
        if len(pdfs) != 1:
            raise ValueError(f"{record_id} requires exactly one PDF, found {len(pdfs)}")
        pdf_path = pdfs[0]
        pdf_payload = pdf_path.read_bytes()
        pdf_hash = _sha256(pdf_payload)
        target = int(spec["target_count"])
        if target <= 0:
            raise ValueError(f"{record_id} target_count must be positive")

        document = fitz_module.open(pdf_path)
        document_pages = int(document.page_count)
        page_best: list[dict[str, object]] = []
        try:
            for page_index, page in enumerate(document):
                best = None
                for block_index, block in enumerate(page.get_text("blocks", sort=True)):
                    text = " ".join(str(block[4]).split())
                    signals = _signals(text)
                    if not ({"explicit_dispersion", "sample_size", "sd", "sem"} & set(signals)):
                        continue
                    row = {
                        "record_id": record_id,
                        "paper_id": paper_id,
                        "pdf_page": page_index + 1,
                        "block_index": block_index,
                        "bbox_points": ",".join(f"{float(value):.3f}" for value in block[:4]),
                        "block_text_sha256": _sha256(text.encode("utf-8")),
                        "signals": signals,
                        "selection_score": _score(signals),
                    }
                    if best is None or (row["selection_score"], -block_index) > (
                        best["selection_score"], -int(best["block_index"])
                    ):
                        best = row
                if best is not None:
                    page_best.append(best)
        finally:
            document.close()
        selected = sorted(
            page_best,
            key=lambda row: (-int(row["selection_score"]), int(row["pdf_page"])),
        )[:target]
        if len(selected) != target:
            raise ValueError(
                f"{record_id} produced {len(selected)} distinct-page candidates; expected {target}"
            )
        relative_pdf = pdf_path.resolve().relative_to(repo_root.resolve()).as_posix()
        sources.append({
            "record_id": record_id,
            "paper_id": paper_id,
            "title": canonical["title"],
            "year": canonical["year"],
            "doi": canonical["doi"],
            "pdf_path": relative_pdf,
            "pdf_sha256": pdf_hash,
            "pages": document_pages,
            "target_count": target,
        })
        for row in selected:
            row.update({
                "title": canonical["title"],
                "doi": canonical["doi"],
                "pdf_path": relative_pdf,
                "pdf_sha256": pdf_hash,
            })
            candidates.append(row)

    candidates.sort(key=lambda row: (str(row["record_id"]), int(row["pdf_page"])))
    for index, row in enumerate(candidates, start=1):
        row["candidate_id"] = f"Q{index:03d}"
    manifest = {
        "format_version": FORMAT_VERSION,
        "benchmark_version": benchmark_version,
        "selector_version": SELECTOR_VERSION,
        "parent_schema_sha256": _schema_sha256(),
        "linked_fields": list(LINKED_FIELDS),
        "sources": sources,
        "candidates": candidates,
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    reviewer_template_path.parent.mkdir(parents=True, exist_ok=True)
    with reviewer_template_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for candidate in candidates:
            row = {column: "" for column in COLUMNS}
            row.update({
                "benchmark_version": benchmark_version,
                "candidate_id": candidate["candidate_id"],
                "record_id": candidate["record_id"],
                "paper_id": candidate["paper_id"],
                "title": candidate["title"],
                "doi": candidate["doi"],
                "pdf_path": candidate["pdf_path"],
                "pdf_sha256": candidate["pdf_sha256"],
                "pdf_page": candidate["pdf_page"],
                "block_index": candidate["block_index"],
                "bbox_points": candidate["bbox_points"],
                "block_text_sha256": candidate["block_text_sha256"],
                "signals": ";".join(candidate["signals"]),
                "linked_fields": ";".join(LINKED_FIELDS),
            })
            writer.writerow(row)
    return manifest_path, reviewer_template_path


def _candidate_block(document, candidate: dict[str, object]) -> str:
    page = document[int(candidate["pdf_page"]) - 1]
    blocks = page.get_text("blocks", sort=True)
    index = int(candidate["block_index"])
    if index >= len(blocks):
        raise ValueError("block index no longer exists")
    return " ".join(str(blocks[index][4]).split())


def validate_quantitative_review(
    manifest_path: Path,
    reviewer_path: Path,
    *,
    repo_root: Path,
    fitz_module=None,
) -> QuantitativeValidation:
    if fitz_module is None:
        import fitz as fitz_module  # type: ignore[no-redef]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    issues: list[str] = []
    if manifest.get("format_version") != FORMAT_VERSION:
        issues.append("unsupported quantitative manifest format")
    if manifest.get("selector_version") != SELECTOR_VERSION:
        issues.append("selector version mismatch")
    if manifest.get("parent_schema_sha256") != _schema_sha256():
        issues.append("parent A-M schema hash mismatch")
    candidates = {row["candidate_id"]: row for row in manifest.get("candidates", [])}
    documents = {}
    try:
        for source in manifest.get("sources", []):
            path = repo_root / source["pdf_path"]
            if not path.is_file():
                issues.append(f"{source['record_id']}: PDF missing")
                continue
            if _sha256(path.read_bytes()) != source["pdf_sha256"]:
                issues.append(f"{source['record_id']}: PDF hash mismatch")
                continue
            documents[source["record_id"]] = fitz_module.open(path)
        for candidate in candidates.values():
            document = documents.get(candidate["record_id"])
            if document is None:
                continue
            try:
                text = _candidate_block(document, candidate)
            except Exception as exc:  # noqa: BLE001
                issues.append(f"{candidate['candidate_id']}: locator invalid: {exc}")
                continue
            if _sha256(text.encode("utf-8")) != candidate["block_text_sha256"]:
                issues.append(f"{candidate['candidate_id']}: block text hash mismatch")

        with reviewer_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            if reader.fieldnames != COLUMNS:
                issues.append("reviewer worksheet columns do not match template")
            rows = list(reader)
        seen = set()
        completed = 0
        for line, row in enumerate(rows, start=2):
            candidate_id = row.get("candidate_id", "")
            if candidate_id in seen:
                issues.append(f"line {line}: duplicate candidate {candidate_id}")
                continue
            seen.add(candidate_id)
            candidate = candidates.get(candidate_id)
            if candidate is None:
                issues.append(f"line {line}: unexpected candidate {candidate_id}")
                continue
            expected = {
                "benchmark_version": manifest["benchmark_version"],
                "candidate_id": candidate_id,
                "record_id": candidate["record_id"],
                "paper_id": candidate["paper_id"],
                "title": candidate["title"],
                "doi": candidate["doi"],
                "pdf_path": candidate["pdf_path"],
                "pdf_sha256": candidate["pdf_sha256"],
                "pdf_page": str(candidate["pdf_page"]),
                "block_index": str(candidate["block_index"]),
                "bbox_points": candidate["bbox_points"],
                "block_text_sha256": candidate["block_text_sha256"],
                "signals": ";".join(candidate["signals"]),
                "linked_fields": ";".join(LINKED_FIELDS),
            }
            for column, value in expected.items():
                if row.get(column, "") != str(value):
                    issues.append(f"line {line}: immutable metadata drift in {column}")
            decision = row.get("decision", "").strip()
            if not decision:
                continue
            completed += 1
            _validate_review_row(row, line, issues)
        missing = set(candidates) - seen
        if missing:
            issues.append(f"worksheet missing {len(missing)} candidate(s)")
        return QuantitativeValidation(len(rows), len(candidates), completed, issues)
    finally:
        for document in documents.values():
            document.close()


def _validate_review_row(row: dict[str, str], line: int, issues: list[str]) -> None:
    decision = row["decision"].strip()
    if decision not in DECISIONS:
        issues.append(f"line {line}: invalid decision {decision!r}")
        return
    if not row["reviewer"].strip() or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["date"].strip()):
        issues.append(f"line {line}: reviewer and ISO date are required")
    if decision in {"reject", "not_recoverable"}:
        if not row["notes"].strip():
            issues.append(f"line {line}: {decision} requires notes")
        return
    if row["source_kind"].strip() not in SOURCE_KINDS:
        issues.append(f"line {line}: invalid source_kind")
    if not row["outcome"].strip():
        issues.append(f"line {line}: outcome is required for {decision}")
    if decision == "tier1_ready":
        required = [
            "treatment_label", "control_label", "treatment_mean_pointer",
            "control_mean_pointer", "treatment_dispersion_pointer",
            "control_dispersion_pointer", "treatment_n_pointer", "control_n_pointer",
        ]
        for field in required:
            if not row[field].strip():
                issues.append(f"line {line}: tier1_ready requires {field}")
        if row["dispersion_type"].strip() not in {"sd", "sem", "se"}:
            issues.append(f"line {line}: tier1_ready requires SD/SEM/SE dispersion")
        if row["sample_size_status"].strip() not in {"exact_per_group", "exact_shared"}:
            issues.append(f"line {line}: tier1_ready requires exact sample size")
        if row["replicate_type"].strip() not in {"biological", "mixed"}:
            issues.append(f"line {line}: tier1_ready requires biological or mixed replicates")
        if row["same_comparison"].strip() != "yes":
            issues.append(f"line {line}: tier1_ready requires same_comparison=yes")
    else:
        if row["dispersion_type"].strip() and row["dispersion_type"].strip() not in DISPERSION_TYPES:
            issues.append(f"line {line}: invalid dispersion_type")
        if row["replicate_type"].strip() and row["replicate_type"].strip() not in REPLICATE_TYPES:
            issues.append(f"line {line}: invalid replicate_type")
        if row["sample_size_status"].strip() and row["sample_size_status"].strip() not in SAMPLE_SIZE_STATUSES:
            issues.append(f"line {line}: invalid sample_size_status")
        if row["same_comparison"].strip() and row["same_comparison"].strip() not in SAME_COMPARISON:
            issues.append(f"line {line}: invalid same_comparison")
        if decision == "tier2_only":
            has_point_pointer = bool(row["effect_pointer"].strip()) or bool(
                row["treatment_mean_pointer"].strip() and row["control_mean_pointer"].strip()
            )
            for field in ("treatment_label", "control_label", "notes"):
                if not row[field].strip():
                    issues.append(f"line {line}: tier2_only requires {field}")
            if not has_point_pointer:
                issues.append(f"line {line}: tier2_only requires a point-effect pointer")
            if row["same_comparison"].strip() != "yes":
                issues.append(f"line {line}: tier2_only requires same_comparison=yes")


def compare_quantitative_reviews(
    manifest_path: Path,
    reviewer_a_path: Path,
    reviewer_b_path: Path,
    *,
    repo_root: Path,
    fitz_module=None,
) -> QuantitativeComparison:
    left_validation = validate_quantitative_review(
        manifest_path, reviewer_a_path, repo_root=repo_root, fitz_module=fitz_module
    )
    right_validation = validate_quantitative_review(
        manifest_path, reviewer_b_path, repo_root=repo_root, fitz_module=fitz_module
    )
    issues = [f"reviewer A: {issue}" for issue in left_validation.issues]
    issues.extend(f"reviewer B: {issue}" for issue in right_validation.issues)

    def decisions(path: Path) -> dict[str, str]:
        return {
            row["candidate_id"]: row["decision"].strip()
            for row in _read_tsv(path)
            if row.get("decision", "").strip()
        }

    left = decisions(reviewer_a_path)
    right = decisions(reviewer_b_path)
    paired_ids = sorted(set(left) & set(right))
    values_a = [left[candidate_id] for candidate_id in paired_ids]
    values_b = [right[candidate_id] for candidate_id in paired_ids]
    exact = (
        sum(a == b for a, b in zip(values_a, values_b)) / len(paired_ids)
        if paired_ids else None
    )
    agreed_tier1 = sum(a == b == "tier1_ready" for a, b in zip(values_a, values_b))
    return QuantitativeComparison(
        rows=left_validation.expected_rows,
        reviewer_a_completed=left_validation.completed,
        reviewer_b_completed=right_validation.completed,
        issues=issues,
        decision_exact_rate=round(exact, 4) if exact is not None else None,
        decision_kappa=_cohen_kappa(values_a, values_b),
        agreed_tier1=agreed_tier1,
    )


def comparison_markdown(result: QuantitativeComparison) -> str:
    status = "PASS_PENDING_ADJUDICATION" if result.gate_pass else "NOT_READY"
    lines = [
        "# Quantitative Dual-Review Pilot Status",
        "",
        f"**Status: {status}**",
        "",
        f"- Candidate locators: {result.rows}",
        f"- Reviewer A completed: {result.reviewer_a_completed}/{result.rows}",
        f"- Reviewer B completed: {result.reviewer_b_completed}/{result.rows}",
        f"- Decision exact agreement: {result.decision_exact_rate if result.decision_exact_rate is not None else 'NA'}",
        f"- Cohen kappa: {result.decision_kappa if result.decision_kappa is not None else 'NA'}",
        f"- Independently agreed tier-1-ready locators: {result.agreed_tier1}",
        f"- Validation issues: {len(result.issues)}",
        "",
        "Passing this pilot only permits conflict adjudication and deterministic value resolution. "
        "It is not wet-lab approval.",
    ]
    if result.issues:
        lines.extend(["", "## Issues", ""] + [f"- {issue}" for issue in result.issues])
    return "\n".join(lines) + "\n"


def copy_working_reviews(template_path: Path, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = output_dir / "reviewer_A.tsv", output_dir / "reviewer_B.tsv"
    for output in outputs:
        if output.exists():
            raise FileExistsError(f"refusing to overwrite existing reviewer sheet: {output}")
        shutil.copyfile(template_path, output)
    return outputs


def render_candidate_crops(
    manifest_path: Path,
    *,
    repo_root: Path,
    output_dir: Path,
    dpi: int = 180,
    fitz_module=None,
) -> list[Path]:
    if fitz_module is None:
        import fitz as fitz_module  # type: ignore[no-redef]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    sources = {row["record_id"]: row for row in manifest["sources"]}
    documents = {}
    outputs = []
    try:
        for record_id, source in sources.items():
            path = repo_root / source["pdf_path"]
            if _sha256(path.read_bytes()) != source["pdf_sha256"]:
                raise ValueError(f"{record_id}: PDF hash mismatch")
            documents[record_id] = fitz_module.open(path)
        for candidate in manifest["candidates"]:
            document = documents[candidate["record_id"]]
            page = document[int(candidate["pdf_page"]) - 1]
            bbox = [float(value) for value in candidate["bbox_points"].split(",")]
            clip = fitz_module.Rect(*bbox)
            clip.x0 = page.rect.x0
            clip.x1 = page.rect.x1
            clip.y0 = max(page.rect.y0, clip.y0 - 18)
            clip.y1 = min(page.rect.y1, clip.y1 + 18)
            output = output_dir / f"{candidate['candidate_id']}_{candidate['record_id']}_p{int(candidate['pdf_page']):02d}.png"
            page.get_pixmap(dpi=dpi, clip=clip, alpha=False).save(output)
            outputs.append(output)
    finally:
        for document in documents.values():
            document.close()
    return outputs
