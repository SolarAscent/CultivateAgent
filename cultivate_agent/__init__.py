"""CultivateAgent — a goal-conditioned, medium-centered literature-mining agent
for culture-medium optimization in cultivated meat.

Pipeline (sequential, with an optional verifier loop):

    ingest -> triage -> extract -> normalize -> knowledge base -> retrieve -> design

See README.md and docs/ARCHITECTURE.md for the full design and its grounding in
ReactionSeek (Nature Communications, 2026) and the project record.
"""

from .config import Config, load_config

__version__ = "0.1.0"
__all__ = ["Config", "load_config", "__version__"]
