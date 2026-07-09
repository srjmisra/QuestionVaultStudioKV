"""Document AST: a structural parse tree, originally modeled for a PDF the Python
engine would parse itself.

DEPRECATED, UNUSED: as of the Gemini JSON Import architecture change, the Python
engine never reads the original PDF — Gemini does, and hands over an already
question-shaped ``paper.json``. Nothing in the pipeline produces or consumes a
DocumentAST today. It is kept, not deleted, because Gemini's output may still
carry structural information worth preserving in a similar shape (page numbers,
question boundaries, asset references, logical blocks) — that will be decided
after the real ``paper.json`` schema has been reviewed. Do not build new
functionality against this model until that decision is made.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from compiler_engine.core.base_model import CompilerBaseModel
from compiler_engine.core.schema_versions import CURRENT_SCHEMA_VERSIONS


class ASTNodeType(str, Enum):
    PAGE = "page"
    HEADING = "heading"
    PARAGRAPH = "paragraph"
    LIST = "list"
    LIST_ITEM = "list_item"
    TABLE = "table"
    TABLE_ROW = "table_row"
    TABLE_CELL = "table_cell"
    IMAGE = "image"
    TEXT_RUN = "text_run"


class BoundingBox(CompilerBaseModel):
    """Position of a node on its page, in PDF points."""

    page_number: int = Field(ge=1)
    x: float
    y: float
    width: float = Field(ge=0)
    height: float = Field(ge=0)


class ASTNode(CompilerBaseModel):
    node_id: str
    node_type: ASTNodeType
    text: str | None = None
    bounding_box: BoundingBox | None = None
    children: tuple["ASTNode", ...] = ()


class DocumentAST(CompilerBaseModel):
    """Root artifact for one compiled source document."""

    schema_version: str = CURRENT_SCHEMA_VERSIONS["document_ast"]
    document_id: str
    source_file: str
    page_count: int = Field(ge=1)
    root_nodes: tuple[ASTNode, ...]
    generated_at: datetime
