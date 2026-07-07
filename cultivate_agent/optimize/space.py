"""The medium-formulation design space.

A formulation is a point in a mixed continuous/binary/categorical space:

* continuous  — component concentrations (e.g. FGF2 ng/mL, FBS %),
* binary      — include / exclude a component,
* categorical — the basal-medium platform.

The space can be **warm-started from the knowledge base** (``space_from_kb``):
the literature tells us *which* components matter (by frequency) and *which*
basal media are in play, which is exactly the prior a cold-start Bayesian
optimizer lacks. Concentration ranges default to literature-typical values per
component class (the extracted numbers are not cross-comparable enough to set
tight per-component bounds — see the record's critique).

Encoding: continuous → [0,1] (min-max), binary → {0,1}, categorical → one-hot.
This gives a plain real vector in [0,1]^d for the GP surrogate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

# Literature-typical ranges per component class (only used to bound the search;
# always overridable). Units are the community-standard ones.
CLASS_RANGES = {
    "serum": (0.0, 20.0, "%"),
    "growth_factor": (0.0, 100.0, "ng/mL"),
    "small_molecule": (0.0, 10.0, "uM"),
    "supplement": (0.0, 20.0, "x/%"),
    "defined_supplement": (0.0, 1.0, "x"),
    "hydrolysate": (0.0, 20.0, "g/L"),
    "extract": (0.0, 20.0, "g/L"),
    "amino_acid": (0.0, 10.0, "mM"),
    "carbon_source": (0.0, 25.0, "mM"),
    "trace_element": (0.0, 100.0, "nM"),
    "albumin_substitute": (0.0, 5.0, "mg/mL"),
}


@dataclass
class Parameter:
    name: str
    kind: str  # "continuous" | "binary" | "categorical"
    low: float = 0.0
    high: float = 1.0
    unit: str = ""
    choices: List[str] = field(default_factory=list)
    component_class: Optional[str] = None

    @property
    def width(self) -> int:
        return len(self.choices) if self.kind == "categorical" else 1


class MediumDesignSpace:
    def __init__(self, parameters: List[Parameter]):
        self.parameters = parameters
        self._offsets: List[int] = []
        off = 0
        for p in parameters:
            self._offsets.append(off)
            off += p.width
        self.dim = off

    # ------------------------------------------------------------------ #
    # Encode / decode                                                    #
    # ------------------------------------------------------------------ #
    def encode(self, formulation: Dict[str, object]) -> np.ndarray:
        x = np.zeros(self.dim)
        for p, off in zip(self.parameters, self._offsets):
            v = formulation.get(p.name)
            if p.kind == "continuous":
                val = float(v) if v is not None else p.low
                x[off] = 0.0 if p.high == p.low else np.clip((val - p.low) / (p.high - p.low), 0, 1)
            elif p.kind == "binary":
                x[off] = 1.0 if v else 0.0
            else:  # categorical one-hot
                if v in p.choices:
                    x[off + p.choices.index(v)] = 1.0
                elif p.choices:
                    x[off] = 1.0  # default to first choice
        return x

    def decode(self, x: np.ndarray) -> Dict[str, object]:
        out: Dict[str, object] = {}
        for p, off in zip(self.parameters, self._offsets):
            if p.kind == "continuous":
                out[p.name] = round(p.low + float(x[off]) * (p.high - p.low), 4)
            elif p.kind == "binary":
                out[p.name] = bool(x[off] >= 0.5)
            else:
                block = x[off:off + p.width]
                out[p.name] = p.choices[int(np.argmax(block))] if p.choices else None
        return out

    # ------------------------------------------------------------------ #
    # Sampling                                                           #
    # ------------------------------------------------------------------ #
    def sample_encoded(self, n: int, *, seed: Optional[int] = None) -> np.ndarray:
        """Space-filling sample in the encoded [0,1] space (valid one-hots)."""
        rng = np.random.default_rng(seed)
        X = np.zeros((n, self.dim))
        for p, off in zip(self.parameters, self._offsets):
            if p.kind == "continuous":
                X[:, off] = rng.random(n)
            elif p.kind == "binary":
                X[:, off] = (rng.random(n) < 0.5).astype(float)
            else:
                idx = rng.integers(0, p.width, size=n)
                for i in range(n):
                    X[i, off + idx[i]] = 1.0
        return X

    def sample(self, n: int, *, seed: Optional[int] = None) -> List[Dict[str, object]]:
        return [self.decode(x) for x in self.sample_encoded(n, seed=seed)]

    def describe(self) -> str:
        lines = [f"MediumDesignSpace: {len(self.parameters)} parameters, encoded dim {self.dim}"]
        for p in self.parameters:
            if p.kind == "continuous":
                lines.append(f"  - {p.name}: continuous [{p.low}, {p.high}] {p.unit}")
            elif p.kind == "binary":
                lines.append(f"  - {p.name}: include/exclude")
            else:
                lines.append(f"  - {p.name}: categorical {p.choices}")
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Factories                                                                   #
# --------------------------------------------------------------------------- #
def default_medium_space() -> MediumDesignSpace:
    """A sensible default space when no knowledge base is available."""
    params = [
        Parameter("basal_medium", "categorical", choices=["DMEM", "DMEM/F12", "Ham's F-10", "B8"]),
        Parameter("FBS", "continuous", *CLASS_RANGES["serum"][:2], unit="%", component_class="serum"),
        Parameter("FGF2", "continuous", *CLASS_RANGES["growth_factor"][:2], unit="ng/mL", component_class="growth_factor"),
        Parameter("IGF-1", "continuous", *CLASS_RANGES["growth_factor"][:2], unit="ng/mL", component_class="growth_factor"),
        Parameter("recombinant-albumin", "continuous", *CLASS_RANGES["albumin_substitute"][:2], unit="mg/mL", component_class="albumin_substitute"),
        Parameter("ITS", "binary", component_class="supplement"),
        Parameter("Y-27632", "continuous", *CLASS_RANGES["small_molecule"][:2], unit="uM", component_class="small_molecule"),
        Parameter("soy-protein-hydrolysate", "continuous", *CLASS_RANGES["supplement"][:2], unit="g/L", component_class="supplement"),
    ]
    return MediumDesignSpace(params)


def space_from_kb(kb, *, max_components: int = 10, min_papers: int = 1) -> MediumDesignSpace:
    """Warm-start the design space from the knowledge base.

    Components are chosen by how many papers use them (a literature-derived
    relevance prior); the basal-medium categorical is drawn from the media
    actually seen in the corpus. Ranges use per-class literature-typical values.
    """
    basal = [c for c, _ in kb.component_counts(role="basal_medium")]
    if not basal:
        basal = ["DMEM", "DMEM/F12", "Ham's F-10", "B8"]

    params: List[Parameter] = [Parameter("basal_medium", "categorical", choices=basal[:6] or ["DMEM/F12"])]

    # Always allow serum level as an actionable knob.
    params.append(Parameter("FBS", "continuous", *CLASS_RANGES["serum"][:2], unit="%", component_class="serum"))

    chosen = 0
    medium_roles = (
        "growth_factor",
        "small_molecule",
        "supplement",
        "defined_supplement",
        "albumin_substitute",
        "hydrolysate",
        "extract",
        "amino_acid",
        "carbon_source",
        "trace_element",
    )
    for role in medium_roles:
        for canonical, n in kb.component_counts(role=role):
            if chosen >= max_components or n < min_papers:
                break
            lo, hi, unit = CLASS_RANGES.get(role, (0.0, 1.0, ""))
            # Represent as continuous concentration (0 = excluded).
            params.append(Parameter(canonical, "continuous", lo, hi, unit=unit, component_class=role))
            chosen += 1

    return MediumDesignSpace(params)
