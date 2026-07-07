#!/usr/bin/env python3
"""Compare q-ParEGO and BoTorch qNEHVI on the synthetic medium benchmark."""

from __future__ import annotations

import argparse
import contextlib
import io
from pathlib import Path
from typing import Dict, List

from cultivate_agent.optimize import MultiObjectiveBO, SyntheticMediumObjective, default_medium_space


def run_backend(backend: str, *, seed: int, rounds: int, batch: int, pool_size: int) -> Dict[str, float]:
    space = default_medium_space()
    obj = SyntheticMediumObjective(noise=0.0, seed=seed)
    mobo = MultiObjectiveBO(space, obj.objectives, backend=backend, seed=seed)
    init = space.sample(max(5, len(obj.objectives) + 3), seed=seed)
    mobo.tell(init, obj.evaluate_many(init))
    start = mobo.hypervolume()
    for _ in range(rounds):
        # BoTorch currently prints numerical guidance warnings for qNEHVI. Keep
        # benchmark output readable; the report documents the warning.
        with contextlib.redirect_stderr(io.StringIO()):
            suggestions = mobo.ask(
                batch,
                pool_size=pool_size,
                preference_weights={"proliferation": 0.6, "cost": 0.4},
            )
        forms = [s.formulation for s in suggestions]
        mobo.tell(forms, obj.evaluate_many(forms))
    final = mobo.hypervolume()
    return {"seed": seed, "backend": backend, "start_hv": start, "final_hv": final, "delta_hv": final - start}


def markdown_table(rows: List[Dict[str, object]], columns: List[str]) -> str:
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(c, "")) for c in columns) + " |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--batch", type=int, default=3)
    parser.add_argument("--pool-size", type=int, default=96)
    parser.add_argument("--out", default="docs/OPTIMIZATION_BENCHMARK.md")
    args = parser.parse_args()

    rows: List[Dict[str, object]] = []
    for seed in args.seeds:
        seed_rows = [
            run_backend("gp", seed=seed, rounds=args.rounds, batch=args.batch, pool_size=args.pool_size),
            run_backend("botorch", seed=seed, rounds=args.rounds, batch=args.batch, pool_size=args.pool_size),
        ]
        max_final = max(r["final_hv"] for r in seed_rows) or 1.0
        for r in seed_rows:
            rows.append({
                "seed": seed,
                "backend": "q-ParEGO" if r["backend"] == "gp" else "qNEHVI",
                "start_hv": round(r["start_hv"], 3),
                "final_hv": round(r["final_hv"], 3),
                "delta_hv": round(r["delta_hv"], 3),
                "normalized_final_hv": round(r["final_hv"] / max_final, 3),
            })

    by_backend: Dict[str, List[float]] = {}
    for row in rows:
        by_backend.setdefault(str(row["backend"]), []).append(float(row["normalized_final_hv"]))
    summary = [
        {
            "backend": backend,
            "mean_normalized_final_hv": round(sum(vals) / len(vals), 3),
            "n_seeds": len(vals),
        }
        for backend, vals in sorted(by_backend.items())
    ]

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "# MOBO Backend Benchmark\n\n"
        "Synthetic benchmark only; real objective values must come from wet-lab `tell()` calls. "
        f"Settings: seeds={args.seeds}, rounds={args.rounds}, batch={args.batch}, pool_size={args.pool_size}.\n\n"
        "BoTorch 0.18.1 warns that legacy `qNoisyExpectedHypervolumeImprovement` has numerical issues "
        "and recommends `qLogNoisyExpectedHypervolumeImprovement`; this project still labels the path "
        "qNEHVI because that is the implemented acquisition today.\n\n"
        "## Per-Seed Results\n\n"
        + markdown_table(rows, ["seed", "backend", "start_hv", "final_hv", "delta_hv", "normalized_final_hv"])
        + "\n\n## Summary\n\n"
        + markdown_table(summary, ["backend", "mean_normalized_final_hv", "n_seeds"])
        + "\n",
        encoding="utf-8",
    )
    print(f"+ wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
