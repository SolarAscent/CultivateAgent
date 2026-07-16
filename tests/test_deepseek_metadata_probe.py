import csv
import json

import pytest

from cultivate_agent.evaluate.deepseek_metadata_probe import (
    MetadataCanaryItem,
    load_metadata_canary,
    run_metadata_probe,
    validate_response,
)


def _item(item_id, mismatch):
    return MetadataCanaryItem(
        item_id=item_id,
        title_record_id=f"T{item_id}",
        abstract_record_id=f"A{item_id}" if mismatch else f"T{item_id}",
        title=f"Title {item_id}", abstract=f"Abstract {item_id}",
        expected_mismatch=mismatch,
    )


def test_load_metadata_canary_resolves_exact_doi_title_and_abstract(tmp_path):
    corpus = tmp_path / "corpus.tsv"
    corpus.write_text(
        "record_id\ttitle\tdoi\nR1\tA Study: One\t10.1/a\nR2\tStudy Two\t10.1/b\n",
        encoding="utf-8",
    )
    zotero = tmp_path / "zotero.csv"
    with zotero.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["Title", "DOI", "Abstract Note"])
        writer.writeheader()
        writer.writerow({"Title": "A Study - One", "DOI": "10.1/a", "Abstract Note": "First"})
        writer.writerow({"Title": "Study Two", "DOI": "10.1/b", "Abstract Note": "Second"})
    spec = tmp_path / "spec.tsv"
    spec.write_text(
        "item_id\ttitle_record_id\tabstract_record_id\texpected_mismatch\n"
        "M1\tR1\tR2\tyes\nM2\tR2\tR2\tno\n",
        encoding="utf-8",
    )

    items = load_metadata_canary(
        spec, corpus_manifest_path=corpus, zotero_csv_path=zotero
    )
    assert items[0].title == "A Study: One"
    assert items[0].abstract == "Second"
    assert items[0].expected_mismatch is True
    assert items[1].expected_mismatch is False


def test_response_schema_allows_only_abstract_pointers():
    items = [_item("M1", True)]
    selected, issues = validate_response(
        '{"candidates":[{"id":"M1","fields":["abstract"]}]}', items
    )
    assert selected == {"M1"}
    assert not issues

    _, issues = validate_response(
        '{"candidates":[{"id":"M1","fields":["abstract"],"value":"invented"}]}', items
    )
    assert issues


def test_repeated_probe_passes_and_resumes_without_calls(tmp_path):
    items = [_item("M1", True), _item("M2", False), _item("M3", True), _item("M4", False)]
    calls = []

    def caller(prompt, max_output_tokens):
        calls.append(prompt)
        payload = json.loads(prompt.split("INPUT_JSON:\n", 1)[1])
        selected = [
            {"id": row["id"], "fields": ["abstract"]}
            for row in payload["records"] if row["id"] in {"M1", "M3"}
        ]
        return json.dumps({"candidates": selected}), {
            "prompt_tokens": 80, "completion_tokens": 20, "total_tokens": 100,
        }

    kwargs = dict(
        checkpoint_dir=tmp_path / "cp", model="deepseek-v4-flash", repeats=3,
        batch_size=2, max_requests=6, max_total_tokens=2000, max_output_tokens=100,
    )
    first = run_metadata_probe(items, caller=caller, **kwargs)
    assert first.gate_pass
    assert first.repeat_recalls == (1.0, 1.0, 1.0)
    assert first.repeat_precisions == (1.0, 1.0, 1.0)
    assert len(calls) == 6

    def no_call(*_):
        pytest.fail("checkpoint resume should not call the provider")

    resumed = run_metadata_probe(items, caller=no_call, **kwargs)
    assert resumed == first


def test_flag_everything_fails_work_reduction_precision_gate(tmp_path):
    items = [_item("M1", True), _item("M2", False), _item("M3", False), _item("M4", False)]

    def caller(prompt, _):
        payload = json.loads(prompt.split("INPUT_JSON:\n", 1)[1])
        return json.dumps({"candidates": [
            {"id": row["id"], "fields": ["abstract"]} for row in payload["records"]
        ]}), 50

    result = run_metadata_probe(
        items, checkpoint_dir=tmp_path / "cp", model="deepseek-v4-flash", repeats=3,
        batch_size=4, max_requests=3, max_total_tokens=1000, max_output_tokens=100,
        caller=caller,
    )
    assert result.repeat_recalls == (1.0, 1.0, 1.0)
    assert result.repeat_precisions == (0.25, 0.25, 0.25)
    assert not result.gate_pass
