from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AucorsaCoordinator
from .entity import AucorsaEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AucorsaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AucorsaRefreshButton(coordinator, entry)])


class AucorsaRefreshButton(AucorsaEntity, ButtonEntity):
    def __init__(self, coordinator: AucorsaCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_translation_key = "refresh_data"
        self._attr_icon = "mdi:refresh"
        self._attr_unique_id = f"{entry.entry_id}_refresh"

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, str | int | bool | None]:
        attributes = dict(super().extra_state_attributes)
        attributes["aucorsa_button_type"] = "refresh"
        return attributes
