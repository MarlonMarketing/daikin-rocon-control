"""Original fixed-origin mobile cloud client. Cookies stay in memory; no write retries."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from http.cookiejar import CookieJar
import json
import math
import re
import ssl
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import (HTTPSHandler, HTTPRedirectHandler, HTTPCookieProcessor,
                            ProxyHandler, Request, build_opener)

ORIGIN = "https://api.rotex-control.com"
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
MODES = {"standby": 1, "heating": 3, "reduced": 4, "summer": 5,
         "automatic_1": 11, "automatic_2": 12, "cooling": 17}
FIELDS = ("actualTemperature", "outsideTemperature", "boilerActualTemperature",
          "actualLeadTemperature", "tvbhMix", "heatGeneratorStatus", "errorCode")
ROOT_FIELDS = ("id", "type", "index", "installation", "setTemperature",
               "boilerSetTemperature", "setLeadTemperature", "onetimeHeatupActive",
               "outsideTemperature", "setbackTemperatureHeating", "setbackTemperatureAbsence",
               "timeProgram", "operationMode")


class CloudError(Exception):
    """Safe fixed message, never request URLs, response bodies or credentials."""


class CloudAuthError(CloudError):
    pass


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise CloudError("Cloud redirect refused")


def identifier(value):
    if isinstance(value, bool) or not isinstance(value, (str, int)) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", str(value)):
        raise CloudError("Invalid cloud identifier")
    return str(value)


def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def supports_cooling(metadata):
    return (type(metadata.get("heatingGeneratorType")) is int and metadata["heatingGeneratorType"] == 0
            or number(metadata.get("softwareNumber")) and metadata["softwareNumber"] > 399)


def effective(value):
    if not isinstance(value, dict):
        return None
    try:
        confirmed_date = datetime.fromisoformat(value["confirmedDate"].replace("Z", "+00:00"))
        set_date = datetime.fromisoformat(value["setDate"].replace("Z", "+00:00"))
        if confirmed_date > set_date:
            return value.get("confirmed")
    except (ValueError, TypeError, KeyError, AttributeError):
        pass
    return value.get("set", value.get("confirmed"))


def path_get(value, path):
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def _serialize(value):
    if isinstance(value, dict):
        if "confirmed" in value and "set" in value:
            requested = effective(value)
            if requested != value["confirmed"]:
                raise CloudError("An existing cloud change is pending; wait before another command")
            return {"set": deepcopy(requested), "confirmed": deepcopy(value["confirmed"])}
        return {key: _serialize(item) for key, item in value.items()
                if key not in ("setDate", "confirmedDate")}
    return deepcopy(value)


def _pair(payload, path, value):
    target = path_get(payload, path)
    if not isinstance(target, dict) or "set" not in target or "confirmed" not in target:
        raise CloudError("Setting missing from this circuit")
    target["set"] = deepcopy(value)


def _time_minutes(value, *, end=False):
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}:\d{2}", value):
        raise CloudError("Use HH:MM in 15-minute steps")
    hour, minute = map(int, value.split(":"))
    if minute not in (0, 15, 30, 45) or hour > 23 and not (end and hour == 24 and minute == 0):
        raise CloudError("Invalid program time")
    return hour * 60 + minute


def parse_program(text):
    if not isinstance(text, str) or len(text) > 64:
        raise CloudError("Three time slots required")
    parts = text.split(";")
    if len(parts) != 3:
        raise CloudError("Use three HH:MM-HH:MM slots separated by semicolons")
    result = []
    previous = 0
    for part in parts:
        split = part.strip().split("-")
        if len(split) != 2:
            raise CloudError("Invalid program interval")
        start, end = split
        a, b = _time_minutes(start), _time_minutes(end, end=True)
        if a == b == 0:
            result.append({"start": start, "end": end})
            continue
        if b <= a or a < previous:
            raise CloudError("Overlapping or inverted program intervals")
        previous = b
        result.append({"start": start, "end": end})
    return result


def build_command(circuit, command, value, installation=None):
    """Full app-shaped object, only selected set values change; dates never fabricated."""
    if circuit.get("type") not in ("direct", "heating", "water"):
        raise CloudError("Unsupported circuit type")
    for key in ("id", "installation", "type", "index", "setTemperature", "operationMode", "timeProgram"):
        if key not in circuit:
            raise CloudError("Incomplete circuit; refusing broad PUT")
    payload = _serialize({key: circuit[key] for key in ROOT_FIELDS if key in circuit})
    kind = circuit["type"]
    changes = {}
    if command.startswith("profile_") and command[-1:] in ("1", "2", "3") and len(command) == 9:
        minimum, maximum = (10, 70) if kind == "water" else (5, 40)
        if not number(value) or not minimum <= value <= maximum or not float(value * 2).is_integer():
            raise CloudError("Temperature outside app range or half-degree step")
        changes[("setTemperature", command[-1])] = value
    elif command in ("setbackTemperatureHeating", "setbackTemperatureAbsence"):
        if kind == "water" or not number(value) or not 5 <= value <= 40 or not float(value * 2).is_integer():
            raise CloudError("Invalid reduced/absence temperature")
        changes[(command,)] = value
    elif command == "mode":
        if kind == "water" or value not in MODES:
            raise CloudError("Shared modes must be changed on the heating circuit")
        if value == "cooling" and not supports_cooling(installation or {}):
            raise CloudError("Cooling not exposed for this controller")
        changes[("operationMode", "type")] = MODES[value]
    elif command == "boost":
        if kind != "water" or not isinstance(value, bool):
            raise CloudError("DHW boost requires a water circuit and boolean value")
        changes[("onetimeHeatupActive",)] = "true" if value else "false"
    elif command == "party":
        if kind == "water" or not number(value) or not 0 <= value <= 360 or value % 15:
            raise CloudError("Party duration must be 0–360 minutes, step 15")
        changes[("operationMode", "party", "hours")] = int(value)
    elif command.startswith("program_"):
        pieces = command.split("_")
        if len(pieces) != 3 or pieces[1] not in ("1", "2") or pieces[2] not in DAYS:
            raise CloudError("Invalid program selector")
        for slot, interval in enumerate(parse_program(value), 1):
            changes[("timeProgram", pieces[1], pieces[2], str(slot))] = interval
    elif command == "holiday":
        if kind == "water" or not isinstance(value, str):
            raise CloudError("Holiday period belongs to the shared heating circuit")
        try:
            first, last = [date.fromisoformat(item.strip()) for item in value.split("/")]
            if last < first or first.year < 2000 or last.year > 2098:
                raise ValueError
            exclusive = last + timedelta(days=1)
        except (ValueError, OverflowError):
            raise CloudError("Use YYYY-MM-DD/YYYY-MM-DD; end date is inclusive") from None
        for name, day in (("beginning", first), ("ending", exclusive)):
            for key, number_value in (("day", day.day), ("month", day.month), ("year", day.year % 100)):
                changes[("operationMode", "holiday", name, key)] = number_value
    elif command == "name":
        if not isinstance(value, str) or not value.strip() or len(value) > 64 or any(ord(char) < 32 for char in value):
            raise CloudError("Invalid circuit name")
        payload["name"] = value.strip()
        return payload, {("name",): value.strip()}
    else:
        raise CloudError("Command not allowlisted")
    for path, requested in changes.items():
        _pair(payload, path, requested)
    return payload, changes


class CloudClient:
    def __init__(self, username, password, *, transport=None):
        self._username, self._password = username, password
        self._transport = transport
        # Constructed in the HA event loop: defer certificate I/O to executor reads.
        self._opener = None
        self._login_at = 0
        self._lock = threading.Lock()
        self.installations = []
        self.last_command = "none"
        self.pending = None

    def _request(self, path, method="GET", payload=None):
        allowed = (method == "POST" and path == "/login" or
                   method == "GET" and (path == "/mobile/installation" or re.fullmatch(r"/mobile/heatingcircuit\?installationId=[A-Za-z0-9_-]{1,128}", path) or re.fullmatch(r"/mobile/heatingcircuit/[A-Za-z0-9_-]{1,128}", path)) or
                   method == "PUT" and re.fullmatch(r"/mobile/heatingcircuit/[A-Za-z0-9_-]{1,128}", path))
        if not allowed:
            raise CloudError("Cloud route refused")
        if self._transport:
            return self._transport(path, method, payload)
        if self._opener is None:
            self._opener = build_opener(ProxyHandler({}), _NoRedirect(),
                HTTPSHandler(context=ssl.create_default_context()), HTTPCookieProcessor(CookieJar()))
        data = json.dumps(payload, allow_nan=False).encode() if payload is not None else None
        request = Request(ORIGIN + path, data=data, method=method, headers={
            "Accept": "application/json", "Content-Type": "application/json", "X-Api-Version": "6"})
        try:
            with self._opener.open(request, timeout=12) as response:
                body = response.read(4 * 1024 * 1024 + 1)
        except HTTPError as exc:
            status = exc.code
            exc.close()
            if status in (401, 403):
                self._login_at = 0
                raise CloudAuthError("Cloud authentication required") from None
            raise CloudError(f"Cloud HTTP {status}; command is not retried") from None
        except (URLError, TimeoutError, OSError):
            raise CloudError("Cloud connection failed; command is not retried") from None
        if len(body) > 4 * 1024 * 1024:
            raise CloudError("Cloud response too large")
        if not body and method == "PUT":
            return {}
        try:
            result = json.loads(body)
        except (ValueError, UnicodeError):
            raise CloudError("Cloud JSON invalid") from None
        if isinstance(result, dict) and result.get("success") is False:
            raise CloudError("Cloud rejected request")
        return result

    def _login(self):
        if self._login_at and time.monotonic() - self._login_at < 4 * 3600:
            return
        if not self._username or not self._password:
            raise CloudAuthError("Cloud credentials required")
        result = self._request("/login", "POST", {"username": self._username, "password": self._password,
            "deviceInformation": {"deviceName": "Home Assistant RoCon", "appVersion": "1.5.13", "systemVersion": "Home Assistant", "language": "it", "country": "IT"}})
        if not isinstance(result, dict) or result.get("success") is False or not isinstance(result.get("user"), dict):
            raise CloudAuthError("Cloud login not confirmed")
        self._login_at = time.monotonic()

    def discover(self):
        with self._lock:
            self._login()
            result = self._request("/mobile/installation")
            if not isinstance(result, list) or not 1 <= len(result) <= 32 or not all(isinstance(item, dict) for item in result):
                raise CloudError("Cloud installations invalid")
            for item in result:
                identifier(item.get("id"))
            self.installations = result
            return deepcopy(result)

    def _read(self, installation_id):
        installation_id = identifier(installation_id)
        self._login()
        if not self.installations:
            result = self._request("/mobile/installation")
            if not isinstance(result, list) or len(result) > 32:
                raise CloudError("Cloud installations invalid")
            self.installations = result
        installation = next((item for item in self.installations if isinstance(item, dict) and str(item.get("id")) == installation_id), None)
        if installation is None:
            raise CloudError("Installation is not owned by this account")
        circuits = self._request("/mobile/heatingcircuit?" + urlencode({"installationId": installation_id}))
        if not isinstance(circuits, list) or not 1 <= len(circuits) <= 32:
            raise CloudError("Cloud circuits invalid")
        details = []
        for circuit in circuits:
            if not isinstance(circuit, dict) or str(circuit.get("installation")) != installation_id:
                raise CloudError("Circuit ownership mismatch")
            circuit_id = identifier(circuit.get("id"))
            detail = self._request("/mobile/heatingcircuit/" + circuit_id)
            if not isinstance(detail, dict) or str(detail.get("id")) != circuit_id or str(detail.get("installation")) != installation_id:
                raise CloudError("Cloud detail ownership mismatch")
            details.append(detail)
        result = {"installation": installation, "circuits": details}
        self._check_pending(result)
        return result

    def snapshot(self, installation_id):
        with self._lock:
            try:
                return self._read(installation_id)
            except CloudAuthError:
                # Reads can refresh an expired session once; writes never replay.
                self.installations = []
                self._login_at = 0
                return self._read(installation_id)

    def _check_pending(self, result):
        if not self.pending:
            return
        circuit_id, changes, sent_at = self.pending
        circuit = next((item for item in result["circuits"] if str(item.get("id")) == circuit_id), {})
        confirmed = True
        for path, value in changes.items():
            if path == ("name",):
                confirmed = confirmed and circuit.get("name") == value
                continue
            pair = path_get(circuit, path)
            if not isinstance(pair, dict) or pair.get("confirmed") != value:
                confirmed = False
                break
            try:
                timestamp = datetime.fromisoformat(pair["confirmedDate"].replace("Z", "+00:00"))
                confirmed = confirmed and timestamp >= sent_at
            except (KeyError, ValueError, AttributeError, TypeError):
                confirmed = False
        if confirmed:
            self.last_command = "confirmed_by_cloud"
            self.pending = None

    def command(self, installation_id, circuit_id, command, value):
        with self._lock:
            fresh = self._read(installation_id)
            if self.pending:
                raise CloudError("Previous command is pending or uncertain; no replay or queue")
            circuit_id = identifier(circuit_id)
            circuit = next((item for item in fresh["circuits"] if str(item["id"]) == circuit_id), None)
            if circuit is None:
                raise CloudError("Circuit is not owned by this installation")
            # Use an available DHW or boiler measurement, never room sentinel -40.
            critical = circuit.get("actualTemperature") if circuit.get("type") == "water" else circuit.get("boilerActualTemperature")
            if not number(critical):
                raise CloudError("Critical measurement unavailable; command refused")
            payload, changes = build_command(circuit, command, value, fresh["installation"])
            if all((circuit.get("name") if path == ("name",) else effective(path_get(circuit, path))) == target for path, target in changes.items()):
                return fresh  # True local no-op: no HTTP write, no fake confirmation.
            self.pending = (circuit_id, changes, datetime.now(timezone.utc))
            self.last_command = "uncertain"
            self._request("/mobile/heatingcircuit/" + circuit_id, "PUT", payload)
            self.last_command = "sent_waiting_confirmation"
            return self._read(installation_id)
