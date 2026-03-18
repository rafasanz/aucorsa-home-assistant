from importlib import import_module
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession


_LOGGER = logging.getLogger(__name__)

DOMAIN = "aucorsa"
DATA_API = "api"
DATA_STATIC_REGISTERED = "static_registered"
STATIC_PANEL_FILENAME = "aucorsa-panel.js"
STATIC_PANEL_PATH = f"/api/{DOMAIN}/static/{STATIC_PANEL_FILENAME}"
PLATFORMS = ("sensor", "button")

if TYPE_CHECKING:
    from .api import AucorsaApi
    from .coordinator import AucorsaCoordinator


def _load_runtime_classes() -> tuple[type["AucorsaApi"], type["AucorsaCoordinator"]]:
    """Import runtime modules lazily so a broken integration does not block HA startup."""
    api_module = import_module(".api", __package__)
    coordinator_module = import_module(".coordinator", __package__)
    return api_module.AucorsaApi, coordinator_module.AucorsaCoordinator


def _cleanup_domain_data(hass: HomeAssistant, entry_id: str) -> None:
    domain_data: dict[str, Any] | None = hass.data.get(DOMAIN)
    if not domain_data:
        return

    domain_data.pop(entry_id, None)
    if not [key for key in domain_data if key != DATA_API]:
        domain_data.pop(DATA_API, None)
    if not domain_data:
        hass.data.pop(DOMAIN, None)


async def _async_ensure_static_assets(hass: HomeAssistant) -> None:
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(DATA_STATIC_REGISTERED):
        return

    static_file = Path(__file__).parent / "static" / STATIC_PANEL_FILENAME
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_PANEL_PATH, str(static_file), False)]
    )
    domain_data[DATA_STATIC_REGISTERED] = True


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    try:
        await _async_ensure_static_assets(hass)
    except Exception:
        _LOGGER.exception("No se pudieron registrar los recursos estáticos de AUCORSA")

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    domain_data = hass.data.setdefault(DOMAIN, {})

    try:
        await _async_ensure_static_assets(hass)
        AucorsaApi, AucorsaCoordinator = _load_runtime_classes()

        api = domain_data.get(DATA_API)
        if api is None:
            api = AucorsaApi(async_get_clientsession(hass))
            domain_data[DATA_API] = api

        coordinator = AucorsaCoordinator(hass, api, entry)
        await coordinator.async_config_entry_first_refresh()

        domain_data[entry.entry_id] = coordinator
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        _LOGGER.exception(
            "AUCORSA no se pudo cargar para la entrada %s. "
            "Home Assistant continuará arrancando sin esta integración.",
            entry.entry_id,
        )
        _cleanup_domain_data(hass, entry.entry_id)
        return False

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False

    _cleanup_domain_data(hass, entry.entry_id)

    return True
