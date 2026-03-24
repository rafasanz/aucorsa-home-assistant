import sys
import types
import unittest
from unittest.mock import AsyncMock


def _install_homeassistant_stubs() -> None:
    if "homeassistant" in sys.modules:
        return

    homeassistant = types.ModuleType("homeassistant")
    components = types.ModuleType("homeassistant.components")
    http = types.ModuleType("homeassistant.components.http")
    const = types.ModuleType("homeassistant.const")
    config_entries = types.ModuleType("homeassistant.config_entries")
    core = types.ModuleType("homeassistant.core")
    exceptions = types.ModuleType("homeassistant.exceptions")
    helpers = types.ModuleType("homeassistant.helpers")
    aiohttp_client = types.ModuleType("homeassistant.helpers.aiohttp_client")

    homeassistant.__path__ = []
    components.__path__ = []
    helpers.__path__ = []

    class StaticPathConfig:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class ConfigEntry:
        pass

    class HomeAssistant:
        pass

    class ConfigEntryNotReady(Exception):
        pass

    class Platform:
        SENSOR = "sensor"
        BUTTON = "button"

    def async_get_clientsession(hass):
        return None

    http.StaticPathConfig = StaticPathConfig
    const.Platform = Platform
    config_entries.ConfigEntry = ConfigEntry
    core.HomeAssistant = HomeAssistant
    exceptions.ConfigEntryNotReady = ConfigEntryNotReady
    aiohttp_client.async_get_clientsession = async_get_clientsession

    sys.modules["homeassistant"] = homeassistant
    sys.modules["homeassistant.components"] = components
    sys.modules["homeassistant.components.http"] = http
    sys.modules["homeassistant.const"] = const
    sys.modules["homeassistant.config_entries"] = config_entries
    sys.modules["homeassistant.core"] = core
    sys.modules["homeassistant.exceptions"] = exceptions
    sys.modules["homeassistant.helpers"] = helpers
    sys.modules["homeassistant.helpers.aiohttp_client"] = aiohttp_client


_install_homeassistant_stubs()

from custom_components.aucorsa.api import AucorsaApi
from custom_components.aucorsa.models import PageContext


class FakeCookieJar:
    def __init__(self) -> None:
        self.cleared_domains: list[str] = []

    def clear_domain(self, domain: str) -> None:
        self.cleared_domains.append(domain)


class FakeResponse:
    def __init__(self, status: int, text: str) -> None:
        self.status = status
        self._text = text

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def text(self) -> str:
        return self._text


class FakeSession:
    def __init__(self, responses: list[FakeResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []
        self.cookie_jar = FakeCookieJar()

    def get(self, url, params=None, headers=None, timeout=None):
        self.calls.append(
            {
                "url": url,
                "params": dict(params) if params else None,
                "headers": headers,
                "timeout": timeout,
            }
        )
        return self.responses.pop(0)


class AsyncApiNonceRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_api_get_text_refreshes_context_after_generic_403(self):
        session = FakeSession(
            [
                FakeResponse(403, '{"message":"Forbidden"}'),
                FakeResponse(200, "[]"),
            ]
        )
        api = AucorsaApi(session, min_request_gap_seconds=0)
        api._context = PageContext(
            nonce="stale-nonce",
            post_id="6935",
            api_url="https://aucorsa.es/wp-json/aucorsa/v1",
        )

        fresh_context = PageContext(
            nonce="fresh-nonce",
            post_id="6935",
            api_url="https://aucorsa.es/wp-json/aucorsa/v1",
        )

        async def _refresh_context():
            api._context = fresh_context
            return fresh_context

        api.refresh_context = AsyncMock(side_effect=_refresh_context)

        response_text = await api._api_get_text("/autocompletion/line", {"term": "12"})

        self.assertEqual(response_text, "[]")
        self.assertEqual(api.refresh_context.await_count, 1)
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(session.calls[0]["params"]["_wpnonce"], "stale-nonce")
        self.assertEqual(session.calls[1]["params"]["_wpnonce"], "fresh-nonce")
        self.assertIn("aucorsa.es", session.cookie_jar.cleared_domains)
        self.assertIn(".aucorsa.es", session.cookie_jar.cleared_domains)


if __name__ == "__main__":
    unittest.main()
