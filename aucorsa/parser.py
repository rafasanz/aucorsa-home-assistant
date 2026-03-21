import json
import re
from html.parser import HTMLParser
from typing import Any, Mapping, Optional

from .models import LineEstimation, StopEstimationsResult


MINUTES_RE = re.compile(r"(\d+)\s*minuto(?:s)?", re.IGNORECASE)
CSS_DECLARATION_RE = re.compile(r"([a-zA-Z-]+)\s*:\s*([^;]+)")
COLOR_VALUE_RE = re.compile(r"(#[0-9a-fA-F]{3,8}|rgb[a]?\([^)]+\))")

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover - se cubre con el fallback estándar
    BeautifulSoup = None


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


class _EstimationsHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stop_label: Optional[str] = None
        self.containers: list[dict] = []
        self._current_container: Optional[dict] = None
        self._current_container_depth = 0
        self._captures: list[dict] = []

    def handle_starttag(self, tag, attrs):
        if self._current_container is not None:
            self._current_container_depth += 1

        for capture in self._captures:
            capture["depth"] += 1

        attr_map = dict(attrs)
        classes = set(attr_map.get("class", "").split())

        if "ppp-container" in classes:
            self._current_container = {"line": None, "route": None, "color": None, "estimations": []}
            self._current_container_depth = 1
            return

        if "ppp-stop-label" in classes:
            self._captures.append({"kind": "stop_label", "depth": 1, "buffer": []})
        elif self._current_container is not None and "ppp-line-number" in classes:
            self._current_container["color"] = self._current_container["color"] or _extract_color_from_style(
                attr_map.get("style")
            )
            self._captures.append({"kind": "line", "depth": 1, "buffer": []})
        elif self._current_container is not None and "ppp-estimations" in classes:
            self._current_container["color"] = self._current_container["color"] or _extract_color_from_style(
                attr_map.get("style")
            )
        elif self._current_container is not None and "ppp-line-route" in classes:
            self._captures.append({"kind": "route", "depth": 1, "buffer": []})
        elif self._current_container is not None and "ppp-estimation" in classes:
            self._captures.append({"kind": "estimation", "depth": 1, "buffer": []})

    def handle_endtag(self, tag):
        remaining_captures = []
        for capture in self._captures:
            capture["depth"] -= 1
            if capture["depth"] == 0:
                self._finalize_capture(capture)
            else:
                remaining_captures.append(capture)
        self._captures = remaining_captures

        if self._current_container is not None:
            self._current_container_depth -= 1
            if self._current_container_depth == 0:
                self.containers.append(self._current_container)
                self._current_container = None

    def handle_data(self, data):
        for capture in self._captures:
            capture["buffer"].append(data)

    def _finalize_capture(self, capture: dict):
        text = _clean_text("".join(capture["buffer"]))
        if not text:
            return

        kind = capture["kind"]
        if kind == "stop_label":
            self.stop_label = text
            return

        if self._current_container is None:
            return

        if kind == "line":
            self._current_container["line"] = text
        elif kind == "route":
            self._current_container["route"] = text
        elif kind == "estimation":
            self._current_container["estimations"].append(text)


def _extract_color_from_style(style: Optional[str]) -> Optional[str]:
    if not style:
        return None

    for property_name, raw_value in CSS_DECLARATION_RE.findall(style):
        prop = property_name.strip().lower()
        value = raw_value.strip()
        if prop == "background-color":
            return value
        if prop == "border-left":
            match = COLOR_VALUE_RE.search(value)
            if match:
                return match.group(1).strip()

    return None


def _looks_like_html(value: str) -> bool:
    text = str(value or "").lstrip()
    return text.startswith("<") and ">" in text


def _extract_html_from_payload(payload: Any) -> Optional[str]:
    if isinstance(payload, str):
        stripped = payload.strip()
        if _looks_like_html(stripped):
            return stripped
        return None

    if isinstance(payload, dict):
        preferred_keys = ("html", "content", "markup", "data", "response", "result")
        for key in preferred_keys:
            if key in payload:
                extracted = _extract_html_from_payload(payload[key])
                if extracted is not None:
                    return extracted

        for value in payload.values():
            extracted = _extract_html_from_payload(value)
            if extracted is not None:
                return extracted

    if isinstance(payload, list):
        for item in payload:
            extracted = _extract_html_from_payload(item)
            if extracted is not None:
                return extracted

    return None


def parse_escaped_html_response(response_text: str) -> str:
    stripped_response = str(response_text or "").strip()
    if not stripped_response:
        raise RuntimeError("La API devolvió una respuesta vacía")

    if _looks_like_html(stripped_response):
        return stripped_response

    try:
        payload = json.loads(stripped_response)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"La respuesta no era JSON ni HTML válido: {exc}") from exc

    html_string = _extract_html_from_payload(payload)
    if html_string is None:
        raise RuntimeError("La API no devolvió HTML reconocible dentro de la respuesta")

    return html_string


def parse_estimations_html(
    html_string: str,
    stop_id: str,
    line_id_by_visible: Optional[Mapping[str, str]] = None,
) -> StopEstimationsResult:
    normalized_line_map = {
        str(visible_line).upper(): str(internal_line_id)
        for visible_line, internal_line_id in (line_id_by_visible or {}).items()
    }

    if BeautifulSoup is not None:
        soup = BeautifulSoup(html_string, "html.parser")
        stop_label = None

        stop_el = soup.select_one(".ppp-stop-label")
        if stop_el:
            stop_label = stop_el.get_text(" ", strip=True)

        container_payloads = []
        for container in soup.select(".ppp-container"):
            line_el = container.select_one(".ppp-line-number")
            if not line_el:
                continue

            route = None
            route_el = container.select_one(".ppp-line-route")
            if route_el:
                route = route_el.get_text(" ", strip=True)

            container_payloads.append(
                {
                    "line": line_el.get_text(" ", strip=True),
                    "route": route,
                    "color": _extract_color_from_style(line_el.get("style"))
                    or _extract_color_from_style(
                        (container.select_one(".ppp-estimations") or {}).get("style")
                        if container.select_one(".ppp-estimations")
                        else None
                    ),
                    "estimations": [
                        estimation_el.get_text(" ", strip=True)
                        for estimation_el in container.select(".ppp-estimation")
                    ],
                }
            )
    else:
        fallback_parser = _EstimationsHTMLParser()
        fallback_parser.feed(html_string)
        stop_label = fallback_parser.stop_label
        container_payloads = fallback_parser.containers

    lines: list[LineEstimation] = []
    for container in container_payloads:
        visible_line = container.get("line")
        if not visible_line:
            continue

        minutes: list[int] = []
        for text in container.get("estimations", []):
            match = MINUTES_RE.search(text)
            if match:
                minutes.append(int(match.group(1)))

        lines.append(
            LineEstimation(
                line=visible_line,
                internal_line_id=normalized_line_map.get(visible_line.upper()),
                route=container.get("route"),
                line_color=container.get("color"),
                next_bus_min=minutes[0] if len(minutes) >= 1 else None,
                following_bus_min=minutes[1] if len(minutes) >= 2 else None,
            )
        )

    return StopEstimationsResult(
        stop_id=str(stop_id),
        stop_label=stop_label,
        lines=lines,
    )


def parse_estimations_response(
    response_text: str,
    stop_id: str,
    line_id_by_visible: Optional[Mapping[str, str]] = None,
) -> StopEstimationsResult:
    html_string = parse_escaped_html_response(response_text)
    return parse_estimations_html(
        html_string=html_string,
        stop_id=stop_id,
        line_id_by_visible=line_id_by_visible,
    )
