"""Bounded JSON reads. Credentials and remote bodies are never logged."""
from __future__ import annotations

import ipaddress
import json
import re
import socket
import ssl
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, ProxyHandler, Request, build_opener, HTTPSHandler

CLOUD_ORIGIN = "https://api.rotex-control.com"
MAX_BYTES = 4 * 1024 * 1024
TIMEOUT = 12
LOCAL_STATUS_PATHS = {"direct": "/api/status/direct", "water": "/api/status/water"}


class DiagnosticError(Exception):
    """Safe message: never includes URLs, credentials or server response bodies."""


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise DiagnosticError("Redirect rifiutato: nessuna credenziale inoltrata.")


def _identifier(value: object) -> str:
    if not isinstance(value, (str, int)) or isinstance(value, bool) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", str(value)):
        raise DiagnosticError("Identificativo assente o non valido nella risposta.")
    return quote(str(value), safe="")


class JsonTransport:
    def __init__(self, *, cookies: bool = False):
        # Direct connection: no inherited proxy forwarding credentials.
        handlers = [ProxyHandler({}), NoRedirect(), HTTPSHandler(context=ssl.create_default_context())]
        if cookies:
            handlers.append(HTTPCookieProcessor(CookieJar()))
        self.opener = build_opener(*handlers)

    def request(self, url: str, *, login: dict | None = None):
        headers = {"Accept": "application/json", "X-Api-Version": "6"}
        payload = None
        method = "GET"
        if login is not None:
            if url != CLOUD_ORIGIN + "/login":
                raise DiagnosticError("POST ammesso esclusivamente al login cloud ufficiale.")
            payload = json.dumps(login).encode("utf-8")
            headers["Content-Type"] = "application/json"
            method = "POST"
        request = Request(url, data=payload, headers=headers, method=method)
        try:
            with self.opener.open(request, timeout=TIMEOUT) as response:
                body = response.read(MAX_BYTES + 1)
        except HTTPError as exc:
            code = exc.code
            exc.close()
            raise DiagnosticError(f"HTTP {code}; nessun retry o comando al dispositivo.") from None
        except (URLError, TimeoutError, OSError):
            raise DiagnosticError("Connessione fallita o timeout; TLS non viene disabilitato.") from None
        if len(body) > MAX_BYTES:
            raise DiagnosticError("Risposta oltre il limite di dimensione.")
        try:
            return json.loads(body)
        except (ValueError, UnicodeError):
            raise DiagnosticError("Risposta JSON non valida.") from None


class CloudReader:
    """Only login and GET. Does not implement PUT/PATCH/DELETE or device commands."""
    def __init__(self, transport=None):
        self.transport = transport if transport is not None else JsonTransport(cookies=True)

    def login(self, username: str, password: str):
        if not username or not password:
            raise DiagnosticError("Username e password obbligatori.")
        result = self.transport.request(CLOUD_ORIGIN + "/login", login={
            "username": username,
            "password": password,
            "deviceInformation": {
                "deviceName": "RoCon protocol diagnostics",
                "appVersion": "1.5.13",
                "systemVersion": "Python diagnostics",
                "language": "it",
                "country": "IT",
            },
        })
        # APK expects a user object; previous installation also returned success.
        if not isinstance(result, dict) or result.get("success") is False or not isinstance(result.get("user"), dict):
            raise DiagnosticError("Login non confermato dalla risposta cloud.")

    def snapshot(self):
        installations = self.transport.request(CLOUD_ORIGIN + "/mobile/installation")
        if not isinstance(installations, list) or not installations:
            raise DiagnosticError("Elenco installazioni assente o formato non verificato.")
        if len(installations) > 32:
            raise DiagnosticError("Troppe installazioni per questa diagnosi limitata.")
        result = []
        for installation in installations:
            if not isinstance(installation, dict):
                raise DiagnosticError("Installazione non valida.")
            installation_id = installation.get("id")
            _identifier(installation_id)
            circuits = self.transport.request(CLOUD_ORIGIN + "/mobile/heatingcircuit?" + urlencode({"installationId": installation_id}))
            if not isinstance(circuits, list) or len(circuits) > 32:
                raise DiagnosticError("Elenco circuiti non valido o oltre limite.")
            details = []
            for circuit in circuits:
                if not isinstance(circuit, dict):
                    raise DiagnosticError("Circuito non valido.")
                # A list result must explicitly belong to the installation.
                if str(circuit.get("installation")) != str(installation_id):
                    raise DiagnosticError("Circuito non associato all'installazione attesa.")
                circuit_id = circuit.get("id")
                detail = self.transport.request(CLOUD_ORIGIN + "/mobile/heatingcircuit/" + _identifier(circuit_id))
                if not isinstance(detail, dict) or str(detail.get("id")) != str(circuit_id) or str(detail.get("installation")) != str(installation_id):
                    raise DiagnosticError("Dettaglio circuito non coerente; acquisizione interrotta.")
                details.append(detail)
            result.append({"installation": installation, "circuits": details})
        return result


def local_origin(host: str) -> str:
    """Require a private IP literal; no public host, URL, DNS or redirect target."""
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        raise DiagnosticError("Inserire soltanto l'indirizzo IP privato del proprio G1.") from None
    rfc1918 = any(address in net for net in (
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
    )) if address.version == 4 else False
    if not rfc1918:
        raise DiagnosticError("Questa versione accetta solo IPv4 privati RFC1918.")
    return "http://" + str(address)


def read_local_status(host: str, api_key: str, circuit: str, transport=None):
    origin = local_origin(host)
    if circuit not in LOCAL_STATUS_PATHS or not api_key:
        raise DiagnosticError("Tipo circuito o API key locale assente/non valida.")
    transport = transport if transport is not None else JsonTransport()
    # Candidate endpoints from independent G1 research, not verified on every firmware.
    return transport.request(origin + LOCAL_STATUS_PATHS[circuit] + "?" + urlencode({"apiKey": api_key}))


def probe_local(host: str):
    local_origin(host)
    results = []
    # Fixed ports on one user-selected host. No login or device writes.
    for port in (80, 443, 22):
        try:
            with socket.create_connection((host, port), timeout=3):
                reachable = True
        except OSError:
            reachable = False
        results.append({"port": port, "reachable": reachable})
    return results
