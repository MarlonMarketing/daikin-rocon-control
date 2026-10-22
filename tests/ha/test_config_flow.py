"""Home Assistant runtime tests. Run in Linux CI, with a mocked G1 only."""
from unittest.mock import patch

import pytest
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResultType
from custom_components.rocon_g1_local.gateway import GatewayAuthError, GatewayError


@pytest.fixture(autouse=True)
def allow_custom_integration(enable_custom_integrations):
    yield


@pytest.mark.parametrize("exception,error", [
    (GatewayAuthError("rejected"), "invalid_auth"),
    (GatewayError("unreachable"), "cannot_connect"),
])
async def test_config_flow_errors_do_not_create_entry(hass, exception, error):
    with patch("custom_components.rocon_g1_local.gateway.Gateway.snapshot", side_effect=exception):
        result = await hass.config_entries.flow.async_init(
            "rocon_g1_local", context={"source": config_entries.SOURCE_USER},
            data={"host": "192.168.50.2", "api_key": "synthetic-test-key"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}
    assert not hass.config_entries.async_entries("rocon_g1_local")


async def test_config_flow_creates_readonly_sensors(hass):
    rows = {"water_status_dhwTemperature": {
        "device": "water", "field": "dhwTemperature", "section": "status",
        "value": 48.3, "temperature": True, "enabled": True}}
    with patch("custom_components.rocon_g1_local.gateway.Gateway.snapshot", return_value=rows):
        result = await hass.config_entries.flow.async_init(
            "rocon_g1_local", context={"source": config_entries.SOURCE_USER},
            data={"host": "192.168.50.2", "api_key": "synthetic-test-key"})
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    entry = result["result"]
    assert entry.state is config_entries.ConfigEntryState.LOADED
    sensors = [state for state in hass.states.async_all("sensor")
               if state.attributes.get("source") == "g1_local_cache"]
    assert len(sensors) == 1
    assert sensors[0].state == "48.3"
    assert sensors[0].attributes["rocon_field"] == "dhwTemperature"
    assert sensors[0].attributes["measurement_timestamp_available"] is False
    assert "synthetic-test-key" not in str(sensors[0].attributes)
    assert not hass.states.async_all("climate")
    assert not hass.states.async_all("water_heater")
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_cloud_config_flow_and_platforms(hass):
    from tests.test_cloud_controls import circuit
    source = circuit()
    data = {"installation":{"id":"test-installation"},"circuits":[source]}
    with patch("custom_components.rocon_g1_local.cloud.CloudClient.discover", return_value=[data["installation"]]), patch("custom_components.rocon_g1_local.cloud.CloudClient.snapshot", return_value=data):
        result = await hass.config_entries.flow.async_init("rocon_g1_local",context={"source":config_entries.SOURCE_USER})
        assert result["step_id"] == "user"
        result = await hass.config_entries.flow.async_configure(result["flow_id"],{"connection_type":"cloud"})
        assert result["step_id"] == "cloud"
        result = await hass.config_entries.flow.async_configure(result["flow_id"],{"username":"synthetic-user","password":"synthetic-password","enable_controls":True})
        assert result["step_id"] == "installation"
        result = await hass.config_entries.flow.async_configure(result["flow_id"],{"installation_id":"test-installation"})
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["result"].state is config_entries.ConfigEntryState.LOADED
    assert len(hass.states.async_all("number")) == 3
    assert len(hass.states.async_all("switch")) == 1
    sensors = [state for state in hass.states.async_all("sensor") if state.attributes.get("source") == "rocon_cloud"]
    assert sensors
    assert "synthetic-password" not in str(sensors)
    assert await hass.config_entries.async_unload(result["result"].entry_id)
