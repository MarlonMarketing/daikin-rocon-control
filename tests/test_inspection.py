import unittest

from rocon_local.client import DiagnosticError
from rocon_local.inspection import flag, inspect_snapshot, pair


class InspectionTests(unittest.TestCase):
    def snapshot(self, circuit):
        return {"data": [{"installation": {"id": "PRIVATE_ID", "address": "PRIVATE_ADDRESS"}, "circuits": [circuit]}]}

    def test_string_false_is_not_treated_as_true(self):
        self.assertIs(flag("false"), False)
        self.assertIs(flag("TRUE"), True)
        self.assertIsNone(flag(1))
        self.assertIsNone(flag("unknown"))

    def test_disconnected_room_sensor_is_not_a_temperature(self):
        report = inspect_snapshot(self.snapshot({"type": "direct", "actualTemperature": -40}))
        temperature = report["installations"][0]["circuits"][0]["measurements"]["actualTemperature"]
        self.assertIsNone(temperature["value"])
        self.assertEqual(temperature["quality"], "sensor_disconnected_sentinel")
        self.assertEqual(report["summary"]["sentinel_measurements"], 1)

    def test_room_sentinel_rule_is_not_applied_to_water(self):
        report = inspect_snapshot(self.snapshot({"type": "water", "actualTemperature": 0}))
        self.assertEqual(report["installations"][0]["circuits"][0]["measurements"]["actualTemperature"]["value"], 0)

    def test_missing_and_non_finite_numbers_are_not_zero(self):
        for value in (None, True, "42", float("nan"), float("inf")):
            report = inspect_snapshot(self.snapshot({"type": "water", "actualTemperature": value}))
            self.assertIsNone(report["installations"][0]["circuits"][0]["measurements"]["actualTemperature"]["value"])

    def test_newer_confirmation_overrides_older_request_like_app(self):
        result = pair({"set": 45, "confirmed": 42, "setDate": "2026-01-01T00:00:00Z", "confirmedDate": "2026-01-01T00:01:00Z"})
        self.assertEqual(result["effective_app_value"], 42)
        self.assertFalse(result["equal_values"])

    def test_invalid_dates_do_not_prove_freshness(self):
        result = pair({"set": 45, "confirmed": 42, "setDate": "yesterday", "confirmedDate": "now"})
        self.assertFalse(result["dated"])
        report = inspect_snapshot(self.snapshot({"type": "water"}))
        self.assertEqual(report["measurement_freshness"], "not_proven")

    def test_identifying_metadata_is_not_in_inspection_report(self):
        report = inspect_snapshot(self.snapshot({"type": "water", "id": "CIRCUIT_ID", "name": "PERSON_NAME"}))
        for private in ("PRIVATE_ID", "PRIVATE_ADDRESS", "CIRCUIT_ID", "PERSON_NAME"):
            self.assertNotIn(private, str(report))

    def test_program_shape_requires_every_weekday_and_slot(self):
        report = inspect_snapshot(self.snapshot({"type": "water", "timeProgram": {"1": {"monday": {"1": {}, "2": {}, "3": {}}}}}))
        program = report["installations"][0]["circuits"][0]["programs"]["1"]
        self.assertEqual(program["days_present"], 1)
        self.assertFalse(program["three_slots_each_day"])

    def test_unknown_snapshot_is_rejected(self):
        with self.assertRaises(DiagnosticError):
            inspect_snapshot({"user": "not-a-snapshot"})


if __name__ == "__main__":
    unittest.main()
