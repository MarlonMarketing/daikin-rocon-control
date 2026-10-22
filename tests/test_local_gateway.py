import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

PATH = Path(__file__).resolve().parents[1] / "custom_components/rocon_g1_local/gateway.py"
SPEC = importlib.util.spec_from_file_location("g1_gateway_under_test", PATH)
gateway = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gateway)


class LocalGatewayTests(unittest.TestCase):
    def test_only_same_host_read_routes_ignore_advertised_urls(self):
        calls = []
        def transport(path):
            calls.append(path)
            if path == "/api":
                return {"water": {"statusUrl": "http://other.example/"}, "direct": {}, "HC1": {}, "../../setting": {}}
            return {}
        rows = gateway.Gateway("192.168.50.2", "not-a-real-key", transport=transport).snapshot()
        self.assertEqual(len(calls), 7)
        self.assertTrue(all(path == "/api" or path.startswith(("/api/status/", "/api/setting/")) for path in calls))
        self.assertIn("water_status_dhwTemperature", rows)

    def test_rejects_non_private_hosts_and_userinfo(self):
        for host in ("example.com", "127.0.0.1", "8.8.8.8", "192.168.1.1@other", "http://192.168.1.1"):
            with self.subTest(host=host), self.assertRaises(gateway.GatewayError):
                gateway.Gateway(host, "key")

    def test_sentinels_and_missing_values_never_become_zero(self):
        rows = gateway.normalize_responses({"HC1": {"status": {"roomTemperature": -40}, "setting": {}}, "water": {"status": {}, "setting": {}}})
        self.assertIsNone(rows["HC1_status_roomTemperature"]["value"])
        self.assertIsNone(rows["water_status_dhwTemperature"]["value"])

    def test_advanced_settings_are_disabled_and_do_not_imply_units(self):
        rows = gateway.normalize_responses({"water": {"status": {"dhwTemperature": 42.5}, "setting": {"dhwSetpoint": 45, "partyDuration": 60, "dhwProgram1Mon1": "06:00-08:00", "unexpected": "private-text"}}})
        self.assertEqual(rows["water_status_dhwTemperature"]["value"], 42.5)
        self.assertTrue(rows["water_setting_dhwSetpoint"]["temperature"])
        self.assertFalse(rows["water_setting_partyDuration"]["temperature"])
        self.assertFalse(rows["water_setting_dhwProgram1Mon1"]["enabled"])
        self.assertNotIn("private-text", str(rows))

    def test_infinite_booleans_and_long_strings_not_temperatures(self):
        for value in (float("nan"), float("inf"), True, "42"):
            rows = gateway.normalize_responses({"water": {"status": {"dhwTemperature": value}, "setting": {"dhwSetpoint": value}}})
            self.assertIsNone(rows["water_status_dhwTemperature"]["value"])
            self.assertIsNone(rows["water_setting_dhwSetpoint"]["value"])

    def test_empty_discovery_is_not_a_working_gateway(self):
        with self.assertRaises(gateway.GatewayError):
            gateway.Gateway("10.0.0.2", "key", transport=lambda path: {}).snapshot()

    def test_non_object_payload_rejected(self):
        with self.assertRaises(gateway.GatewayError):
            gateway.Gateway("10.0.0.2", "key", transport=lambda path: []).snapshot()

    def test_no_key_in_connection_error(self):
        client = gateway.Gateway("10.0.0.2", "secret-test-value")
        with patch.object(gateway, "build_opener") as build:
            build.return_value.open.side_effect = URLError("url contains secret-test-value")
            with self.assertRaises(gateway.GatewayError) as error:
                client.snapshot()
        self.assertNotIn("secret-test-value", str(error.exception))

    def test_redirect_is_refused(self):
        with self.assertRaises(gateway.GatewayError):
            gateway._NoRedirect().redirect_request(None, None, 302, "found", {}, "http://other.example")

    def test_real_transport_builds_get_and_encodes_key(self):
        client = gateway.Gateway("10.0.0.2", "key&other=1")
        with patch.object(gateway, "build_opener") as build:
            build.return_value.open.return_value.__enter__.return_value.read.return_value = b'{}'
            client._get("/api/status/water", float("inf"))
            request = build.return_value.open.call_args.args[0]
            self.assertEqual(request.method, "GET")
            self.assertEqual(request.full_url, "http://10.0.0.2/api/status/water?apiKey=key%26other%3D1")

    def test_http_401_is_auth_error_without_echoing_private_response(self):
        client = gateway.Gateway("10.0.0.2", "private-test-key")
        failure = HTTPError("http://10.0.0.2/?apiKey=private-test-key", 401, "private-server-error", {}, io.BytesIO(b"private-body"))
        with patch.object(gateway, "build_opener") as build:
            build.return_value.open.side_effect = failure
            with self.assertRaises(gateway.GatewayAuthError) as error:
                client.snapshot()
        self.assertNotIn("private-test-key", str(error.exception))
        self.assertNotIn("private-body", str(error.exception))

    def test_no_setting_or_export_post_route_is_callable(self):
        client = gateway.Gateway("10.0.0.2", "key", transport=lambda path: {})
        for path in ("/web/import", "/web/export.json", "/api/setting/water/extra", "/logout"):
            with self.subTest(path=path), self.assertRaises(gateway.GatewayError):
                client._get(path, float("inf"))


if __name__ == "__main__":
    unittest.main()
