"""Shared cloud entity metadata. No optimistic states or private account dump."""
from datetime import date, timedelta

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DOMAIN
from .cloud import effective, path_get


class CloudEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, circuit, key, name, path=None):
        super().__init__(coordinator)
        self.circuit_id = str(circuit["id"])
        self.key, self.path = key, path
        self.entry_id = entry.entry_id
        self._attr_unique_id = f"{entry.entry_id}_{self.circuit_id}_{key}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_{self.circuit_id}")},
            name=f"RoCon {circuit['type']} {circuit.get('index', '')}",
            manufacturer="Daikin / ROTEX", model="RoCon G1 via Daikin Control cloud")

    @property
    def circuit(self):
        return next((item for item in self.coordinator.data.get("circuits", [])
                     if str(item.get("id")) == self.circuit_id), {})

    @property
    def available(self):
        return super().available and bool(self.circuit)

    @property
    def pair(self):
        return path_get(self.circuit, self.path) if self.path else None

    @property
    def extra_state_attributes(self):
        attributes = {"source": "rocon_cloud", "rocon_gateway": self.entry_id,
            "rocon_circuit": self.circuit_id, "rocon_index": self.circuit.get("index"),
            "rocon_device": self.circuit.get("type"), "rocon_field": self.key,
            "rocon_section": "setting" if self.path else "status",
            "measurement_timestamp_available": False,
            "last_command_status": self.coordinator.client.last_command,
            "controls_enabled": self.coordinator.controls_enabled}
        if isinstance(self.pair, dict):
            attributes.update(requested=self.pair.get("set"), confirmed=self.pair.get("confirmed"),
                              requested_at=self.pair.get("setDate"), confirmed_at=self.pair.get("confirmedDate"))
        return attributes

    async def async_write(self, command, value):
        await self.coordinator.async_command(self.circuit_id, command, value)


def holiday_text(circuit, *, confirmed=True):
    try:
        days = []
        for name in ("beginning", "ending"):
            obj = circuit["operationMode"]["holiday"][name]
            values = [obj[k].get("confirmed") if confirmed else effective(obj[k]) for k in ("year", "month", "day")]
            days.append(date(2000 + int(values[0]), int(values[1]), int(values[2])))
        return days[0].isoformat() + "/" + (days[1] - timedelta(days=1)).isoformat()
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
