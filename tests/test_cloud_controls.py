"""Synthetic fixtures only. No account, network or heating commands used by tests."""
from copy import deepcopy
from datetime import datetime, timezone, timedelta
import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location("cloud_under_test", Path(__file__).resolve().parents[1] / "custom_components/rocon_g1_local/cloud.py")
cloud = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cloud)


def pair(value):
    return {"set":deepcopy(value), "confirmed":deepcopy(value), "setDate":"2025-01-01T00:00:00Z", "confirmedDate":"2025-01-01T00:00:00Z"}


def circuit(kind="water"):
    return {"id":"test-water" if kind=="water" else "test-direct", "installation":"test-installation", "type":kind, "index":1,
        "name":"Synthetic circuit", "actualTemperature":44, "boilerActualTemperature":32,
        "setTemperature":{str(i):pair(40+i) for i in (1,2,3)},
        "setbackTemperatureHeating":pair(18), "setbackTemperatureAbsence":pair(16),
        "onetimeHeatupActive":pair("false"),
        "operationMode":{"type":pair(3),"party":{"hours":pair(0)},"holiday":{
            key:{"day":pair(2 if key=="ending" else 1),"month":pair(1),"year":pair(25)} for key in ("beginning","ending")}},
        "timeProgram":{n:{day:{str(i):pair({"start":"00:00","end":"00:00"}) for i in (1,2,3)} for day in cloud.DAYS} for n in ("1","2")}}


