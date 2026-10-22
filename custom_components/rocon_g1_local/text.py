"""Validated daily programs, inclusive holiday pair and optional circuit name."""
from homeassistant.components.text import TextEntity, TextMode
from .cloud import DAYS, path_get
from .cloud_entity import CloudEntity, holiday_text


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    entities = []
    for circuit in coordinator.data["circuits"]:
        entities.append(CloudText(coordinator, entry, circuit, "name", "Nome circuito", None))
        if circuit["type"] in ("direct", "heating") and holiday_text(circuit) is not None:
            entities.append(CloudText(coordinator, entry, circuit, "holiday", "Vacanze inizio e fine inclusiva", ("operationMode", "holiday")))
        for program in ("1", "2"):
            for day in DAYS:
                path = ("timeProgram", program, day)
                if isinstance(path_get(circuit, path), dict):
                    entities.append(CloudText(coordinator, entry, circuit, f"program_{program}_{day}", f"Programma {program} {day}", path))
    async_add_entities(entities)


class CloudText(CloudEntity, TextEntity):
    _attr_mode = TextMode.TEXT
    _attr_native_max = 64
    _attr_native_min = 1

    def __init__(self, coordinator, entry, circuit, key, name, path):
        super().__init__(coordinator, entry, circuit, key, name, path)
        self._attr_entity_registry_enabled_default = key != "name"
        # Existing installations may have an unnamed circuit. Permit that read
        # state; the command validator still rejects submitting an empty name.
        if key == "name":
            self._attr_native_min = 0

    @property
    def native_value(self):
        if self.key == "name":
            return self.circuit.get("name")
        if self.key == "holiday":
            return holiday_text(self.circuit)
        try:
            return ";".join(self.pair[str(slot)]["confirmed"]["start"] + "-" + self.pair[str(slot)]["confirmed"]["end"] for slot in (1,2,3))
        except (KeyError, TypeError):
            return None

    async def async_set_value(self, value):
        await self.async_write(self.key, value)
