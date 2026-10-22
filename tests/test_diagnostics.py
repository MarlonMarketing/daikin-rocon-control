import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from rocon_local import cli
from rocon_local.client import (
    CLOUD_ORIGIN, MAX_BYTES, CloudReader, DiagnosticError, JsonTransport,
    NoRedirect, local_origin, read_local_status,
)


class FakeTransport:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def request(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return next(self.responses)


class Response:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self.body[:limit]


class DiagnosticsTests(unittest.TestCase):
    def test_only_login_posts_and_circuit_reads_have_verified_ownership(self):
        circuit = {"id": 7, "installation": "TEST_INSTALL", "type": "water"}
        fake = FakeTransport([{"user": {"id": 1}}, [{"id": "TEST_INSTALL"}], [circuit], circuit])
        reader = CloudReader(fake)
        reader.login("test-user", "test-password")
        snapshot = reader.snapshot()
        self.assertEqual(snapshot[0]["circuits"], [circuit])
        self.assertEqual(fake.calls[0][0], CLOUD_ORIGIN + "/login")
        self.assertIn("login", fake.calls[0][1])
        self.assertTrue(all(not kwargs for _, kwargs in fake.calls[1:]))
        self.assertTrue(all(url.startswith(CLOUD_ORIGIN + "/mobile/") for url, _ in fake.calls[1:]))

    def test_rejects_circuit_from_another_installation_before_detail_read(self):
        fake = FakeTransport([[{"id": "FIRST"}], [{"id": 7, "installation": "OTHER"}]])
        with self.assertRaises(DiagnosticError):
            CloudReader(fake).snapshot()
        self.assertEqual(len(fake.calls), 2)

    def test_rejects_detail_from_another_circuit(self):
        fake = FakeTransport([[{"id": "FIRST"}], [{"id": 7, "installation": "FIRST"}], {"id": 8, "installation": "FIRST"}])
        with self.assertRaises(DiagnosticError):
            CloudReader(fake).snapshot()

    def test_rejects_unknown_installation_format_without_guessing(self):
        with self.assertRaises(DiagnosticError):
            CloudReader(FakeTransport([{"models": []}])).snapshot()

    def test_identifier_cannot_change_path(self):
        fake = FakeTransport([[{"id": "FIRST"}], [{"id": "../logout", "installation": "FIRST"}]])
        with self.assertRaises(DiagnosticError):
            CloudReader(fake).snapshot()
        self.assertEqual(len(fake.calls), 2)

    def test_login_failure_does_not_print_server_body(self):
        with self.assertRaises(DiagnosticError) as error:
            CloudReader(FakeTransport([{"success": False, "error": "private-server-body"}])).login("u", "p")
        self.assertNotIn("private-server-body", str(error.exception))

    def test_local_only_rfc1918_literals(self):
        self.assertEqual(local_origin("192.168.50.10"), "http://192.168.50.10")
        for host in ("8.8.8.8", "127.0.0.1", "169.254.1.1", "gateway.local", "https://192.168.1.1", "192.168.1.1@evil.example", "::1"):
            with self.subTest(host=host), self.assertRaises(DiagnosticError):
                local_origin(host)

    def test_local_key_is_encoded_and_only_allowlisted_status_is_used(self):
        fake = FakeTransport([{"status": "test"}])
        self.assertEqual(read_local_status("10.0.0.2", "key&x=value", "water", fake), {"status": "test"})
        self.assertTrue(fake.calls[0][0].endswith("/api/status/water?apiKey=key%26x%3Dvalue"))
        with self.assertRaises(DiagnosticError):
            read_local_status("10.0.0.2", "key", "setting/water", fake)

    def test_redirect_never_forwards_credentials(self):
        with self.assertRaises(DiagnosticError):
            NoRedirect().redirect_request(None, None, 302, "found", {}, "https://other.example/")

    def test_transport_cannot_post_to_device(self):
        with self.assertRaises(DiagnosticError):
            JsonTransport().request("http://192.168.1.1/api/setting/water", login={"set": 1})

    def test_transport_errors_do_not_expose_key_urls(self):
        transport = JsonTransport()
        with patch.object(transport.opener, "open", side_effect=URLError("http://host/?apiKey=private-key")):
            with self.assertRaises(DiagnosticError) as error:
                transport.request("http://10.0.0.2/api/status/water?apiKey=private-key")
        self.assertNotIn("private-key", str(error.exception))

    def test_response_limit_and_invalid_json(self):
        transport = JsonTransport()
        for body in (b"x" * (MAX_BYTES + 1), b"not-json"):
            with self.subTest(size=len(body)), patch.object(transport.opener, "open", return_value=Response(body)):
                with self.assertRaises(DiagnosticError):
                    transport.request(CLOUD_ORIGIN + "/mobile/installation")

    def test_request_method_and_headers(self):
        transport = JsonTransport()
        with patch.object(transport.opener, "open", return_value=Response(b"{}")) as opened:
            transport.request(CLOUD_ORIGIN + "/mobile/installation")
            request = opened.call_args.args[0]
            self.assertEqual(request.method, "GET")
            self.assertEqual(dict((k.lower(), v) for k, v in request.header_items())["x-api-version"], "6")

    def test_private_export_refuses_public_location_and_overwrite(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(cli, "ROOT", Path(directory)):
            public = Path(directory) / "public.json"
            with self.assertRaises(DiagnosticError):
                cli.save_private({"private": "data"}, str(public))
            private = Path(directory) / "_private" / "read.json"
            cli.save_private({"private": "data"}, str(private))
            self.assertEqual(json.loads(private.read_text(encoding="utf-8"))["data"], {"private": "data"})
            with self.assertRaises(FileExistsError):
                cli.save_private({}, str(private))

    def test_preview_never_includes_user_keys_or_values(self):
        preview = json.dumps(cli.shape({"user-name": "user-address", "id": "installation-id"}))
        self.assertNotIn("user-name", preview)
        self.assertNotIn("user-address", preview)
        self.assertNotIn("installation-id", preview)

    def test_public_archive_selection_contains_tools_but_no_private_data(self):
        from tools.build_public import public_paths, ROOT
        selected = [path.relative_to(ROOT).as_posix() for path in public_paths()]
        self.assertIn("tools/acquire_apk.ps1", selected)
        self.assertIn("Diagnostica-cloud.cmd", selected)
        self.assertIn("custom_components/rocon_g1_local/manifest.json", selected)
        self.assertIn("custom_components/rocon_g1_local/gateway.py", selected)
        self.assertIn("tools/g1_readonly_diagnostics.sh", selected)
        self.assertTrue(all("_private" not in name and "__pycache__" not in name for name in selected))
        self.assertTrue(all(not name.endswith((".apk", ".jar", ".dex", ".har", ".pcap", ".key")) for name in selected))

    def test_invalid_public_output_fails_before_prompting_credentials(self):
        with patch("builtins.input") as prompt, patch("getpass.getpass") as password, patch("builtins.print"):
            self.assertEqual(cli.main(["cloud", "--output", "public-response.json"]), 1)
        prompt.assert_not_called()
        password.assert_not_called()


if __name__ == "__main__":
    unittest.main()
