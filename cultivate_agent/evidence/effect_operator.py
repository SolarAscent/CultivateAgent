"""Effect-extraction operator: turn paper text into quoted directional evidence.

This is the honest data source for :mod:`cultivate_agent.evidence.meta_analysis`.
It asks the LLM, for one outcome (e.g. proliferation), which medium components the
paper provides *directional* evidence about, each with a verbatim quote and the
experimental context. It never infers an effect from mere co-occurrence.

Each returned :class:`EvidenceItem` carries:
* direction (+1 beneficial / -1 detrimental / 0 neutral),
* an optional standardized effect + variance when the paper reports them,
* context covariates (species, cell type, stage) for heterogeneity modeling,
* a verbatim quote, verified against the source.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import List, Optional

from ..llm.base import LLMClient, LLMError, extract_json
from ..schema.evidence import Evidence
from ..schema.paper import PaperRef
from ..schema.structured_paper import structured_paper_from_text
from .meta_analysis import EvidenceItem

# Sections where component->outcome effects are reported. A naive text[:N] prefix
# misses these in long reviews (found during the live DeepSeek run), so we route.
_EFFECT_SECTION_HINTS = [
    "results", "discussion", "methods", "materials and methods",
    "media", "medium", "cell culture", "growth", "proliferation", "expansion",
]

_SYSTEM = (
    "You extract DIRECTIONAL EVIDENCE about how culture-medium components affect a "
    "specific outcome, from a cultivated-meat paper. Report only relationships the "
    "text actually supports, each with a verbatim quote. Do NOT infer an effect from "
    "the mere presence of a component. If the paper does not state a direction, use 0 "
    "(neutral/unclear). Output STRICT JSON only."
)


def _route_effect_context(text: str, paper_id: str, title: Optional[str], max_chars: int) -> str:
    """Concatenate effect-bearing sections (results/methods/media...) up to a budget.

    Falls back to the leading text if no sections match, so short inputs still work.
    """
    if len(text) <= max_chars:
        return text
    paper = structured_paper_from_text(paper_id, text, title=title)
    passages = paper.section_passages(_EFFECT_SECTION_HINTS)
    if not passages:
        return text[:max_chars]
    out, used = [], 0
    if paper.abstract:
        chunk = "Abstract\n" + paper.abstract
        out.append(chunk[: max_chars // 4]); used += len(out[-1])
    for _sid, passage in passages:
        if used >= max_chars:
            break
        chunk = passage[: max_chars - used]
        out.append(chunk); used += len(chunk)
    return "\n\n".join(out)


def _prompt(ref: PaperRef, outcome: str, text: str) -> str:
    return f"""PAPER: {ref.title or ref.paper_id}
OUTCOME OF INTEREST: {outcome}

For each medium component the paper gives evidence about, report its effect on
{outcome}: +1 = increases/beneficial, -1 = decreases/detrimental, 0 = no or
unclear effect. Include an `effect` number and `variance` ONLY if the quoted
span contains the exact reported number needed to support that field; otherwise
omit it. Do not compute transformed effect sizes yourself. Include experimental
context. Every item needs a verbatim `quote` from the text.

Return STRICT JSON:
{{
  "evidence": [
    {{"component": "<name>", "direction": 1, "effect": null, "variance": null,
      "context": {{"species": "<or omit>", "cell_type": "<or omit>", "stage": "<or omit>"}},
      "quote": "<verbatim span>"}}
  ]
}}

TEXT:
'''{text}'''

