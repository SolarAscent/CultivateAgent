"""Replayability checks for the medium-corpus evaluation bundle."""

from __future__ import annotations

import hashlib
import json

import pytest


def test_medium_eval_artifact_round_trip_is_byte_stable(tmp_path):
    from scripts.evaluate_medium_corpus import write_reports

    artifacts = tmp_path / "artifacts"
    first = tmp_path / "first"
    replay = tmp_path / "replay"

    first_paths = write_reports(
        first,
        provider="mock_gpt",
        agreement_scope="mock",
        artifacts_out=artifacts,
    )
    replay_paths = write_reports(
        replay,
        artifacts_in=artifacts,
    )

    assert (artifacts / "gold.json").is_file()
    assert (artifacts / "manifest.json").is_file()
    assert [path.read_bytes() for path in first_paths] == [
        path.read_bytes() for path in replay_paths
    ]


def test_medium_eval_artifact_rejects_fixture_hash_drift(tmp_path):
    from scripts.evaluate_medium_corpus import write_reports

    artifacts = tmp_path / "artifacts"
    write_reports(tmp_path / "first", artifacts_out=artifacts)
    manifest_path = artifacts / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    first_paper = manifest["paper_ids"][0]
    manifest["source_sha256"][first_paper] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="source hash mismatch"):
        write_reports(tmp_path / "replay", artifacts_in=artifacts)


def test_medium_eval_artifact_rejects_file_tampering(tmp_path):
    from scripts.evaluate_medium_corpus import write_reports

    artifacts = tmp_path / "artifacts"
    write_reports(tmp_path / "first", artifacts_out=artifacts)
    gold_path = artifacts / "gold.json"
    gold_path.write_text(gold_path.read_text(encoding="utf-8") + " ", encoding="utf-8")

    with pytest.raises(ValueError, match="artifact file hash mismatch: gold.json"):
        write_reports(tmp_path / "replay", artifacts_in=artifacts)


def test_medium_eval_artifact_rejects_prediction_order_drift(tmp_path):
    from scripts.evaluate_medium_corpus import write_reports

    artifacts = tmp_path / "artifacts"
    write_reports(tmp_path / "first", artifacts_out=artifacts)
    manifest_path = artifacts / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prediction_name = manifest["prediction_files"]["mock_gpt"]
    prediction_path = artifacts / prediction_name
    predictions = json.loads(prediction_path.read_text(encoding="utf-8"))
    predictions[0], predictions[1] = predictions[1], predictions[0]
    prediction_path.write_text(
        json.dumps(predictions, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest["artifact_sha256"][prediction_name] = hashlib.sha256(
        prediction_path.read_bytes()
    ).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="prediction paper order does not match"):
        write_reports(tmp_path / "replay", artifacts_in=artifacts)


def test_medium_eval_artifact_replay_rejects_live_options(tmp_path):
    from scripts.evaluate_medium_corpus import write_reports

    artifacts = tmp_path / "artifacts"
    write_reports(tmp_path / "first", artifacts_out=artifacts)

    with pytest.raises(ValueError, match="cannot be combined"):
        write_reports(tmp_path / "replay", artifacts_in=artifacts, live_limit=1)
