import pytest

from agent.patches import SpanPatch, apply_span_patch


def test_replace_middle_single_line():
    src = "a\nb\nc\n"
    p = SpanPatch(path="x", start=2, end=3, text="B")
    out = apply_span_patch(src, p)
    assert out == "a\nB\nc\n"


def test_replace_first_line():
    src = "one\nTwo\nthree\n"
    p = SpanPatch(path="x", start=1, end=2, text="ONE")
    out = apply_span_patch(src, p)
    assert out == "ONE\nTwo\nthree\n"


def test_replace_last_line():
    src = "one\nTwo\nthree\n"
    p = SpanPatch(path="x", start=3, end=4, text="THREE")
    out = apply_span_patch(src, p)
    assert out == "one\nTwo\nTHREE\n"


def test_replace_multiple_lines():
    src = "l1\nl2\nl3\nl4\n"
    p = SpanPatch(path="x", start=2, end=4, text="BLOCK")
    out = apply_span_patch(src, p)
    assert out == "l1\nBLOCK\nl4\n"


def test_clamps_start_below_one_and_end_beyond_length():
    # start < 1, end > len(lines) should clamp to full replacement
    src = "a\nb\nc\n"
    p = SpanPatch(path="x", start=0, end=999, text="ALL")
    out = apply_span_patch(src, p)
    assert out == "ALL\n"


def test_insertion_at_end_with_start_eq_end_len_plus_one():
    # start=end=len(lines)+1 inserts at end, preserving all prior content
    src = "a\nb\n"
    p = SpanPatch(path="x", start=3, end=3, text="c")
    out = apply_span_patch(src, p)
    assert out == "a\nb\nc\n"


def test_always_appends_single_newline_after_text():
    # Even if text already ends with a newline, the function appends another '\n'
    src = "a\nb\nc\n"
    p = SpanPatch(path="x", start=2, end=2, text="B\n")
    out = apply_span_patch(src, p)
    assert out == "a\nB\n\nb\nc\n"


def test_preserves_unaffected_line_endings():
    # Surrounding CRLFs are preserved; the injected text uses '\n'
    src = "a\r\nb\r\nc\r\n"
    p = SpanPatch(path="x", start=2, end=3, text="B")
    out = apply_span_patch(src, p)
    assert out == "a\r\nB\nc\r\n"


def test_empty_source_insert_first_line():
    src = ""
    p = SpanPatch(path="x", start=1, end=1, text="hello")
    out = apply_span_patch(src, p)
    assert out == "hello\n"