REMINDER: only text-supported directional claims; verbatim quotes; strict JSON.
"""


def extract_effects(
    client: LLMClient,
    ref: PaperRef,
    text: str,
    outcome: str,
    *,
    normalizer=None,
    verify_evidence: bool = True,
    max_context_chars: int = 28000,
) -> List[EvidenceItem]:
    """Extract directional :class:`EvidenceItem`s for ``outcome`` from one paper."""
    if not text or not text.strip():
        return []
    routed = _route_effect_context(text, ref.paper_id, ref.title, max_context_chars)
    try:
        raw = client.chat(_SYSTEM, _prompt(ref, outcome, routed))
        payload = extract_json(raw)
    except LLMError:
        return []
    if not isinstance(payload, dict):
        return []

    items: List[EvidenceItem] = []
    for e in payload.get("evidence", []) or []:
        if not isinstance(e, dict):
            continue
        component = str(e.get("component", "")).strip()
        quote = str(e.get("quote", "")).strip()
        if not component:
            continue
        if verify_evidence and quote and not Evidence(quote=quote).verify_against(text):
            # Ungrounded claim -> drop (stricter than the schema extractor: an
            # unverifiable effect must not enter the meta-analysis).
            continue
        if normalizer is not None:
            component = normalizer.canonicalize(component).canonical

        direction = e.get("direction")
        try:
            direction = int(direction) if direction is not None else None
        except (TypeError, ValueError):
            direction = None
        effect = _to_float(e.get("effect"))
        variance = _to_float(e.get("variance"))
        context = {k: str(v) for k, v in (e.get("context") or {}).items() if v}
        if quote:
            inferred = _infer_log_response_ratio(quote, direction, component, outcome)
            if effect is not None and not _number_supported_by_quote(effect, quote):
                effect = None
            if variance is not None and not _number_supported_by_quote(variance, quote):
                variance = None
            if inferred.effect is not None:
                effect = inferred.effect
                variance = inferred.variance
                context.update(inferred.context)
        else:
            effect = None
            variance = None

        items.append(EvidenceItem(
            component=component, outcome=outcome, paper_id=ref.paper_id,
            effect=effect, variance=variance, direction=direction,
            context=context, quote=quote,
        ))
    return items


def _to_float(x) -> Optional[float]:
    try:
        return float(x) if x is not None else None
    except (TypeError, ValueError):
        return None


_NUMBER_RE = re.compile(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?")


def _number_supported_by_quote(value: float, quote: str) -> bool:
    """Return True only when ``quote`` contains a numerically matching token.

    This is deliberately conservative. If an LLM computes a transformed effect
    (for example log fold-change) without the resulting number appearing in the
    quote, the item stays direction-only until a deterministic numeric extractor
    or human reviewer verifies the calculation.
    """
    for match in _NUMBER_RE.finditer(quote):
        if _number_is_embedded(quote, match.start(), match.end()):
            continue
        token = match.group(0)
        try:
            observed = float(token)
        except ValueError:
            continue
        tol = max(1e-9, abs(value) * 1e-6)
        if abs(observed - value) <= tol:
            return True
    return False


_POSITIVE_WORDS = (
    "increase", "increased", "increases", "increasing", "improve", "improved",
    "improves", "enhance", "enhanced", "enhances", "higher", "greater", "more",
)
_NEGATIVE_WORDS = (
    "decrease", "decreased", "decreases", "decreasing", "reduce", "reduced",
    "reduces", "reduction", "lower", "less", "suppress", "suppressed",
    "inhibit", "inhibited", "decline", "declined",
)
_FOLD_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?:-| )?(?:fold|x|\u00d7)\b",
    flags=re.IGNORECASE,
)
# "2.2 \u00b1 0.4-fold": the point estimate is 2.2, not the dispersion 0.4. Capture the
# leading value so the bare _FOLD_RE below does not latch onto the error bar.
_FOLD_DISPERSION_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?:\u00b1|\+/-|\+/\u2212)\s*\d+(?:\.\d+)?"
    r"\s*(?:-| )?(?:fold|x|\u00d7)\b",
    flags=re.IGNORECASE,
)
_PERCENT_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*%\s*(?:change|increase|decrease|reduction|improvement|higher|lower|more|less)?",
    flags=re.IGNORECASE,
)


@dataclass
class _NumericInference:
    effect: Optional[float] = None
    variance: Optional[float] = None
    context: dict[str, str] = field(default_factory=dict)


def _infer_log_response_ratio(
    quote: str,
    direction: Optional[int],
    component: str = "",
    outcome: str = "",
) -> _NumericInference:
    """Infer ln(response ratio) from explicit proportional phrasing.

    The parser only handles directly reported proportional changes in the quote.
    It also handles very explicit treatment/control means, but never infers a
    variance. This creates tier-2 evidence at most.
    """
    fold = _infer_fold_ratio(quote, direction)
    if fold is not None and fold > 0:
        return _NumericInference(effect=math.log(fold), context={
            "effect_metric": "log_response_ratio",
            "effect_inference_source": "explicit_fold_or_percent",
        })
    percent = _infer_percent_ratio(quote, direction)
    if percent is not None and percent > 0:
        return _NumericInference(effect=math.log(percent), context={
            "effect_metric": "log_response_ratio",
            "effect_inference_source": "explicit_fold_or_percent",
        })
    means = _infer_raw_mean_ratio(quote, component, outcome)
    if means.effect is not None:
        return means
    return _NumericInference()


def _infer_fold_ratio(quote: str, direction: Optional[int]) -> Optional[float]:
    # "N ± M-fold": take the point estimate N, never the dispersion M.
    # "fold"/"x"/"×" denotes a ratio, so (unlike a percentage) it is almost never a
    # concentration; the model's global direction is an acceptable fallback. The
    # only observed failure was grabbing the dispersion in "N ± M-fold".
    disp = _FOLD_DISPERSION_RE.search(quote)
    if disp is not None:
        fold = _safe_positive_float(disp.group("value"))
        if fold is not None and fold > 0:
            polarity = _local_polarity(quote, disp.start(), disp.end(), direction)
            if polarity > 0:
                return fold
            if polarity < 0:
                return 1.0 / fold
            return None
    for match in _FOLD_RE.finditer(quote):
        # Skip a number that is itself the dispersion in "N ± M-fold".
        if _preceded_by_dispersion(quote, match.start()):
            continue
        fold = _safe_positive_float(match.group("value"))
        if fold is None or fold <= 0:
            continue
        polarity = _local_polarity(quote, match.start(), match.end(), direction)
        if polarity > 0:
            return fold
        if polarity < 0:
            return 1.0 / fold
    return None


def _preceded_by_dispersion(quote: str, start: int) -> bool:
    """True if the number at ``start`` is the error term after ``±`` / ``+/-``."""
    prefix = quote[max(0, start - 4):start]
    return any(sym in prefix for sym in ("±", "+/-", "+/−"))


_CONCENTRATION_CONTEXT = (
    "fbs", "serum", "medium", "media", "glucose", "glutamax", "glutamine",
    "albumin", "bsa", "hydrolysate", "extract", "dmso", "co2", "o2", "dmem",
    "supplement", "v/v", "w/v", "psfc",
)


def _infer_percent_ratio(quote: str, direction: Optional[int]) -> Optional[float]:
    for match in _PERCENT_RE.finditer(quote):
        pct = _safe_positive_float(match.group("value"))
        if pct is None:
            continue
        # "30% FBS" / "20% FBS-PSFC" are concentrations, not "+30% responses":
        # if a reagent/medium word follows the percentage, it is composition.
        tail = quote[match.end(): match.end() + 14].lower()
        if any(word in tail for word in _CONCENTRATION_CONTEXT):
            continue
        # Require an explicit change word next to the number (strict); do not fall
        # back to the model's global direction, which would turn any leftover
        # composition percentage into a fabricated effect magnitude.
        polarity = _local_polarity(quote, match.start(), match.end(), direction, strict=True)
        if polarity > 0:
            return 1.0 + pct / 100.0
        if polarity < 0 and pct < 100.0:
            return 1.0 - pct / 100.0
    return None


def _local_polarity(
    quote: str, start: int, end: int, direction: Optional[int], *, strict: bool = False
) -> int:
    """Polarity of the change described next to a number.

    With ``strict=True`` an explicit increase/decrease word must appear next to
    the number; the model's global ``direction`` is NOT used as a fallback. This
    is what separates "increased 30%" (a real effect) from "30% FBS" (a
    concentration), so magnitude inference does not fabricate effect sizes.
    """
    window = quote[max(0, start - 48): min(len(quote), end + 48)].lower()
    has_pos = any(word in window for word in _POSITIVE_WORDS)
    has_neg = any(word in window for word in _NEGATIVE_WORDS)
    if has_pos and not has_neg:
        return 1
    if has_neg and not has_pos:
        return -1
    if strict:
        return 0
    if direction is not None:
        return int(math.copysign(1, direction)) if direction != 0 else 0
    return 0


def _safe_positive_float(value: str) -> Optional[float]:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out > 0 else None


_CONTROL_WORDS = (
    "control", "vehicle", "untreated", "basal", "comparator", "baseline",
)
_TREATMENT_WORDS = (
    "treated", "treatment", "supplemented", "supplementation", "with", "plus",
    "exposed", "condition",
)
_NON_RESPONSE_UNITS = (
    "%", "fold", "x", "\u00d7", "ng/ml", "ng ml", "ug/ml", "\u03bcg/ml", "mg/ml",
    "g/l", "mm", "mmol", "um", "\u03bcm", "nm", "pm", "h", "hr", "hrs", "hour",
    "hours", "d", "day", "days", "passage", "passages",
)
_TIMEPOINT_RE = re.compile(
    r"\b(?:at|after|for)\s+(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>h|hr|hrs|hours?|d|days?)\b",
    flags=re.IGNORECASE,
)
_GROUP_STATS_RE = re.compile(
    r"(?P<label>[^.;,]{0,80}?)\bmean\s*=?\s*(?P<mean>[-+]?(?:\d+(?:\.\d*)?|\.\d+))"
    r"\s*,?\s*(?P<stat_label>sd|s\.d\.|standard deviation|se|s\.e\.|sem|s\.e\.m\.|standard error)"
    r"\s*=?\s*(?P<stat>[-+]?(?:\d+(?:\.\d*)?|\.\d+))"
    r"\s*,?\s*n\s*=?\s*(?P<n>\d+)",
    flags=re.IGNORECASE,
)


def _infer_raw_mean_ratio(quote: str, component: str, outcome: str) -> _NumericInference:
    stats = _labelled_group_stats(quote, component)
    treatment_stats = [group for group in stats if group["label"] == "treatment"]
    control_stats = [group for group in stats if group["label"] == "control"]
    if len(treatment_stats) == 1 and len(control_stats) == 1:
        return _infer_raw_mean_ratio_from_stats(
            treatment_stats[0],
            control_stats[0],
            quote,
            outcome,
        )

    observations = _labelled_numeric_observations(quote, component)
    treatment = [obs for obs in observations if obs["label"] == "treatment"]
    control = [obs for obs in observations if obs["label"] == "control"]
    if len(treatment) != 1 or len(control) != 1:
        return _NumericInference()

    treatment_value = treatment[0]["value"]
    control_value = control[0]["value"]
    if treatment_value <= 0 or control_value <= 0:
        return _NumericInference()

    context = {
        "effect_metric": "log_response_ratio",
        "effect_inference_source": "treatment_control_means",
        "treatment_mean": _format_effect_number(treatment_value),
        "control_mean": _format_effect_number(control_value),
    }
    if outcome:
        context["effect_endpoint"] = outcome
    timepoint = _extract_timepoint(quote)
    if timepoint:
        context["effect_timepoint"] = timepoint
    return _NumericInference(effect=math.log(treatment_value / control_value), context=context)


def _infer_raw_mean_ratio_from_stats(
    treatment: dict[str, float | int | str],
    control: dict[str, float | int | str],
    quote: str,
    outcome: str,
) -> _NumericInference:
    treatment_mean = float(treatment["mean"])
    control_mean = float(control["mean"])
    treatment_sd = float(treatment["sd"])
    control_sd = float(control["sd"])
    treatment_n = int(treatment["n"])
    control_n = int(control["n"])
    if min(treatment_mean, control_mean, treatment_sd, control_sd) <= 0:
        return _NumericInference()
    if treatment_n <= 1 or control_n <= 1:
        return _NumericInference()

    effect = math.log(treatment_mean / control_mean)
    variance = (
        (treatment_sd ** 2) / (treatment_n * treatment_mean ** 2)
        + (control_sd ** 2) / (control_n * control_mean ** 2)
    )
    context = {
        "effect_metric": "log_response_ratio",
        "effect_inference_source": "treatment_control_mean_sd_n",
        "treatment_mean": _format_effect_number(treatment_mean),
        "control_mean": _format_effect_number(control_mean),
        "treatment_sd": _format_effect_number(treatment_sd),
        "control_sd": _format_effect_number(control_sd),
        "treatment_n": str(treatment_n),
        "control_n": str(control_n),
        "variance_formula": "ROM_LS_Hedges1999",
    }
    if outcome:
        context["effect_endpoint"] = outcome
    timepoint = _extract_timepoint(quote)
    if timepoint:
        context["effect_timepoint"] = timepoint
    return _NumericInference(effect=effect, variance=variance, context=context)


def _labelled_group_stats(quote: str, component: str) -> list[dict[str, float | int | str]]:
    groups: list[dict[str, float | int | str]] = []
    component_terms = _component_terms(component)
    for match in _GROUP_STATS_RE.finditer(quote):
        label_text = match.group("label").lower()
        has_control = any(word in label_text for word in _CONTROL_WORDS)
        has_component = any(term and term in label_text for term in component_terms)
        has_treatment = has_component or any(word in label_text for word in _TREATMENT_WORDS)
        if has_control == has_treatment:
            continue
        mean = _safe_positive_float(match.group("mean"))
        stat = _safe_positive_float(match.group("stat"))
        try:
            n = int(match.group("n"))
        except (TypeError, ValueError):
            continue
        if mean is None or stat is None or n <= 1:
            continue
        stat_label = match.group("stat_label").lower().replace(".", "")
        sd = stat * math.sqrt(n) if stat_label in {"se", "sem", "standard error"} else stat
        groups.append({
            "label": "control" if has_control else "treatment",
            "mean": mean,
            "sd": sd,
            "n": n,
        })
    return groups


def _labelled_numeric_observations(quote: str, component: str) -> list[dict[str, float | str]]:
    out: list[dict[str, float | str]] = []
    component_terms = _component_terms(component)
    for match in _NUMBER_RE.finditer(quote):
        if _number_is_embedded(quote, match.start(), match.end()):
            continue
        value = _safe_positive_float(match.group(0))
        if value is None or _is_non_response_number(quote, match.end()):
            continue
        left = _local_left_phrase(quote[max(0, match.start() - 64):match.start()]).lower()
        right = quote[match.end(): min(len(quote), match.end() + 12)].lower()
        label_window = f"{left} {right}"
        has_control = any(word in label_window for word in _CONTROL_WORDS)
        has_component = any(term and term in label_window for term in component_terms)
        has_treatment = has_component or any(word in label_window for word in _TREATMENT_WORDS)
        if has_control and not has_treatment:
            out.append({"label": "control", "value": value})
        elif has_treatment and not has_control:
            out.append({"label": "treatment", "value": value})
    return out


def _component_terms(component: str) -> list[str]:
    terms = [component.strip().lower()]
    for part in re.split(r"[^A-Za-z0-9+\-]+", component):
        part = part.strip().lower()
        if len(part) >= 3:
            terms.append(part)
    return sorted(set(terms), key=len, reverse=True)


def _local_left_phrase(text: str) -> str:
    parts = re.split(r"[,;:()]", text)
    return parts[-1] if parts else text


def _number_is_embedded(text: str, start: int, end: int) -> bool:
    if start > 0 and text[start - 1].isalpha():
        return True
    if start > 1 and text[start - 1] == "-" and text[start - 2].isalpha():
        return True
    if end < len(text) and text[end].isalpha():
        return True
    return False


def _is_non_response_number(quote: str, number_end: int) -> bool:
    tail = quote[number_end: number_end + 20].strip().lower()
    return any(tail.startswith(unit) for unit in _NON_RESPONSE_UNITS)


def _extract_timepoint(quote: str) -> str:
    match = _TIMEPOINT_RE.search(quote)
    if not match:
        return ""
    return f"{match.group('value')} {match.group('unit')}"


def _format_effect_number(value: float) -> str:
    return f"{value:.12g}"
