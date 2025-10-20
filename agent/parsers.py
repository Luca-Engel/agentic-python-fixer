import json
import re
from typing import Tuple, Dict, Any

_THOUGHT_PATTERNS = [
    r"Thought\[(?P<body>.+?)\]",  # Thought[...]
    r"Thought:\s*(?P<body>.+?)$",  # Thought: ...
    r"Thought\s+(?P<body>\{.*?\}|\[.*?\]|\".*?\"|'.*?'|.+?)$",  # fallback
]

_PATCH_PATTERNS = [
    r"Patch\[(?P<json>\{.*?\})\]",  # Patch[{...}]
    r"Patch:\s*(?P<json>\{.*?\})",  # Patch: {...}
    r"Patch\s*(?P<json>\{.*?\})",  # Patch {...}
]


def _last_match(text: str, patterns) -> Tuple[str, re.Match[str] | None]:
    last = None
    pat_used = ""
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.S | re.M):
            last = m
            pat_used = pat
    return pat_used, last


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    return s


# ---------- Thought ----------

def match_thought(block: str) -> Tuple[str, str, str]:
    """
    Returns: (inner_text, matched_substring, "Thought")
    Finds the LAST 'Thought[...]' or 'Thought: ...' occurrence in the block.
    """
    _, m = _last_match(block, _THOUGHT_PATTERNS)
    if not m:
        raise ValueError("No Thought block found.")
    inner = m.group("body").strip()
    inner = _strip_quotes(inner)
    return inner, m.group(0), "Thought"


def parse_thought(block: str) -> Tuple[str, Dict[str, Any], str]:
    """
    Strict Thought parser. Accepts:
      - Thought["..."] / Thought['...'] / Thought[...]
      - Thought: ...
    Returns: ("Thought", {"text": <string>}, matched_substring)
    """
    inner, matched, name = match_thought(block)
    if not inner:
        raise ValueError("Empty Thought content.")
    return name, {"text": inner}, matched


# ---------- Patch ----------

def match_patch(block: str) -> Tuple[str, str, str]:
    """
    Returns: (json_text, matched_substring, "Patch")
    Finds the LAST Patch occurrence in the block.
    """
    _, m = _last_match(block, _PATCH_PATTERNS)
    if not m:
        raise ValueError("No Patch block found.")
    json_text = m.group("json").strip()
    return json_text, m.group(0), "Patch"


def _coerce_int(name: str, v: Any) -> int:
    if isinstance(v, int):
        return v
    if isinstance(v, str) and v.isdigit():
        return int(v)
    raise ValueError(f"{name} must be an integer.")


def parse_patch(block: str) -> Tuple[str, Dict[str, Any], str]:
    """
    Strict Patch parser. Accepts:
      - Patch[{...}]
      - Patch: {...}
      - Patch {...}
    Requires keys: start (int), end (int), text (str)
    Optional: nb_indents (int)
    """
    json_text, matched, name = match_patch(block)

    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError:
        raise ValueError("Patch JSON is invalid.")

    if not isinstance(payload, dict):
        raise ValueError("Patch payload must be a JSON object.")

    if "start" not in payload or "end" not in payload or "text" not in payload:
        raise ValueError("Patch must include 'start', 'end', and 'text'.")

    start = _coerce_int("start", payload["start"])
    end = _coerce_int("end", payload["end"])
    text = payload["text"]
    if not isinstance(text, str):
        raise ValueError("'text' must be a string.")

    nb_indents = payload.get("nb_indents", 0)
    if not isinstance(nb_indents, int):
        # allow coercion from numeric-looking strings
        if isinstance(nb_indents, str) and nb_indents.isdigit():
            nb_indents = int(nb_indents)
        else:
            raise ValueError("'nb_indents' must be an integer if present.")

    args = {"start": start, "end": end, "text": text, "nb_indents": nb_indents}
    return name, args, matched
