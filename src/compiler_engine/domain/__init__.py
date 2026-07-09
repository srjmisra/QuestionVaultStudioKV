from compiler_engine.domain.answer_ir import AnswerIR, AnswerOption
from compiler_engine.domain.canonical_knowledge_object import (
    CanonicalKnowledgeObject,
    Provenance,
)
# DEPRECATED, UNUSED — see compiler_engine.domain.document_ast module docstring.
from compiler_engine.domain.document_ast import ASTNode, ASTNodeType, BoundingBox, DocumentAST
from compiler_engine.domain.educational_analysis import (
    BloomLevel,
    DifficultyLevel,
    EducationalAnalysis,
)
from compiler_engine.domain.question_ir import QuestionIR
from compiler_engine.domain.taxonomy import Taxonomy, TaxonomyNode
from compiler_engine.domain.validation_report import (
    ValidationIssue,
    ValidationReport,
    ValidationSeverity,
)

__all__ = [
    "ASTNode",
    "ASTNodeType",
    "AnswerIR",
    "AnswerOption",
    "BloomLevel",
    "BoundingBox",
    "CanonicalKnowledgeObject",
    "DifficultyLevel",
    "DocumentAST",
    "EducationalAnalysis",
    "Provenance",
    "QuestionIR",
    "Taxonomy",
    "TaxonomyNode",
    "ValidationIssue",
    "ValidationReport",
    "ValidationSeverity",
]
