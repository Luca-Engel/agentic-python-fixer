import json

import pytest

from agent.react_loop import match_thought, _parse_thought, match_patch, _parse_patch, parse_action


@pytest.mark.parametrize(
    "line, expected_inner",
    [
        (
                "some text Thought[Remove the line that incorrectly returns True when two numbers are closer than the threshold.]",
                "Remove the line that incorrectly returns True when two numbers are closer than the threshold.",
        ),
        (
                "Thought[Remove the line that incorrectly returns True when two numbers are closer than the threshold.]",
                "Remove the line that incorrectly returns True when two numbers are closer than the threshold.",
        ),
        (
                "Thought: Remove the line that incorrectly returns True when two numbers are closer than the threshold.",
                "Remove the line that incorrectly returns True when two numbers are closer than the threshold.",
        ),
        (
                "some text Thought: Remove the line that incorrectly returns True when two numbers are closer than the threshold.",
                "Remove the line that incorrectly returns True when two numbers are closer than the threshold.",
        ),
    ],
)
def test_match_thought_examples(line, expected_inner):
    inner, matched, name = match_thought(line)
    assert name == "Thought"
    assert inner.strip() == expected_inner
    assert "Thought" in matched


def test_match_thought_prefers_last_occurrence_from_bottom():
    # There are two Thought occurrences; function should pick the lowest one
    text = """
    prefix
    Thought[First one]
    some middle text
    Thought: Second one
    """
    inner, matched, name = match_thought(text)
    assert name == "Thought"
    assert inner.strip() == "Second one"
    assert matched.endswith("Second one")


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
    kind, payload, matched = _parse_thought(block)
    assert kind == "Thought"
    assert payload["text"] == expected
    assert "Thought" in matched


@pytest.mark.parametrize(
    "block",
    [
        "Something[content]",  # wrong action for this stage
        "Thought[123",  # no closing bracket
    ],
)
def test__parse_thought_rejects_invalid(block):
    with pytest.raises(ValueError):
        _parse_thought(block)


@pytest.mark.parametrize(
    "line",
    [
        'some text Patch[{"start":0,"end":10,"text":"fix"}]',
        'Patch[{"start":5,"end":8,"text":"change"}]',
        'Patch: {"start":1, "end":2, "text": "t"}',
        'some text Patch: {"start":2, "end":3, "text":"x"}',
    ],
)
def test_match_patch_examples(line):
    inner, matched = match_patch(line)
    assert matched
    # Must be parsable JSON with required fields
    args = json.loads(inner)
    assert {"start", "end", "text"} <= set(args)


def test_match_patch_picks_bottom_most():
    # There are two Patch occurrences; function should pick the lowest one
    text = """
    Patch[{"start":0,"end":1,"text":"top"}]
    some stuff
    Patch[{"start":2,"end":3,"text":"bottom"}]
    """
    inner, matched = match_patch(text)
    args = json.loads(inner)
    assert args["text"] == "bottom"


def test__parse_patch_happy_path_and_coercions():
    block = 'Patch[{"start":"1","end":"3","text":"new code"}]'
    kind, args, matched = _parse_patch(block)
    assert kind == "Patch"
    assert args["start"] == 1 and args["end"] == 3
    assert isinstance(args.get("nb_indents", 0), int)
    assert args["text"] == "new code"


@pytest.mark.parametrize(
    "block",
    [
        'Patch[{"end":3,"text":"x"}]',  # missing start
        'Patch[{"start":1,"text":"x"}]',  # missing end
        'Patch[{"start":1,"end":3}]',  # missing text
        'Patch[{"start":"a","end":3,"text":"x"}]',  # non-int start
        'Patch[{"start":1,"end":"b","text":"x"}]',  # non-int end
        "Patch[]",  # not a JSON object
        "Patch[[]]",  # not a dict
    ],
)
def test__parse_patch_invalid(block):
    with pytest.raises(ValueError):
        _parse_patch(block)


def test_parse_action_thought():
    name, args, matched = parse_action('Thought[Do a thing]')
    assert name == "Thought"
    assert args == {}  # Thought returns empty args here
    assert "Thought[" in matched


def test_parse_action_patch():
    block = 'Patch[{"start":0,"end":2,"text":"xx"}]'
    name, args, matched = parse_action(block)
    assert name == "Patch"
    assert args == {"start": 0, "end": 2, "text": "xx"}


def test_parse_action_unknown_tool_raises():
    with pytest.raises(ValueError):
        parse_action("Run[{}]")


# ----------------------------
# Robustness / integration-like sanity
# ----------------------------
def test_parse_then_patch_roundtrip_with_matchers():
    # Simulate LLM output that includes extra lines; we use the matchers then the strict parsers
    messy = """
    random chatter
    Patch: {"start": 4, "end": 9, "text": "replacement"}
    extra trailing
    """
    inner, matched = match_patch(messy)
    kind, args, matched2 = _parse_patch(matched)
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
    kind, payload, matched2 = _parse_thought(matched)
    assert kind == "Thought"
    assert payload["text"] == "Keep patches minimal and focused."
