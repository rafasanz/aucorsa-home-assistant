import asyncio
import html
import logging
import re
import time
from typing import Any, Optional

from aiohttp import ClientError, ClientSession

from .const import REQUEST_GAP_SECONDS
from .models import EstimationResult, LineMatch, PageContext
from .parser import parse_estimations_response


_LOGGER = logging.getLogger(__name__)

PAGE_URL = "https://aucorsa.es/tiempos-de-paso/"
DEFAULT_API_URL = "https://aucorsa.es/wp-json/aucorsa/v1"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept-Language": "es-ES,es;q=0.9",
}

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


def line_match_from_api(item: dict[str, Any]) -> LineMatch:
    raw_label = str(item.get("label", "")).strip()
    line, route = split_line_label(raw_label)
    return LineMatch(
        id=str(item["id"]),
        line=line,
        label=normalize_line_label(raw_label),
        route=route,
    )


class AucorsaApi:
    def __init__(self, session: ClientSession, min_request_gap_seconds: float = REQUEST_GAP_SECONDS):
        self._session = session
        self._context: Optional[PageContext] = None
        self._request_lock = asyncio.Lock()
        self._last_request_monotonic = 0.0
        self._min_request_gap_seconds = min_request_gap_seconds

    async def _throttled_get(self, url: str, params: Optional[dict[str, Any]] = None) -> str:
        async with self._request_lock:
            now = time.monotonic()
            delay = self._min_request_gap_seconds - (now - self._last_request_monotonic)
            if delay > 0:
                _LOGGER.debug("Waiting %.2f seconds before requesting %s", delay, url)
                await asyncio.sleep(delay)

            async with self._session.get(url, params=params, headers=HEADERS, timeout=20) as response:
                text = await response.text()
                self._last_request_monotonic = time.monotonic()

                if response.status >= 400:
                    raise RuntimeError(f"HTTP {response.status} al consultar {url}: {text[:200]!r}")

                return text

    async def fetch_page(self) -> str:
        return await self._throttled_get(PAGE_URL)

    def extract_nonce(self, page_html: str) -> str:
        patterns = [
            r'ajax_nonce["\']?\s*:\s*["\']([^"\']+)["\']',
            r'"ajax_nonce"\s*:\s*"([^"]+)"',
            r'ajax_nonce=([a-zA-Z0-9_-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, page_html)
            if match:
                return html.unescape(match.group(1)).strip()
        raise RuntimeError("No se pudo extraer el _wpnonce de la página")

    def extract_post_id(self, page_html: str) -> str:
        patterns = [
            r'"post_id"\s*:\s*"([^"]+)"',
            r'post_id["\']?\s*:\s*["\']?([0-9]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, page_html)
            if match:
                return html.unescape(match.group(1)).strip()
        raise RuntimeError("No se pudo extraer el post_id de la página")

    def extract_api_url(self, page_html: str) -> str:
        patterns = [
            r'"api_url"\s*:\s*"([^"]+)"',
            r"api_url['\"]?\s*:\s*['\"]([^'\"]+)['\"]",
        ]
        for pattern in patterns:
            match = re.search(pattern, page_html)
            if match:
                api_url = html.unescape(match.group(1)).replace("\\/", "/").strip()
                if api_url:
                    return api_url.rstrip("/")
        return DEFAULT_API_URL

    async def refresh_context(self) -> PageContext:
        page_html = await self.fetch_page()
        self._context = PageContext(
            nonce=self.extract_nonce(page_html),
            post_id=self.extract_post_id(page_html),
            api_url=self.extract_api_url(page_html),
        )
        return self._context

    async def _get_context(self) -> PageContext:
        return self._context or await self.refresh_context()

    async def _api_get_text(
        self,
        path: str,
        params: dict[str, Any],
        retry_with_fresh_nonce: bool = True,
    ) -> str:
        context = await self._get_context()
        request_params = dict(params)
        request_params.setdefault("_wpnonce", context.nonce)

        text = await self._throttled_get(
            f"{(context.api_url or DEFAULT_API_URL).rstrip('/')}{path}",
            params=request_params,
        )
        if text.strip() != "-1":
            return text

        if not retry_with_fresh_nonce:
            raise RuntimeError("La API devolvió -1 incluso tras refrescar el nonce")

        _LOGGER.debug("Nonce caducado; refrescando contexto y reintentando")
        context = await self.refresh_context()
        request_params["_wpnonce"] = context.nonce
        return await self._api_get_text(path, request_params, retry_with_fresh_nonce=False)

    async def _api_get_json(self, path: str, params: dict[str, Any]) -> Any:
        import json

        text = await self._api_get_text(path, params)
        try:
            return json.loads(text)
        except ValueError as exc:
            raise RuntimeError(f"La API no devolvió JSON válido en {path}: {text[:200]!r}") from exc

    async def search_lines(self, term: str) -> list[LineMatch]:
        data = await self._api_get_json("/autocompletion/line", {"term": term})
        if not isinstance(data, list):
            raise RuntimeError("La API de autocompletado de líneas devolvió un formato inesperado")
        return [line_match_from_api(item) for item in data]

    async def resolve_line(self, visible_line: str) -> LineMatch:
        requested = str(visible_line).strip().upper()
        matches = await self.search_lines(visible_line)
        for match in matches:
            if match.line.upper() == requested:
                return match

        available = ", ".join(sorted({item.line for item in matches})) or "sin coincidencias"
        raise LookupError(
            f"No se encontró una coincidencia exacta para la línea {visible_line!r}. "
            f"Coincidencias devueltas por AUCORSA: {available}"
        )

    async def estimate(
        self,
        visible_line: str,
        stop_id: str,
        internal_line_id: Optional[str] = None,
    ) -> EstimationResult:
        if internal_line_id:
            line_match = LineMatch(
                id=str(internal_line_id),
                line=str(visible_line).strip(),
                label=str(visible_line).strip(),
                route=None,
            )
        else:
            line_match = await self.resolve_line(visible_line)

        response_text = await self._api_get_text(
            "/estimations/stop",
            {
                "line": line_match.id,
                "current_line": line_match.id,
                "stop_id": str(stop_id).strip(),
            },
        )

        parsed = parse_estimations_response(
            response_text=response_text,
            stop_id=str(stop_id).strip(),
            line_id_by_visible={line_match.line: line_match.id},
        )

        requested_line = str(visible_line).strip().upper()
        selected_line = None
        for line in parsed.lines:
            if line.line.upper() == requested_line:
                selected_line = line
                break

        if selected_line is None:
            return EstimationResult(
                stop_id=str(stop_id).strip(),
                line=str(visible_line).strip(),
                internal_line_id=line_match.id,
                stop_label=parsed.stop_label,
                route=None,
                line_color=None,
                next_bus_min=None,
                following_bus_min=None,
            )

        return EstimationResult(
            stop_id=str(stop_id).strip(),
            line=selected_line.line,
            internal_line_id=line_match.id,
            stop_label=parsed.stop_label,
            route=selected_line.route,
            line_color=selected_line.line_color,
            next_bus_min=selected_line.next_bus_min,
            following_bus_min=selected_line.following_bus_min,
        )
