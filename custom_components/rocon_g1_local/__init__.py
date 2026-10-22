"""Experimental local, read-only RoCon G1 integration. Not deployed by this project."""
from datetime import timedelta
import asyncio
import logging
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_KEY, CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .gateway import Gateway, GatewayAuthError, GatewayError
from .cloud import CloudClient, CloudAuthError, CloudError

DOMAIN = "rocon_g1_local"
PLATFORMS = [Platform.SENSOR]
CLOUD_PLATFORMS = [Platform.SENSOR, Platform.NUMBER, Platform.SELECT, Platform.SWITCH, Platform.TEXT]
LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Serve only the bundled public card, never gateway data or credentials."""
    await hass.http.async_register_static_paths([
        StaticPathConfig("/rocon_g1_local/rocon-climate-card.js",
                         str(Path(__file__).parent / "frontend" / "rocon-climate-card.js"), False)
    ])
    return True


class RoConCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        # 60 seconds is an initial polling parameter, not a safety/freshness threshold.
        super().__init__(hass, LOGGER, name=DOMAIN, config_entry=entry, update_interval=timedelta(seconds=60))
        self.gateway = Gateway(entry.data[CONF_HOST], entry.data[CONF_API_KEY])

    async def _async_update_data(self):
        try:
            return await self.hass.async_add_executor_job(self.gateway.snapshot)
        except GatewayAuthError:
            raise ConfigEntryAuthFailed("Local G1 authentication failed") from None
        except GatewayError:
            raise UpdateFailed("Local G1 read failed") from None


class CloudCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, entry):
        super().__init__(hass, LOGGER, name=DOMAIN, config_entry=entry,
                         update_interval=timedelta(seconds=300))
        self.client = CloudClient(entry.data["username"], entry.data["password"])
        self.installation_id = entry.data["installation_id"]
        self.controls_enabled = entry.data.get("enable_controls", False)
        self._command_lock = asyncio.Lock()

    async def _async_update_data(self):
        try:
            return await self.hass.async_add_executor_job(self.client.snapshot, self.installation_id)
        except CloudAuthError:
            raise ConfigEntryAuthFailed("Cloud authentication failed") from None
        except CloudError:
            raise UpdateFailed("Cloud read failed") from None

    async def async_command(self, circuit_id, command, value):
        if not self.controls_enabled or not self.last_update_success:
            raise HomeAssistantError("Cloud controls disabled or cloud data unavailable")
        async with self._command_lock:
            try:
                data = await self.hass.async_add_executor_job(
                    self.client.command, self.installation_id, circuit_id, command, value)
            except CloudError as error:
                # CloudError contains fixed safe messages only. Never propagate HTTP bodies.
                self.async_set_updated_data(self.data)
                raise HomeAssistantError(str(error)) from None
            self.async_set_updated_data(data)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    cloud = entry.data.get("connection_type") == "cloud"
    coordinator = CloudCoordinator(hass, entry) if cloud else RoConCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, CLOUD_PLATFORMS if cloud else PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, CLOUD_PLATFORMS if entry.data.get("connection_type") == "cloud" else PLATFORMS)
