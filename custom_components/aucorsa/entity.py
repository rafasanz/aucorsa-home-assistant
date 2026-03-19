from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ATTRIBUTION
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    API_CONFIGURATION_URL,
    ATTRIBUTION,
    CONF_SCAN_INTERVAL_SECONDS,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DOMAIN,
    INTEGRATION_VERSION,
    MANUFACTURER,
)
from .coordinator import AucorsaCoordinator


class AucorsaEntity(CoordinatorEntity[AucorsaCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, coordinator: AucorsaCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.config_entry = entry

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self.config_entry.entry_id)},
            manufacturer=MANUFACTURER,
            model="Servicio de llegada de autobuses",
            translation_key="managed_stop",
            translation_placeholders={
                "line": self.coordinator.data.line,
                "stop_id": self.coordinator.data.stop_id,
            },
            configuration_url=API_CONFIGURATION_URL,
        )

    @property
    def extra_state_attributes(self) -> dict[str, str | int | None]:
        data = self.coordinator.data
        return {
            ATTR_ATTRIBUTION: ATTRIBUTION,
            "aucorsa_managed": True,
            "line": data.line,
            "stop_id": data.stop_id,
            "stop_label": data.stop_label,
            "route": data.route,
            "line_color": data.line_color,
            "internal_line_id": data.internal_line_id,
            "integration_version": INTEGRATION_VERSION,
            "scan_interval_seconds": self.config_entry.options.get(
                CONF_SCAN_INTERVAL_SECONDS,
                DEFAULT_SCAN_INTERVAL_SECONDS,
            ),
        }
