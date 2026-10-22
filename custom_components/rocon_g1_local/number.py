"""App profile temperatures and Party duration. No inferred active setpoint."""
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import UnitOfTemperature, UnitOfTime
from .cloud_entity import CloudEntity
from .cloud import number, path_get


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    entities = []
    for circuit in coordinator.data["circuits"]:
        for index in ("1", "2", "3"):
            path = ("setTemperature", index)
            if isinstance(path_get(circuit, path), dict):
                entities.append(CloudNumber(coordinator, entry, circuit, f"profile_{index}", f"Temperatura profilo {index}", path,
                                            10 if circuit["type"] == "water" else 5, 70 if circuit["type"] == "water" else 40, .5))
        if circuit["type"] in ("direct", "heating"):
            for key, label in (("setbackTemperatureHeating", "Temperatura ridotta"), ("setbackTemperatureAbsence", "Temperatura assenza")):
                if isinstance(circuit.get(key), dict):
                    entities.append(CloudNumber(coordinator, entry, circuit, key, label, (key,), 5, 40, .5))
            path = ("operationMode", "party", "hours")
            if isinstance(path_get(circuit, path), dict):
                entities.append(CloudNumber(coordinator, entry, circuit, "party", "Party durata in minuti", path, 0, 360, 15, minutes=True))
    async_add_entities(entities)


class CloudNumber(CloudEntity, NumberEntity):
    def __init__(self, coordinator, entry, circuit, key, label, path, minimum, maximum, step, minutes=False):
        super().__init__(coordinator, entry, circuit, key, label, path)
        self._attr_native_min_value, self._attr_native_max_value = minimum, maximum
        self._attr_native_step = step
        self._attr_mode = NumberMode.BOX
        self._attr_native_unit_of_measurement = UnitOfTime.MINUTES if minutes else UnitOfTemperature.CELSIUS

    @property
    def native_value(self):
        value = (self.pair or {}).get("confirmed")
        return value if number(value) else None

    @property
    def available(self):
        return super().available and self.native_value is not None

    async def async_set_native_value(self, value):
        await self.async_write(self.key, value)
