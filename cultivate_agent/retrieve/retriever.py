"""Evidence retrieval over the knowledge base.

A retriever is what lets the design agent be *grounded*: recommendations cite
real papers rather than the model's memory. The default backend is BM25 (lexical,
no external service, works offline). An embedding backend is provided for when
the OpenAI embeddings API is available; both share one interface so the design
agent does not care which is active.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9\-/]+")


def _tokenize(text: str) -> List[str]:
    return _TOKEN_RE.findall((text or "").lower())


@dataclass
class Document:
    doc_id: str          # paper_id
    text: str            # searchable blob
    title: str = ""


@dataclass
class Hit:
    doc_id: str
    score: float
    title: str
    snippet: str


class Retriever:
    """Interface: ``index(docs)`` then ``search(query, top_k)``."""

    def index(self, docs: Sequence[Document]) -> None:  # pragma: no cover
        raise NotImplementedError

    def search(self, query: str, top_k: int = 10) -> List[Hit]:  # pragma: no cover
        raise NotImplementedError


class BM25Retriever(Retriever):
    def __init__(self):
        self._docs: List[Document] = []
        self._bm25 = None
        self._fallback = None  # simple TF-IDF-ish fallback if rank_bm25 missing

    def index(self, docs: Sequence[Document]) -> None:
        self._docs = list(docs)
        corpus = [_tokenize(d.text) for d in self._docs]
        try:
            from rank_bm25 import BM25Okapi  # type: ignore

            self._bm25 = BM25Okapi(corpus) if corpus else None
        except ImportError:
            self._bm25 = None
            self._fallback = _SimpleTfIdf(corpus)

    def search(self, query: str, top_k: int = 10) -> List[Hit]:
        if not self._docs:
            return []
        q = _tokenize(query)
        qset = set(q)
        if self._bm25 is not None:
            scores = self._bm25.get_scores(q)
        elif self._fallback is not None:
            scores = self._fallback.scores(q)
        else:
            return []
        # Keep docs that share at least one query term. We do NOT filter on
        # ``score > 0``: with small corpora BM25's IDF can go negative for terms
        # that appear in every document, yet those docs are still on-topic. The
        # token-overlap gate removes genuinely irrelevant docs while preserving
        # the relative ranking.
        scored = []
        for d, s in zip(self._docs, scores):
            if qset & set(_tokenize(d.text)):
                scored.append((d, float(s)))
        scored.sort(key=lambda t: t[1], reverse=True)
        return [
            Hit(doc_id=d.doc_id, score=s, title=d.title, snippet=_snippet(d.text, q))
            for d, s in scored[:top_k]
        ]


class _SimpleTfIdf:
    """Dependency-free lexical fallback so retrieval works without rank_bm25."""

    def __init__(self, corpus: List[List[str]]):
        self.corpus = corpus
        self.df: dict = {}
        for doc in corpus:
            for term in set(doc):
                self.df[term] = self.df.get(term, 0) + 1
        self.N = max(len(corpus), 1)

    def _idf(self, term: str) -> float:
        return math.log((self.N + 1) / (self.df.get(term, 0) + 1)) + 1.0

    def scores(self, query: List[str]) -> List[float]:
        out = []
        for doc in self.corpus:
            if not doc:
                out.append(0.0)
                continue
            tf = {}
            for t in doc:
                tf[t] = tf.get(t, 0) + 1
            s = sum((tf.get(t, 0) / len(doc)) * self._idf(t) for t in query)
            out.append(s)
        return out


def _snippet(text: str, query_tokens: List[str], *, width: int = 240) -> str:
    low = text.lower()
    for t in query_tokens:
        i = low.find(t)
        if i >= 0:
            start = max(0, i - width // 2)
            return text[start : start + width].strip()
    return text[:width].strip()


# --------------------------------------------------------------------------- #
# Build a searchable corpus from the knowledge base                           #
# --------------------------------------------------------------------------- #
def build_corpus_from_kb(kb) -> List[Document]:
    """One :class:`Document` per paper, blending the most retrieval-useful fields."""
    docs: List[Document] = []
    for ext in kb.iter_extractions():
        b, m, k = ext.basic_info, ext.medium_info, ext.findings_limitations
        parts = [
            b.title or "",
            "; ".join(ext.fast_triage.species or []),
            m.serum_free_status or "", m.serum_usage or "",
            "; ".join(m.basal_medium or []),
            "growth factors: " + "; ".join(m.growth_factors or []),
            "small molecules: " + "; ".join(m.small_molecules or []),
            "supplements: " + "; ".join(m.hydrolysates_or_extracts or []),
            m.medium_optimization_strategy or "",
            m.cost_reduction_relevance or "",
            k.core_findings or "",
            ext.final_judgment.one_paragraph_reader_summary or "",
            # include verbatim evidence so retrieval can surface exact support
            " ".join(ev.quote for ev in ext.evidence.values()),
        ]
        docs.append(Document(doc_id=ext.paper_id, text="\n".join(p for p in parts if p), title=b.title or ext.paper_id))
    return docs
