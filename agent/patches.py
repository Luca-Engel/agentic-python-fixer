from dataclasses import dataclass


@dataclass
class SpanPatch:
    path: str
    start: int  # 0-based
    end: int  # 0-based
    text: str


def apply_span_patch(src: str, patch: SpanPatch) -> str:
    lines = src.splitlines(keepends=True)
    start = max(patch.start, 0)
    end = min(patch.end, len(lines))
    return "".join(lines[:start]) + patch.text + "\n" + "".join(lines[end:])
