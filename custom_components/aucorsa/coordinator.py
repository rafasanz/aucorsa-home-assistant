import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AucorsaApi
from .const import (
    CONF_INTERNAL_LINE_ID,
    CONF_LINE,
    CONF_SCAN_INTERVAL_SECONDS,
    CONF_STOP_ID,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
)
from .models import EstimationResult


_LOGGER = logging.getLogger(__name__)


class AucorsaCoordinator(DataUpdateCoordinator[EstimationResult]):
    def __init__(self, hass: HomeAssistant, api: AucorsaApi, entry: ConfigEntry) -> None:
        self.api = api
        self.entry = entry
        self.line = entry.data[CONF_LINE]
        self.stop_id = entry.data[CONF_STOP_ID]
        self.internal_line_id = entry.data[CONF_INTERNAL_LINE_ID]
        scan_interval_seconds = entry.options.get(
            CONF_SCAN_INTERVAL_SECONDS,
            DEFAULT_SCAN_INTERVAL_SECONDS,
        )

        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=scan_interval_seconds),
            always_update=False,
        )

    async def _async_update_data(self) -> EstimationResult:
        try:
            return await self.api.estimate(
                visible_line=self.line,
                stop_id=self.stop_id,
                internal_line_id=self.internal_line_id,
            )
        except Exception as exc:
            raise UpdateFailed(f"No se pudieron actualizar los datos de AUCORSA: {exc}") from exc
