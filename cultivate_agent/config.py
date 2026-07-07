"""Configuration loading (YAML + .env) and typed settings.

``load_config()`` reads ``config/config.yaml`` (falling back to
``config/config.example.yaml``), loads ``.env`` for API keys, and returns a
typed :class:`Config`. Modules receive a ``Config`` rather than reading globals,
so tests can build one in-memory.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None  # type: ignore


class ProjectCfg(BaseModel):
    name: str = "CultivateAgent"
    data_dir: str = "data"
    kb_path: str = "data/knowledge_base.sqlite"


class LLMCfg(BaseModel):
    provider: str = "openai"
    model: str = "gpt-5.4"
    temperature: float = 0.0
    max_tokens: int = 4096
    request_timeout_s: int = 120
    max_retries: int = 4
    triage_model: Optional[str] = None


class IngestCfg(BaseModel):
    bibtex_path: str = "data/library.bib"
    extract_page_images: bool = True
    extract_figures: bool = True
    extract_tables: bool = True
    page_image_dpi: int = 150


class ExtractCfg(BaseModel):
    triage_blocks: List[str] = Field(default_factory=lambda: ["A", "B", "C", "J", "M"])
    full_blocks: List[str] = Field(default_factory=lambda: ["D", "E", "F", "G", "H", "I", "K", "L"])
    require_evidence: bool = True
    max_context_chars: int = 60000


class RetrieveCfg(BaseModel):
    backend: str = "bm25"
    top_k: int = 12
    embedding_model: str = "text-embedding-3-small"


class DesignCfg(BaseModel):
    objectives: List[str] = Field(
        default_factory=lambda: ["proliferation", "cost", "differentiation_retention", "tissue_readiness"]
    )
    presets: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    actionable_variables: List[str] = Field(default_factory=list)


class Config(BaseModel):
    project: ProjectCfg = Field(default_factory=ProjectCfg)
    llm: LLMCfg = Field(default_factory=LLMCfg)
    ingest: IngestCfg = Field(default_factory=IngestCfg)
    extract: ExtractCfg = Field(default_factory=ExtractCfg)
    retrieve: RetrieveCfg = Field(default_factory=RetrieveCfg)
    design: DesignCfg = Field(default_factory=DesignCfg)

    # Resolved at load time.
    root: str = "."

    # ---- derived paths ----
    @property
    def data_path(self) -> Path:
        return (Path(self.root) / self.project.data_dir).resolve()

    @property
    def papers_dir(self) -> Path:
        return self.data_path / "papers"

    @property
    def kb_file(self) -> Path:
        return (Path(self.root) / self.project.kb_path).resolve()

    @property
    def ontology_dir(self) -> Path:
        return (Path(self.root) / "config" / "ontology").resolve()

    # ---- LLM client factory ----
    def make_llm_client(self, *, triage: bool = False):
        from .llm import get_client

        model = self.llm.triage_model if (triage and self.llm.triage_model) else self.llm.model
        return get_client(
            self.llm.provider,
            model,
            temperature=self.llm.temperature,
            max_tokens=self.llm.max_tokens,
            max_retries=self.llm.max_retries,
            timeout_s=self.llm.request_timeout_s,
        )


def _find_config(root: Path) -> Optional[Path]:
    for name in ("config/config.yaml", "config/config.example.yaml"):
        p = root / name
        if p.exists():
            return p
    return None


def load_config(path: Optional[str | Path] = None, *, root: Optional[str | Path] = None) -> Config:
    """Load config from ``path`` (or auto-discover), plus ``.env`` for secrets."""
    root_path = Path(root or ".").resolve()

    if load_dotenv is not None:
        env_file = root_path / ".env"
        if env_file.exists():
            load_dotenv(env_file)

    cfg_path = Path(path) if path else _find_config(root_path)
    data: dict = {}
    if cfg_path and Path(cfg_path).exists():
        data = yaml.safe_load(Path(cfg_path).read_text(encoding="utf-8")) or {}

    cfg = Config.model_validate(data)
    cfg.root = str(root_path)
    return cfg
