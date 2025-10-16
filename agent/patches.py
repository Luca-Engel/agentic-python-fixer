from dataclasses import dataclass


@dataclass
class SpanPatch:
    path: str
    start: int  # 1-based line start inclusive
    end: int  # 1-based line end inclusive
    text: str


def apply_span_patch(src: str, patch: SpanPatch) -> str:
    lines = src.splitlines(keepends=True)
    start = max(patch.start - 1, 0)
    end = min(patch.end, len(lines))
    return "".join(lines[:start]) + patch.text + "".join(lines[end:])
