from agent.tools import Toolset, get_text_with_indents


def test_empty_string_handled_without_error():
    t = Toolset(".")
    text = ""
    out = get_text_with_indents(1, text)
    assert out == "    \n"


def test_basic_removes_leading_and_adds_indent():
    t = Toolset(".")
    text = "    line1\n    line2\n"
    out = get_text_with_indents(1, text)
    assert out == "    line1\n    line2\n"


def test_partial_line_with_less_indent_kept():
    t = Toolset(".")
    text = "    line1\n  short\n"
    out = get_text_with_indents(1, text)
    # first line has 4 leading spaces removed, second line kept (2 spaces) then global indent added
    assert out == "    line1\n      short\n"


def test_no_leading_spaces():
    t = Toolset(".")
    text = "a\nb\n"
    out = get_text_with_indents(2, text)
    # nb_indents=2 -> 8 spaces prefix each line
    assert out == "        a\n        b\n"


def test_no_leading_spaces_removed_from_b():
    t = Toolset(".")
    text = "a\n    b\n"
    out = get_text_with_indents(2, text)
    # nb_indents=2 -> 8 spaces prefix each line
    assert out == "        a\n            b\n"


def test_internal_blank_lines_preserved():
    t = Toolset(".")
    text = "    a\n\n    b\n"
    out = get_text_with_indents(1, text)
    assert out == "    a\n    \n    b\n"


def test_always_appends_newline():
    t = Toolset(".")
    text = "    a\n    b"  # no trailing newline in input
    out = get_text_with_indents(0, text)
    assert out == "a\nb\n"
