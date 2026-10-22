"""Cached G1 readings. No climate/water_heater services or setters are registered."""
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTemperature
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .cloud import FIELDS, number, path_get
from .cloud_entity import CloudEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    if entry.data.get("connection_type") == "cloud":
        entities = []
        for circuit in coordinator.data["circuits"]:
            for key in FIELDS:
                entities.append(CloudReading(coordinator, entry, circuit, key, key))
            for key in ("boilerSetTemperature", "setLeadTemperature"):
                if isinstance(circuit.get(key), dict):
                    entities.append(CloudReading(coordinator, entry, circuit, key, key + " confirmed", (key,)))
            entities.append(CloudReading(coordinator, entry, circuit, "command_status", "Stato ultimo comando cloud"))
        async_add_entities(entities)
        return
    added = set()

    def discover():
        keys = set(coordinator.data or {}) - added
        async_add_entities([RoConSensor(coordinator, entry, key) for key in sorted(keys)])
        added.update(keys)

    discover()
    entry.async_on_unload(coordinator.async_add_listener(discover))


class RoConSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, key):
        super().__init__(coordinator)
        self.key = key
        row = coordinator.data[key]
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = f"{row['device']} {row['field']} cache"
        self._attr_entity_registry_enabled_default = row["enabled"]
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, entry.entry_id)}, name="RoCon G1", manufacturer="Daikin / ROTEX", model="RoCon G1")
        if row["temperature"]:
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def available(self):
        return super().available and self.key in (self.coordinator.data or {}) and self.coordinator.data[self.key]["value"] is not None

    @property
    def native_value(self):
        return self.coordinator.data.get(self.key, {}).get("value")

    @property
    def extra_state_attributes(self):
        row = self.coordinator.data.get(self.key, {})
        return {"source": "g1_local_cache", "measurement_timestamp_available": False,
                "suitable_for_automatic_setpoints": False,
                "rocon_gateway": self.coordinator.config_entry.entry_id,
                "rocon_device": row.get("device"), "rocon_field": row.get("field"),
                "rocon_section": row.get("section")}


class CloudReading(CloudEntity, SensorEntity):
    def __init__(self, coordinator, entry, circuit, key, name, path=None):
        super().__init__(coordinator, entry, circuit, key, name, path)
        if "Temperature" in key or key == "tvbhMix":
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_entity_registry_enabled_default = key not in ("errorCode", "heatGeneratorStatus", "boilerSetTemperature", "setLeadTemperature")

    @property
    def native_value(self):
        if self.key == "command_status":
            return self.coordinator.client.last_command
        value = (self.pair or {}).get("confirmed") if self.path else self.circuit.get(self.key)
        if not number(value):
            return None
        if self.key == "actualTemperature" and self.circuit.get("type") != "water" and value in (-60,-40,0):
            return None
        return value

    @property
    def available(self):
        return super().available and self.native_value is not None
