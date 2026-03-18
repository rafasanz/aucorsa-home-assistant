import re
import sys
import unicodedata
from typing import Any, Optional

import requests

from .lines import line_match_from_api, select_exact_line
from .models import EstimationResult, LineMatch, PageContext, StopEstimationsResult, StopMatch
from .parser import parse_estimations_response


PAGE_URL = "https://aucorsa.es/tiempos-de-paso/"
API_URL = "https://aucorsa.es/wp-json/aucorsa/v1"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "es-ES,es;q=0.9",
}


def _normalize_search_text(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text.casefold())
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


class AucorsaClient:
    def __init__(self, debug: bool = False):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.debug = debug
        self._context: Optional[PageContext] = None

    def _log(self, msg: str):
        if self.debug:
            print(f"[DEBUG] {msg}", file=sys.stderr)

    def fetch_page(self) -> str:
        self._log(f"GET {PAGE_URL}")
        response = self.session.get(PAGE_URL, timeout=20)
        response.raise_for_status()
        return response.text

    def extract_nonce(self, page_html: str) -> str:
        patterns = [
            r'ajax_nonce["\']?\s*:\s*["\']([a-zA-Z0-9]+)["\']',
            r'"ajax_nonce"\s*:\s*"([a-zA-Z0-9]+)"',
            r'ajax_nonce=([a-zA-Z0-9]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, page_html)
            if match:
                nonce = match.group(1)
                self._log(f"Nonce encontrado: {nonce}")
                return nonce
        raise RuntimeError("No se pudo extraer el _wpnonce de la página")

    def extract_post_id(self, page_html: str) -> str:
        patterns = [
            r'"post_id"\s*:\s*"(\d+)"',
            r'post_id["\']?\s*:\s*["\']?(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, page_html)
            if match:
                post_id = match.group(1)
                self._log(f"post_id encontrado: {post_id}")
                return post_id
        raise RuntimeError("No se pudo extraer el post_id de la página")

    def refresh_context(self) -> PageContext:
        page_html = self.fetch_page()
        self._context = PageContext(
            nonce=self.extract_nonce(page_html),
            post_id=self.extract_post_id(page_html),
        )
        return self._context

    def _get_context(self) -> PageContext:
        return self._context or self.refresh_context()

    def _api_get(self, path: str, params: dict[str, Any], retry_with_fresh_nonce: bool = True) -> requests.Response:
        context = self._get_context()
        request_params = dict(params)
        request_params.setdefault("_wpnonce", context.nonce)

        url = f"{API_URL}{path}"
        self._log(f"GET {url} params={request_params}")
        response = self.session.get(url, params=request_params, timeout=20)
        response.raise_for_status()

        if response.text.strip() == "-1":
            if not retry_with_fresh_nonce:
                raise RuntimeError("La API devolvió -1 incluso tras refrescar el nonce")

            self._log("Respuesta -1 recibida; refrescando nonce y reintentando")
            context = self.refresh_context()
            request_params["_wpnonce"] = context.nonce
            return self._api_get(path, request_params, retry_with_fresh_nonce=False)

        self._log(f"Status API: {response.status_code}")
        return response

    def _api_get_json(self, path: str, params: dict[str, Any]) -> Any:
        response = self._api_get(path, params)
        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError(f"La API no devolvió JSON válido en {path}: {response.text[:200]!r}") from exc

    def search_lines(self, term: str) -> list[LineMatch]:
        data = self._api_get_json("/autocompletion/line", {"term": term})
        if not isinstance(data, list):
            raise RuntimeError("La API de autocompletado de líneas devolvió un formato inesperado")
        return [line_match_from_api(item) for item in data]

    def resolve_line(self, visible_line: str) -> LineMatch:
        matches = self.search_lines(visible_line)
        match = select_exact_line(matches, visible_line)
        if match:
            return match

        available = ", ".join(sorted({item.line for item in matches})) or "sin coincidencias"
        raise LookupError(
            f"No se encontró una coincidencia exacta para la línea {visible_line!r}. "
            f"Coincidencias devueltas por AUCORSA: {available}"
        )

    def search_stops(self, term: str, line: Optional[str] = None) -> list[StopMatch]:
        context = self._get_context()
        params: dict[str, Any] = {"post_id": context.post_id}

        if line:
            line_match = self.resolve_line(line)
            params["post_id"] = line_match.id
            params["line_number"] = line_match.line

        data = self._api_get_json("/autocompletion/stop", params)
        if not isinstance(data, list):
            raise RuntimeError("La API de autocompletado de paradas devolvió un formato inesperado")

        stops = [
            StopMatch(
                id=str(item["id"]),
                label=str(item.get("label", "")).strip(),
                link=str(item["link"]) if item.get("link") else None,
            )
            for item in data
        ]

        if not term:
            return stops

        normalized_term = _normalize_search_text(term)
        return [stop for stop in stops if normalized_term in _normalize_search_text(stop.label)]

    def fetch_estimations_raw(self, stop_id: str, internal_line_id: Optional[str] = None) -> str:
        params: dict[str, Any] = {"stop_id": stop_id}
        if internal_line_id:
            params["line"] = internal_line_id
            params["current_line"] = internal_line_id

        response = self._api_get("/estimations/stop", params)
        return response.text

    def estimate_stop(self, stop_id: str) -> StopEstimationsResult:
        raw_response = self.fetch_estimations_raw(stop_id=stop_id)
        self._log("HTML devuelto por la API:")
        self._log(raw_response)
        return parse_estimations_response(raw_response, stop_id=stop_id)

    def estimate(
        self,
        visible_line: str,
        stop_id: str,
        internal_line_id: Optional[str] = None,
    ) -> EstimationResult:
        line_match = None
        if internal_line_id:
            line_match = LineMatch(
                id=str(internal_line_id),
                line=str(visible_line),
                label=str(visible_line),
                route=None,
            )
        else:
            line_match = self.resolve_line(visible_line)

        raw_response = self.fetch_estimations_raw(stop_id=stop_id, internal_line_id=line_match.id)
        self._log("HTML devuelto por la API:")
        self._log(raw_response)

        parsed = parse_estimations_response(
            raw_response,
            stop_id=stop_id,
            line_id_by_visible={line_match.line: line_match.id},
        )

        selected_line = None
        requested_line = str(visible_line).strip().upper()
        for line in parsed.lines:
            if line.line.upper() == requested_line:
                selected_line = line
                break

        if selected_line is None:
            return EstimationResult(
                stop_id=str(stop_id),
                line=str(visible_line),
                internal_line_id=line_match.id,
                stop_label=parsed.stop_label,
                route=None,
                line_color=None,
                next_bus_min=None,
                following_bus_min=None,
            )

        return EstimationResult(
            stop_id=str(stop_id),
            line=selected_line.line,
            internal_line_id=line_match.id,
            stop_label=parsed.stop_label,
            route=selected_line.route,
            line_color=selected_line.line_color,
            next_bus_min=selected_line.next_bus_min,
            following_bus_min=selected_line.following_bus_min,
        )
