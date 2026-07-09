from datetime import datetime, timezone

import pytest

from compiler_engine.core.errors import SchemaError
from compiler_engine.domain.document_ast import ASTNode, ASTNodeType, BoundingBox, DocumentAST


def _sample_ast() -> DocumentAST:
    leaf = ASTNode(node_id="n2", node_type=ASTNodeType.TEXT_RUN, text="Hello")
    paragraph = ASTNode(
        node_id="n1",
        node_type=ASTNodeType.PARAGRAPH,
        bounding_box=BoundingBox(page_number=1, x=0, y=0, width=100, height=20),
        children=(leaf,),
    )
    return DocumentAST(
        document_id="doc1",
        source_file="paper.pdf",
        page_count=1,
        root_nodes=(paragraph,),
        generated_at=datetime.now(timezone.utc),
    )


def test_builds_a_nested_ast():
    ast = _sample_ast()
    assert ast.root_nodes[0].children[0].text == "Hello"


def test_round_trips_through_json():
    ast = _sample_ast()
    assert DocumentAST.from_json(ast.to_json()) == ast


def test_rejects_zero_page_count():
    with pytest.raises(SchemaError):
        DocumentAST.from_dict(
            {
                "document_id": "doc1",
                "source_file": "paper.pdf",
                "page_count": 0,
                "root_nodes": [],
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
        )


def test_rejects_unknown_node_type():
    with pytest.raises(SchemaError):
        ASTNode.from_dict({"node_id": "n1", "node_type": "not_a_real_type"})
