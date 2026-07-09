from compiler_engine.canonical_knowledge_object_generation.checksum import compute_checksum
from compiler_engine.paper_import.schema import RawContent, RawOption, TextBlock


def _content(text: str) -> RawContent:
    return RawContent(blocks=(TextBlock(block_type="text", value=text),))


def test_identical_content_produces_the_same_checksum():
    a = compute_checksum(_content("What is 2+2?"), None)
    b = compute_checksum(_content("What is 2+2?"), None)
    assert a == b


def test_different_text_produces_a_different_checksum():
    a = compute_checksum(_content("What is 2+2?"), None)
    b = compute_checksum(_content("What is 2+3?"), None)
    assert a != b


def test_checksum_does_not_depend_on_paper_or_question_identity():
    # The checksum function's signature doesn't even accept a paper_id/question_id --
    # this test documents that guarantee at the call site.
    a = compute_checksum(_content("Same question"), None)
    b = compute_checksum(_content("Same question"), None)
    assert a == b


def test_block_order_is_meaningful_and_affects_the_checksum():
    two_blocks_ab = RawContent(
        blocks=(TextBlock(block_type="text", value="A"), TextBlock(block_type="text", value="B"))
    )
    two_blocks_ba = RawContent(
        blocks=(TextBlock(block_type="text", value="B"), TextBlock(block_type="text", value="A"))
    )
    assert compute_checksum(two_blocks_ab, None) != compute_checksum(two_blocks_ba, None)


def test_no_text_normalization_even_a_single_character_difference_matters():
    a = compute_checksum(_content("What is 2+2? "), None)  # trailing space
    b = compute_checksum(_content("What is 2+2?"), None)
    assert a != b


def test_options_participate_in_the_checksum():
    options_a = (RawOption(option_id="opt_a", display_order=1, blocks=(TextBlock(block_type="text", value="4"),)),)
    options_b = (RawOption(option_id="opt_a", display_order=1, blocks=(TextBlock(block_type="text", value="5"),)),)
    content = _content("What is 2+2?")
    assert compute_checksum(content, options_a) != compute_checksum(content, options_b)


def test_presence_or_absence_of_options_changes_the_checksum():
    content = _content("What is 2+2?")
    options = (RawOption(option_id="opt_a", display_order=1, blocks=(TextBlock(block_type="text", value="4"),)),)
    assert compute_checksum(content, None) != compute_checksum(content, options)


def test_empty_options_tuple_and_none_are_treated_the_same():
    content = _content("What is 2+2?")
    assert compute_checksum(content, None) == compute_checksum(content, ())