class CloudCommandTests(unittest.TestCase):
    def test_profile_preserves_confirmed_and_other_profiles(self):
        original=circuit(); before=deepcopy(original)
        payload,changes=cloud.build_command(original,"profile_1",45.5)
        self.assertEqual(original,before)
        self.assertEqual(payload["setTemperature"]["1"],{"set":45.5,"confirmed":41})
        self.assertEqual(payload["setTemperature"]["2"],{"set":42,"confirmed":42})
        self.assertNotIn("actualTemperature",payload)
        self.assertNotIn("name",payload)
        self.assertNotIn("Date",str(payload))
        self.assertEqual(changes,{("setTemperature","1"):45.5})

    def test_ranges_and_unknown_commands_refused(self):
        for command,value in [("profile_1",70.5),("profile_1",45.1),("profile_1",True),("profile_1",float("nan")),("boilerSetTemperature",50),("curve",1)]:
            with self.subTest(command=command,value=value),self.assertRaises(cloud.CloudError):cloud.build_command(circuit(),command,value)
        with self.assertRaises(cloud.CloudError):cloud.build_command(circuit("direct"),"profile_1",45)

    def test_mode_proxy_cannot_write_water(self):
        with self.assertRaises(cloud.CloudError):cloud.build_command(circuit(),"mode","summer")
        result,_=cloud.build_command(circuit("direct"),"mode","summer")
        self.assertEqual(result["operationMode"]["type"]["set"],5)

    def test_cooling_requires_app_capability(self):
        with self.assertRaises(cloud.CloudError):cloud.build_command(circuit("direct"),"mode","cooling",{"softwareNumber":300,"heatingGeneratorType":1})
        result,_=cloud.build_command(circuit("direct"),"mode","cooling",{"softwareNumber":300,"heatingGeneratorType":0})
        self.assertEqual(result["operationMode"]["type"]["set"],17)

    def test_boost_serializes_strings(self):
        result,_=cloud.build_command(circuit(),"boost",True)
        self.assertEqual(result["onetimeHeatupActive"],{"set":"true","confirmed":"false"})
        with self.assertRaises(cloud.CloudError):cloud.build_command(circuit(),"boost","true")

    def test_party_is_minutes_not_hours(self):
        result,_=cloud.build_command(circuit("direct"),"party",90)
        self.assertEqual(result["operationMode"]["party"]["hours"]["set"],90)
        with self.assertRaises(cloud.CloudError):cloud.build_command(circuit("direct"),"party",361)

    def test_holiday_end_inclusive_leap_and_year_rollover(self):
        for period,expected in [("2028-02-28/2028-02-29",(1,3,28)),("2027-12-30/2027-12-31",(1,1,28))]:
            result,_=cloud.build_command(circuit("direct"),"holiday",period)
            ending=result["operationMode"]["holiday"]["ending"]
            self.assertEqual(tuple(ending[k]["set"] for k in ("day","month","year")),expected)
        with self.assertRaises(cloud.CloudError):cloud.build_command(circuit("direct"),"holiday","2027-02-29/2027-03-01")

    def test_daily_program_and_24h(self):
        result,_=cloud.build_command(circuit(),"program_2_sunday","06:00-08:00;18:00-24:00;00:00-00:00")
        self.assertEqual(result["timeProgram"]["2"]["sunday"]["2"]["set"]["end"],"24:00")
        for bad in ["06:01-08:00;00:00-00:00;00:00-00:00","08:00-06:00;00:00-00:00;00:00-00:00","06:00-08:00;07:00-09:00;00:00-00:00","06:00-08:00","24:00-24:00;00:00-00:00;00:00-00:00"]:
            with self.subTest(bad=bad),self.assertRaises(cloud.CloudError):cloud.parse_program(bad)

    def test_pending_changes_are_not_replayed(self):
        source=circuit();source["setTemperature"]["2"]["set"]=55
        with self.assertRaises(cloud.CloudError):cloud.build_command(source,"profile_1",45)

    def test_newer_confirmed_value_does_not_replay_older_request(self):
        source=circuit();source["setTemperature"]["2"].update(set=55,confirmed=43,confirmedDate="2025-01-02T00:00:00Z")
        result,_=cloud.build_command(source,"profile_1",45)
        self.assertEqual(result["setTemperature"]["2"],{"set":43,"confirmed":43})

    def test_missing_fields_fail_instead_of_defaulting(self):
        source=circuit();del source["timeProgram"]
        with self.assertRaises(cloud.CloudError):cloud.build_command(source,"profile_1",45)

    def client(self, fail_write=False):
        source=circuit(); calls=[]
        def transport(path,method,payload):
            calls.append((path,method,deepcopy(payload)))
            if path=="/login":return {"success":True,"user":{}}
            if path=="/mobile/installation":return [{"id":"test-installation"}]
            if "?installationId=" in path:return [deepcopy(source)]
            if method=="GET":return deepcopy(source)
            if fail_write:raise cloud.CloudError("Synthetic timeout")
            source["setTemperature"]["1"]["set"]=payload["setTemperature"]["1"]["set"]
            return {"success":True}
        return cloud.CloudClient("synthetic-user","synthetic-password",transport=transport),source,calls

    def test_write_once_then_pending_until_dated_confirmation(self):
        client,source,calls=self.client()
        client.command("test-installation","test-water","profile_1",45)
        self.assertEqual(client.last_command,"sent_waiting_confirmation")
        with self.assertRaises(cloud.CloudError):client.command("test-installation","test-water","profile_1",46)
        self.assertEqual(sum(method=="PUT" for _,method,_ in calls),1)
        source["setTemperature"]["1"].update(confirmed=45,confirmedDate=(datetime.now(timezone.utc)+timedelta(seconds=1)).isoformat())
        client.snapshot("test-installation")
        self.assertEqual(client.last_command,"confirmed_by_cloud")
        self.assertIsNone(client.pending)

    def test_timeout_keeps_uncertainty_and_no_retry(self):
        client,_,calls=self.client(fail_write=True)
        with self.assertRaises(cloud.CloudError):client.command("test-installation","test-water","profile_1",45)
        with self.assertRaises(cloud.CloudError):client.command("test-installation","test-water","profile_1",45)
        self.assertEqual(client.last_command,"uncertain")
        self.assertEqual(sum(method=="PUT" for _,method,_ in calls),1)

    def test_noop_has_no_write_and_no_false_confirmation(self):
        client,_,calls=self.client()
        client.command("test-installation","test-water","profile_1",41)
        self.assertFalse(any(method=="PUT" for _,method,_ in calls))
        self.assertEqual(client.last_command,"none")

    def test_foreign_installation_and_circuit_fail_before_write(self):
        for installation,circuit_id in [("other","test-water"),("test-installation","other")]:
            client,_,calls=self.client()
            with self.assertRaises(cloud.CloudError):client.command(installation,circuit_id,"profile_1",45)
            self.assertFalse(any(method=="PUT" for _,method,_ in calls))

    def test_missing_critical_measurement_blocks_write(self):
        client,source,calls=self.client();source["actualTemperature"]=None
        with self.assertRaises(cloud.CloudError):client.command("test-installation","test-water","profile_1",45)
        self.assertFalse(any(method=="PUT" for _,method,_ in calls))

    def test_arbitrary_route_and_redirect_are_refused(self):
        client,_,calls=self.client()
        for path,method in [("https://other.example/","GET"),("/mobile/heatingcircuit/test-water","DELETE"),("/web/import","POST")]:
            with self.assertRaises(cloud.CloudError):client._request(path,method)
        self.assertFalse(calls)
        with self.assertRaises(cloud.CloudError):cloud._NoRedirect().redirect_request(None)
