"""One-time ACS heatup; state is server-confirmed, never optimistic."""
from homeassistant.components.switch import SwitchEntity
from .cloud_entity import CloudEntity


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    async_add_entities([CloudBoost(coordinator, entry, circuit, "boost", "Riscaldamento ACS una tantum", ("onetimeHeatupActive",))
                        for circuit in coordinator.data["circuits"] if circuit["type"] == "water" and isinstance(circuit.get("onetimeHeatupActive"), dict)])


class CloudBoost(CloudEntity, SwitchEntity):
    @property
    def is_on(self):
        value = (self.pair or {}).get("confirmed")
        return True if value is True or value == "true" else False if value is False or value == "false" else None

    async def async_turn_on(self, **kwargs):
        await self.async_write("boost", True)

    async def async_turn_off(self, **kwargs):
        await self.async_write("boost", False)
