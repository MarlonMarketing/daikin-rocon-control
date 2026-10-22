"""Local API key setup. No cloud credentials, local user creation or gateway changes."""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY, CONF_HOST
from homeassistant.helpers import selector

from . import DOMAIN
from .gateway import Gateway, GatewayAuthError, GatewayError
from .cloud import CloudClient, CloudAuthError, CloudError


class RoConFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        # Existing LAN test/config payloads remain supported.
        if user_input and CONF_HOST in user_input:
            return await self._form("local", user_input)
        if user_input:
            if user_input["connection_type"] == "cloud":
                return await self.async_step_cloud()
            return await self.async_step_local()
        return self.async_show_form(step_id="user", data_schema=vol.Schema({
            vol.Required("connection_type", default="cloud"): vol.In({"cloud": "Daikin Control cloud", "local": "G1 LAN (experimental read-only)"})}))

    async def async_step_local(self, user_input=None):
        return await self._form("local", user_input)

    async def async_step_cloud(self, user_input=None):
        errors = {}
        if user_input is not None:
            try:
                client = CloudClient(user_input["username"], user_input["password"])
                installations = await self.hass.async_add_executor_job(client.discover)
                self._cloud_input = dict(user_input)
                self._cloud_installations = installations
                return await self.async_step_installation()
            except CloudAuthError:
                errors["base"] = "invalid_auth"
            except CloudError:
                errors["base"] = "cannot_connect"
        return self.async_show_form(step_id="cloud", errors=errors, data_schema=vol.Schema({
            vol.Required("username"): str,
            vol.Required("password"): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)),
            vol.Required("enable_controls", default=True): bool}))

    async def async_step_installation(self, user_input=None):
        choices = {str(item["id"]): f"Impianto {index+1}" for index,item in enumerate(self._cloud_installations)}
        if user_input:
            installation_id = user_input["installation_id"]
            if installation_id not in choices:
                return self.async_abort(reason="invalid_installation")
            data = {**self._cloud_input, "connection_type": "cloud", "installation_id": installation_id}
            entry = getattr(self, "_cloud_update_entry", None)
            for existing in self._async_current_entries():
                if existing.data.get("connection_type") == "cloud" and existing.data.get("installation_id") == installation_id and (entry is None or existing.entry_id != entry.entry_id):
                    return self.async_abort(reason="already_configured")
            if entry:
                return self.async_update_reload_and_abort(entry, data_updates=data)
            return self.async_create_entry(title="Daikin Control cloud", data=data)
        return self.async_show_form(step_id="installation", data_schema=vol.Schema({
            vol.Required("installation_id", default=next(iter(choices))): vol.In(choices)}))

    async def async_step_reauth(self, entry_data):
        if entry_data.get("connection_type") == "cloud":
            self._cloud_update_entry = self._get_reauth_entry()
            return await self.async_step_cloud()
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        return await self._form("reauth_confirm", user_input)

    async def async_step_reconfigure(self, user_input=None):
        if self._get_reconfigure_entry().data.get("connection_type") == "cloud":
            self._cloud_update_entry = self._get_reconfigure_entry()
            return await self.async_step_cloud(user_input)
        return await self._form("reconfigure", user_input)

    async def _form(self, step, user_input):
        entry = self._get_reauth_entry() if step == "reauth_confirm" else self._get_reconfigure_entry() if step == "reconfigure" else None
        errors = {}
        if user_input is not None:
            try:
                gateway = Gateway(user_input[CONF_HOST], user_input[CONF_API_KEY])
                if any(existing.data.get(CONF_HOST) == gateway.host and (entry is None or existing.entry_id != entry.entry_id) for existing in self._async_current_entries()):
                    return self.async_abort(reason="already_configured")
                await self.hass.async_add_executor_job(gateway.snapshot)
            except GatewayAuthError:
                errors["base"] = "invalid_auth"
            except GatewayError:
                errors["base"] = "cannot_connect"
            else:
                data = {CONF_HOST: gateway.host, CONF_API_KEY: user_input[CONF_API_KEY]}
                if entry is not None:
                    return self.async_update_reload_and_abort(entry, data_updates=data)
                return self.async_create_entry(title=f"RoCon G1 {gateway.host}", data=data)
        default_host = entry.data[CONF_HOST] if entry is not None else vol.UNDEFINED
        schema = vol.Schema({vol.Required(CONF_HOST, default=default_host): str,
                             vol.Required(CONF_API_KEY): selector.TextSelector(selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD))})
        return self.async_show_form(step_id=step, data_schema=schema, errors=errors)
