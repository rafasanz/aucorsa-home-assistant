import re
from typing import Iterable, Optional

from .models import LineMatch


LINE_LABEL_SEPARATOR = "\u3164"


def normalize_line_label(label: str) -> str:
    return re.sub(r"\s+", " ", label.replace(LINE_LABEL_SEPARATOR, " ")).strip()


def split_line_label(label: str) -> tuple[str, Optional[str]]:
    normalized = normalize_line_label(label)
    if not normalized:
        return "", None

    parts = normalized.split(" ", 1)
    line = parts[0].strip()
    route = parts[1].strip() if len(parts) > 1 else None
    return line, route


def line_match_from_api(item: dict) -> LineMatch:
    raw_label = str(item.get("label", "")).strip()
    line, route = split_line_label(raw_label)
    return LineMatch(
        id=str(item["id"]),
        line=line,
        label=normalize_line_label(raw_label),
        route=route,
    )


def select_exact_line(matches: Iterable[LineMatch], requested_line: str) -> Optional[LineMatch]:
    requested = str(requested_line).strip().upper()
    for match in matches:
        if match.line.upper() == requested:
            return match
    return None
