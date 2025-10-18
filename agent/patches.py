from dataclasses import dataclass


@dataclass
class SpanPatch:
    """
    A patch that replaces a span of lines in a file with new text.
    Line numbers are 1-based.
    """
    path: str
    start: int  # 1-based
    end: int  # 1-based
    text: str


def apply_span_patch(src: str, patch: SpanPatch) -> str:
    """
    Apply a SpanPatch to the given source code string.
    Line numbers in SpanPatch are 1-based.
    """
    lines = src.splitlines(keepends=True)
    start = max(patch.start - 1, 0)
    end = min(patch.end - 1, len(lines))
    return "".join(lines[:start]) + patch.text + "\n" + "".join(lines[end:])
