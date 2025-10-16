from agent.patches import apply_span_patch, SpanPatch


def test_apply_span_patch_basic():
    src = "a\nb\nc\n"
    sp = SpanPatch(path="x", start=2, end=2, text="B\n")
    out = apply_span_patch(src, sp)
    assert out == "a\nB\nc\n"
