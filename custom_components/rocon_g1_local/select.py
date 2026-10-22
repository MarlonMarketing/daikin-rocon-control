"""Shared operation modes are exposed on heating circuits, never duplicated on ACS."""
from homeassistant.components.select import SelectEntity
from .cloud import MODES, path_get, supports_cooling
from .cloud_entity import CloudEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    entities = []
    for circuit in coordinator.data["circuits"]:
        if circuit["type"] in ("direct", "heating") and isinstance(path_get(circuit, ("operationMode", "type")), dict):
            entities.append(CloudMode(coordinator, entry, circuit))
    async_add_entities(entities)


class CloudMode(CloudEntity, SelectEntity):
    def __init__(self, coordinator, entry, circuit):
        super().__init__(coordinator, entry, circuit, "mode", "Modalità condivisa riscaldamento e ACS", ("operationMode", "type"))
        metadata = coordinator.data["installation"]
        self._attr_options = [key for key in MODES if key != "cooling" or supports_cooling(metadata)]

    @property
    def current_option(self):
        return next((key for key, value in MODES.items() if value == (self.pair or {}).get("confirmed")), None)

    async def async_select_option(self, option):
        await self.async_write("mode", option)
