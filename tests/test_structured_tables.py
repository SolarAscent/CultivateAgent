import hashlib

from cultivate_agent.schema import structured_paper_from_grobid_tei_xml


JATS_TABLE = """<?xml version="1.0" encoding="UTF-8"?>
<article>
  <body>
    <table-wrap id="stats-1">
      <label>Table 2</label>
      <caption><p>Proliferation at day 7.</p></caption>
      <table>
        <thead>
          <tr><th rowspan="2" scope="col">Group</th><th colspan="2" scope="colgroup">Cell count</th></tr>
          <tr><th scope="col">Mean</th><th scope="col">SD</th></tr>
        </thead>
        <tbody>
          <tr><th scope="row">Control</th><td>1.0</td><td>0.2</td></tr>
          <tr><th scope="row">FGF2</th><td>2.0</td><td>0.4</td></tr>
        </tbody>
      </table>
      <table-wrap-foot><fn id="n1"><label>a</label><p>n = 4 independent cultures.</p></fn></table-wrap-foot>
    </table-wrap>
  </body>
</article>"""


def test_jats_table_preserves_stable_cells_spans_footnotes_and_hash():
    paper = structured_paper_from_grobid_tei_xml("p1", JATS_TABLE)
    table = paper.tables[0]

    assert table.table_id == "T1"
    assert table.source_table_id == "stats-1"
    assert table.row_count == 4
    assert table.column_count == 3
    assert table.source_sha256 == hashlib.sha256(JATS_TABLE.encode()).hexdigest()
    assert table.footnotes == ["a n = 4 independent cultures."]

    group_header = table.cell("T1.R1.C1")
    assert group_header is not None
    assert group_header.text == "Group"
    assert group_header.is_header is True
    assert group_header.row_span == 2
    assert group_header.scope == "col"

    mean_header = table.cell("T1.R2.C2")
    assert mean_header is not None and mean_header.text == "Mean"
    assert table.cell("T1.R4.C2").text == "2.0"


def test_jats_table_serialization_keeps_pointers_separate_from_caption():
    paper = structured_paper_from_grobid_tei_xml("p1", JATS_TABLE)
    table = paper.tables[0]

    assert table.caption == "Table 2 Proliferation at day 7."
    assert "2.0" not in table.caption
    assert "[T1.R4.C2] 2.0" in table.as_text()
    assert "[footnote] a n = 4 independent cultures." in table.as_text()
    assert "[T1.R4.C2] 2.0" in paper.all_text()


def test_jats_table_pointer_is_stable_across_repeated_parses():
    first = structured_paper_from_grobid_tei_xml("p1", JATS_TABLE).tables[0]
    second = structured_paper_from_grobid_tei_xml("p1", JATS_TABLE).tables[0]

    assert [cell.model_dump() for cell in first.cells] == [cell.model_dump() for cell in second.cells]
    assert first.source_sha256 == second.source_sha256
