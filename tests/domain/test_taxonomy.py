import pytest

from compiler_engine.core.errors import SchemaError
from compiler_engine.domain.taxonomy import Taxonomy, TaxonomyNode


def _sample_taxonomy() -> Taxonomy:
    subtopic = TaxonomyNode(node_id="cs-prog-loops", name="Loops", level=2)
    topic = TaxonomyNode(node_id="cs-prog", name="Programming", level=1, children=(subtopic,))
    subject = TaxonomyNode(node_id="cs", name="Computer Science", level=0, children=(topic,))
    return Taxonomy(taxonomy_id="kv-coders", name="KV Coders Subject Taxonomy", roots=(subject,))


def test_builds_a_nested_taxonomy():
    taxonomy = _sample_taxonomy()
    assert taxonomy.roots[0].children[0].children[0].name == "Loops"


def test_round_trips_through_json():
    taxonomy = _sample_taxonomy()
    assert Taxonomy.from_json(taxonomy.to_json()) == taxonomy


def test_rejects_missing_roots():
    with pytest.raises(SchemaError):
        Taxonomy.from_dict({"taxonomy_id": "kv-coders", "name": "KV Coders Subject Taxonomy"})
