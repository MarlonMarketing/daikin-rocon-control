"""Original read-only G1 adapter. No Home Assistant dependencies or device writes."""
from __future__ import annotations

import ipaddress
import json
import math
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

MAX_BYTES = 512 * 1024
SNAPSHOT_TIMEOUT = 30
DEVICE = re.compile(r"(?:direct|water|HC(?:[1-9]|1[0-6]))\Z")
PROGRAM = re.compile(r"(?:dhw|heating)Program[12](?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[123]\Z")
TEMPERATURE_SETTINGS = {"dhwSetpoint", "boilerSetTemperature", "roomSetpoint", "roomSetpoint1", "roomSetpoint2", "roomSetpoint3", "ecoSetpoint", "flowTemperatureDay", "absenceSetpoint"}
OTHER_SETTINGS = {"oneOffHeatingUpDhw", "partyDuration", "holidayStart", "holidayEnd", "mode"}
STATUS_FIELDS = {"direct": ("outsideTemperature", "boilerTemperature", "error"), "water": ("dhwTemperature", "error")}


class GatewayError(Exception):
    """Safe error, without request URL or key."""


class GatewayAuthError(GatewayError):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise GatewayError("G1 redirect refused")


def validate_host(host):
    try:
        address = ipaddress.IPv4Address(host)
    except ipaddress.AddressValueError:
        raise GatewayError("A private IPv4 address is required") from None
    if not any(address in ipaddress.IPv4Network(net) for net in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")):
        raise GatewayError("A private IPv4 address is required")
    return str(address)


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def normalize_responses(responses):
    """Stable sensor descriptions; no default-zero coercion or write capability."""
    rows = {}
    for device, payload in responses.items():
        if not DEVICE.fullmatch(device):
            continue
        status = payload.get("status", {})
        settings = payload.get("setting", {})
        fields = STATUS_FIELDS.get(device, ("roomTemperature", "error"))
        for field in fields:
            value = status.get(field)
            if not _number(value) or (field == "roomTemperature" and value in (-60, -40, 0)):
                value = None
            key = f"{device}_status_{field}"
            rows[key] = {"device": device, "field": field, "section": "status", "value": value,
                         "temperature": field != "error", "enabled": field != "error"}
        for field, raw in settings.items():
            if field not in TEMPERATURE_SETTINGS | OTHER_SETTINGS and not PROGRAM.fullmatch(field):
                continue
            # The legacy API has inconsistent field typing. Expose bounded scalar
            # cache values only, as sensors; never interpret them as commands.
            if field in TEMPERATURE_SETTINGS:
                value = raw if _number(raw) else None
            elif _number(raw) or isinstance(raw, bool):
                value = raw
            elif isinstance(raw, str) and len(raw) <= 64:
                value = raw
            else:
                value = None
            key = f"{device}_setting_{field}"
            rows[key] = {"device": device, "field": field, "section": "setting", "value": value,
                         "temperature": field in TEMPERATURE_SETTINGS, "enabled": False}
    return rows


class Gateway:
    def __init__(self, host, api_key, *, transport=None):
        self.host = validate_host(host)
        if not isinstance(api_key, str) or not api_key:
            raise GatewayAuthError("Local API key required")
        self._key = api_key
        self._transport = transport

    def _get(self, path, deadline):
        if not re.fullmatch(r"/api(?:/(?:status|setting)/(?:direct|water|HC(?:[1-9]|1[0-6])))?", path):
            raise GatewayError("Read endpoint not allowed")
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise GatewayError("G1 snapshot timeout")
        if self._transport is not None:
            result = self._transport(path)
            if not isinstance(result, dict):
                raise GatewayError("G1 JSON object required")
            return result
        url = "http://" + self.host + path + "?" + urlencode({"apiKey": self._key})
        opener = build_opener(ProxyHandler({}), _NoRedirect())
        try:
            with opener.open(Request(url, headers={"Accept": "application/json"}, method="GET"), timeout=min(8, remaining)) as response:
                body = response.read(MAX_BYTES + 1)
        except HTTPError as exc:
            status = exc.code
            exc.close()
            if status in (401, 403):
                raise GatewayAuthError("G1 local authentication failed") from None
            raise GatewayError("G1 HTTP request failed") from None
        except (URLError, TimeoutError, OSError):
            raise GatewayError("G1 connection unavailable") from None
        if len(body) > MAX_BYTES:
            raise GatewayError("G1 response too large")
        try:
            result = json.loads(body)
        except (ValueError, UnicodeError):
            raise GatewayError("G1 JSON invalid") from None
        if not isinstance(result, dict):
            raise GatewayError("G1 JSON object required")
        return result

    def snapshot(self):
        deadline = time.monotonic() + SNAPSHOT_TIMEOUT
        listed = self._get("/api", deadline)
        devices = sorted(name for name in listed if DEVICE.fullmatch(name))
        if not devices:
            raise GatewayError("No compatible G1 devices returned")
        responses = {}
        for device in devices:
            # Ignore server-supplied URLs. Always construct fixed same-host GETs.
            responses[device] = {section: self._get(f"/api/{section}/{device}", deadline) for section in ("status", "setting")}
        return normalize_responses(responses)
