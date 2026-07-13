# Mock Evaluation Bundle v1

Status: deterministic format/regression exemplar only.

This bundle contains four short cultivated-meat fixture records, one structured
gold file, and predictions from three deterministic mock profiles. It proves
that T1/T2 artifact serialization, integrity checks, and provider-free replay
work across clean checkouts. It does **not** measure GPT, Claude, Gemini, or the
production extraction system and must not support a thesis accuracy claim or a
wet-lab decision.

Generated with:

```bash
python scripts/evaluate_medium_corpus.py \
  --provider mock_gpt \
  --agreement-scope mock \
  --artifacts-out data/evaluation/runs/mock-baseline-v1 \
  --out-dir /tmp/cultivate-mock-baseline-v1
```

Replay with no provider call:

```bash
python scripts/evaluate_medium_corpus.py \
  --artifacts-in data/evaluation/runs/mock-baseline-v1 \
  --out-dir /tmp/cultivate-mock-baseline-v1-replay
```

The manifest restores the original scored provider and agreement scope. Replay
fails if fixture source text, gold/prediction files, paper order, or checksums no
longer match. The gold predates human re-adjudication of the new
`D.culture_stage` and `E.medium_type` fields; those fields remain unfilled.

