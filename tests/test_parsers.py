import pytest

from agent.parsers import match_thought, parse_thought, match_patch, parse_patch


@pytest.mark.parametrize(
    "line, expected_inner",
    [
        ("some text Thought[Remove the line that incorrectly returns True when two numbers are closer than the threshold.]",
         "Remove the line that incorrectly returns True when two numbers are closer than the threshold."),
        ("Thought[Remove the line that incorrectly returns True when two numbers are closer than the threshold.]",
         "Remove the line that incorrectly returns True when two numbers are closer than the threshold."),
        ("Thought: keep it simple", "keep it simple"),
        ("foo\nThought: final wins\nbar", "final wins"),
    ],
)
def test__match_thought(line, expected_inner):
    inner, matched, name = match_thought(line)
    assert name == "Thought"
    assert expected_inner in inner
    assert "Thought" in matched


@pytest.mark.parametrize(
    "block, expected",
    [
        ('Thought["Hello"]', "Hello"),
        ("Thought['Hi there']", "Hi there"),
        ("Thought[Just do it]", "Just do it"),
        ("Thought: Single line", "Single line"),
    ],
)
def test__parse_thought_accepts_quoted_and_unquoted(block, expected):
    kind, payload, matched = parse_thought(block)
    assert kind == "Thought"
    assert payload["text"] == expected
    assert "Thought" in matched


@pytest.mark.parametrize(
    "block",
    [
        "Something[content]",  # wrong action
        "Thought[123",  # no closing bracket
        "",  # empty
    ],
)
def test__parse_thought_invalid(block):
    with pytest.raises(ValueError):
        parse_thought(block)


@pytest.mark.parametrize(
    "block, expected",
    [
        ('Patch[{"start":4,"end":9,"text":"replacement"}]', (4, 9, "replacement")),
        ('Patch: {"start": 1, "end": 3, "text": "x"}', (1, 3, "x")),
        ('Patch {"start":"2","end":"5","text":"ok"}', (2, 5, "ok")),
    ],
)
def test__parse_patch_ok(block, expected):
    kind, args, matched = parse_patch(block)
    assert kind == "Patch"
    assert args["start"] == expected[0] and args["end"] == expected[1]
    assert args["text"] == expected[2]
    assert isinstance(args.get("nb_indents", 0), int)


@pytest.mark.parametrize(
    "block",
    [
        'Patch[{"end":3,"text":"x"}]',  # missing start
        'Patch[{"start":1,"text":"x"}]',  # missing end
        'Patch[{"start":1,"end":3}]',  # missing text
        'Patch[{"start":"a","end":3,"text":"x"}]',  # non-int start
        'Patch[{"start":1,"end":"b","text":"x"}]',  # non-int end
        "Patch[]",  # not JSON object
        "Patch[[]]",  # not dict
    ],
)
def test__parse_patch_invalid(block):
    with pytest.raises(ValueError):
        parse_patch(block)


def test_parse_then_patch_roundtrip_with_matchers():
    messy = """
    random chatter
    Patch: {"start": 4, "end": 9, "text": "replacement"}
    some middle text
    Patch: {"start": 1, "end": 3, "text": "ignore this one"}
    """
    inner, matched, name = match_patch(messy)
    assert name == "Patch"
    assert inner.strip().startswith("{") and inner.strip().endswith("}")
    kind, args, matched2 = parse_patch(matched)
    assert kind == "Patch"
    assert args["start"] == 4 and args["end"] == 9 and args["text"] == "replacement"


def test_parse_then_thought_roundtrip_with_matchers():
    messy = """
    preface
    Thought: Keep patches minimal and focused.
    postface
    """
    inner, matched, name = match_thought(messy)
    assert name == "Thought"
    kind, payload, matched2 = parse_thought(matched)
    assert kind == "Thought"
    assert payload["text"] == "Keep patches minimal and focused."
