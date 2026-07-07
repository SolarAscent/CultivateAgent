"""Canonicalize medium components against the ontology.

This is the CultivateAgent analog of ReactionSeek's name->SMILES standardization:
a deterministic, dictionary-backed step that turns the LLM's free-text component
names ("bFGF", "basic FGF", "FGF-2") into a single canonical key ("FGF2") so the
knowledge base is queryable and comparable.

Matching order: exact -> alias -> (optional) fuzzy. Fuzzy matching requires
``rapidfuzz``; without it, only exact/alias matches are made (and everything
else is passed through unchanged, never dropped).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass
class ComponentMatch:
    raw: str
    canonical: str
    category: Optional[str]
    matched_via: str        # "exact" | "alias" | "fuzzy" | "none"
    score: float = 1.0


class ComponentNormalizer:
    def __init__(self, ontology_dir: str | Path, *, fuzzy_threshold: float = 0.90):
        self.ontology_dir = Path(ontology_dir)
        self.fuzzy_threshold = fuzzy_threshold
        # lowercased surface form -> (canonical, category)
        self._lookup: Dict[str, tuple] = {}
        self._canonicals: List[str] = []
        self._load()

    def _load(self) -> None:
        if not self.ontology_dir.exists():
            return
        for yml in sorted(self.ontology_dir.glob("*.yaml")):
            try:
                entries = yaml.safe_load(yml.read_text(encoding="utf-8")) or []
            except Exception:  # noqa: BLE001
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                canonical = entry.get("canonical")
                if not canonical:
                    continue
                category = entry.get("category")
                self._canonicals.append(canonical)
                self._lookup[canonical.lower()] = (canonical, category)
                for alias in entry.get("aliases", []) or []:
                    self._lookup.setdefault(str(alias).lower(), (canonical, category))

    def canonicalize(self, name: str) -> ComponentMatch:
        raw = (name or "").strip()
        if not raw:
            return ComponentMatch(raw=name, canonical=name, category=None, matched_via="none", score=0.0)
        key = raw.lower()

        hit = self._lookup.get(key)
        if hit:
            canon, cat = hit
            via = "exact" if canon.lower() == key else "alias"
            return ComponentMatch(raw=raw, canonical=canon, category=cat, matched_via=via, score=1.0)

        # Optional fuzzy match.
        try:
            from rapidfuzz import process, fuzz  # type: ignore

            surfaces = list(self._lookup.keys())
            if surfaces:
                best = process.extractOne(key, surfaces, scorer=fuzz.WRatio)
                if best and best[1] / 100.0 >= self.fuzzy_threshold:
                    canon, cat = self._lookup[best[0]]
                    return ComponentMatch(raw=raw, canonical=canon, category=cat, matched_via="fuzzy", score=best[1] / 100.0)
        except ImportError:
            pass

        return ComponentMatch(raw=raw, canonical=raw, category=None, matched_via="none", score=0.0)

    def canonicalize_list(self, names: Optional[List[str]]) -> List[ComponentMatch]:
        return [self.canonicalize(n) for n in (names or []) if str(n).strip()]

    @property
    def n_terms(self) -> int:
        return len(self._lookup)
