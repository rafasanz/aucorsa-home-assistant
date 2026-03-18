from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import AucorsaCoordinator
from .entity import AucorsaEntity


PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: AucorsaCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AucorsaStopNameSensor(coordinator, entry),
            AucorsaArrivalSensor(coordinator, entry, "next", "next_arrival", "mdi:bus-clock"),
            AucorsaArrivalSensor(
                coordinator,
                entry,
                "following",
                "following_arrival",
                "mdi:bus",
            ),
        ]
    )


class AucorsaArrivalSensor(AucorsaEntity, SensorEntity):
    def __init__(
        self,
        coordinator: AucorsaCoordinator,
        entry: ConfigEntry,
        key: str,
        translation_key: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, entry)
        self._key = key
        self._attr_translation_key = translation_key
        self._attr_icon = icon
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_suggested_display_precision = 0

    @property
    def native_value(self) -> int | None:
        if self._key == "next":
            return self.coordinator.data.next_bus_min
        return self.coordinator.data.following_bus_min

    @property
    def extra_state_attributes(self) -> dict[str, str | int | bool | None]:
        attributes = dict(super().extra_state_attributes)
        attributes["aucorsa_sensor_type"] = self._key
        return attributes


class AucorsaStopNameSensor(AucorsaEntity, SensorEntity):
    def __init__(self, coordinator: AucorsaCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_translation_key = "stop_name"
        self._attr_icon = "mdi:map-marker"
        self._attr_unique_id = f"{entry.entry_id}_stop_name"

    @property
    def native_value(self) -> str:
        return self.coordinator.data.stop_label or f"Stop {self.coordinator.data.stop_id}"

    @property
    def extra_state_attributes(self) -> dict[str, str | int | bool | None]:
        attributes = dict(super().extra_state_attributes)
        attributes["aucorsa_sensor_type"] = "stop_name"
        return attributes
