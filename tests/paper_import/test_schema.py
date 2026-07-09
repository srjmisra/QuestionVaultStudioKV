from pathlib import Path

import pytest

from compiler_engine.core.errors import SchemaError
from compiler_engine.paper_import.schema import (
    CodeBlock,
    PaperImport,
    RawContent,
    TableBlock,
    TextBlock,
)

REAL_PAPER_PATH = Path(__file__).resolve().parents[2] / "imports" / "paper.json"


def test_parses_the_real_gold_standard_paper():
    paper = PaperImport.from_json(REAL_PAPER_PATH.read_text(encoding="utf-8"))

    assert paper.schema_version == "1.0"
    assert paper.paper_id == "cbse_2025_26_xii_083_set_a"
    assert paper.paper_metadata.class_name == "XII"
    assert len(paper.questions) == 49
    assert len(paper.sections) == 5


def test_round_trips_the_real_paper_through_json():
    paper = PaperImport.from_json(REAL_PAPER_PATH.read_text(encoding="utf-8"))
    assert PaperImport.from_json(paper.to_json()) == paper


def test_class_alias_serializes_back_to_the_reserved_keyword():
    paper = PaperImport.from_json(REAL_PAPER_PATH.read_text(encoding="utf-8"))
    assert '"class":' in paper.to_json()
    assert '"class_name"' not in paper.to_json()


def test_content_blocks_parse_into_their_discriminated_type():
    paper = PaperImport.from_json(REAL_PAPER_PATH.read_text(encoding="utf-8"))
    blocks_by_type = {}
    for question in paper.questions:
        for block in question.content.blocks:
            blocks_by_type[type(block)] = block

    assert isinstance(blocks_by_type[TextBlock], TextBlock)
    assert isinstance(blocks_by_type[CodeBlock], CodeBlock)
    assert isinstance(blocks_by_type[TableBlock], TableBlock)


def test_unknown_block_type_is_rejected():
    with pytest.raises(SchemaError):
        RawContent.from_dict({"blocks": [{"block_type": "video", "value": "x"}]})


def test_table_block_missing_rows_is_rejected():
    with pytest.raises(SchemaError):
        TableBlock.from_dict({"block_type": "table", "headers": ["a"]})


def test_missing_required_field_is_rejected():
    with pytest.raises(SchemaError):
        PaperImport.from_dict({"schema_version": "1.0", "paper_id": "p1"})


def test_empty_paper_id_is_rejected():
    with pytest.raises(SchemaError):
        PaperImport.from_dict(
            {
                "schema_version": "1.0",
                "paper_id": "",
                "paper_metadata": {
                    "board": "CBSE",
                    "conducting_body": "X",
                    "region": "Y",
                    "examination": "Z",
                    "academic_session": "2025-26",
                    "class": "XII",
                    "subject": "CS",
                    "subject_code": "083",
                    "duration": "3 HOURS",
                    "maximum_marks": 70,
                    "set": "SET A",
                    "total_questions": 0,
                    "total_sections": 0,
                },
                "sections": [],
                "questions": [],
            }
        )
