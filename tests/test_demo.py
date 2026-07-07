"""Guard the end-to-end capstone demo (composition of the whole novel pipeline)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_full_pipeline_demo_runs():
    """operators -> evidence synthesis -> KB -> prior -> prior-guided MOBO composes offline."""
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "demo_full_pipeline.py")],
        capture_output=True, text=True, timeout=120, cwd=str(ROOT),
    )
    assert r.returncode == 0, r.stderr
    out = r.stdout
    assert "Evidence synthesis" in out
    assert "P(beneficial|proliferation)" in out
    assert "prior-guided MOBO all composed" in out
