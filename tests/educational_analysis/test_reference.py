from compiler_engine.domain.taxonomy import Taxonomy, TaxonomyNode
from compiler_engine.educational_analysis.reference import build_curriculum_index, question_type_ids


def _curriculum() -> Taxonomy:
    return Taxonomy(
        taxonomy_id="curriculum",
        name="test curriculum",
        roots=(
            TaxonomyNode(
                node_id="unit_1",
                name="Unit 1",
                level=0,
                children=(
                    TaxonomyNode(
                        node_id="ch_x",
                        name="Chapter X",
                        level=1,
                        children=(
                            TaxonomyNode(
                                node_id="top_x",
                                name="Topic X",
                                level=2,
                                children=(
                                    TaxonomyNode(node_id="con_x1", name="Concept X1", level=3),
                                    TaxonomyNode(node_id="con_x2", name="Concept X2", level=3),
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def test_indexes_chapters_topics_and_concepts_by_id():
    index = build_curriculum_index(_curriculum())
    assert index.chapter_ids == frozenset({"ch_x"})
    assert index.topic_ids == frozenset({"top_x"})
    assert index.concept_ids == frozenset({"con_x1", "con_x2"})


def test_indexes_parent_relationships():
    index = build_curriculum_index(_curriculum())
    assert index.chapter_of_topic == {"top_x": "ch_x"}
    assert index.topic_of_concept == {"con_x1": "top_x", "con_x2": "top_x"}


def test_depth_is_derived_from_tree_position_not_the_level_field():
    # node.level deliberately wrong (says 0, but it's nested 3 deep) -- the index
    # must still classify it correctly, by actual position in the tree.
    curriculum = Taxonomy(
        taxonomy_id="curriculum",
        name="test",
        roots=(
            TaxonomyNode(
                node_id="unit_1",
                name="Unit",
                level=0,
                children=(
                    TaxonomyNode(
                        node_id="ch_x",
                        name="Chapter",
                        level=0,
                        children=(
                            TaxonomyNode(
                                node_id="top_x",
                                name="Topic",
                                level=0,
                                children=(TaxonomyNode(node_id="con_x", name="Concept", level=0),),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )
    index = build_curriculum_index(curriculum)
    assert index.chapter_ids == frozenset({"ch_x"})
    assert index.topic_ids == frozenset({"top_x"})
    assert index.concept_ids == frozenset({"con_x"})


def test_empty_curriculum_produces_empty_index():
    empty = Taxonomy(taxonomy_id="curriculum", name="empty", roots=())
    index = build_curriculum_index(empty)
    assert index.chapter_ids == frozenset()
    assert index.topic_ids == frozenset()
    assert index.concept_ids == frozenset()


def test_question_type_ids_reads_flat_roots():
    question_types = Taxonomy(
        taxonomy_id="question_types",
        name="question types",
        roots=(
            TaxonomyNode(node_id="qt_mcq", name="MCQ", level=0),
            TaxonomyNode(node_id="qt_sql_query", name="SQL Query", level=0),
        ),
    )
    assert question_type_ids(question_types) == frozenset({"qt_mcq", "qt_sql_query"})
