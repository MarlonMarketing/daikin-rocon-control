"""Inspect saved cloud data offline; never derive device commands or active setpoints."""
from __future__ import annotations

import math
from datetime import datetime

from .client import DiagnosticError

MEASUREMENTS = ("actualTemperature", "outsideTemperature", "boilerActualTemperature", "actualLeadTemperature", "tvbhMix")
MODES = {1: "standby", 3: "heating", 4: "reduced", 5: "summer", 11: "automatic_1", 12: "automatic_2", 17: "cooling"}
DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def flag(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in ("true", "false"):
        return value.lower() == "true"
    return None


def _timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo is not None else None
    except ValueError:
        return None


def pair(value, *, boolean=False):
    if not isinstance(value, dict):
        return {"available": False}
    requested, confirmed = value.get("set"), value.get("confirmed")
    if boolean:
        requested, confirmed = flag(requested), flag(confirmed)
        valid = requested is not None and confirmed is not None
    else:
        valid = numeric(requested) and numeric(confirmed)
        requested = requested if numeric(requested) else None
        confirmed = confirmed if numeric(confirmed) else None
    set_date = _timestamp(value.get("setDate"))
    confirmed_date = _timestamp(value.get("confirmedDate"))
    effective = confirmed if set_date and confirmed_date and confirmed_date > set_date else requested
    return {"available": valid, "requested": requested, "confirmed": confirmed,
            "equal_values": valid and requested == confirmed,
            "effective_app_value": effective,
            "dated": set_date is not None and confirmed_date is not None,
            "note": "Uguaglianza/date cloud non provano applicazione fisica o misura fresca."}


def inspect_snapshot(snapshot):
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("data"), list):
        raise DiagnosticError("Il file non è uno snapshot prodotto dalla diagnostica.")
    summary = {"installations": len(snapshot["data"]), "circuits": 0,
               "sentinel_measurements": 0, "missing_measurements": 0}
    report = {"summary": summary, "measurement_freshness": "not_proven", "installations": []}
    for entry in snapshot["data"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("installation"), dict) or not isinstance(entry.get("circuits"), list):
            raise DiagnosticError("Struttura dello snapshot non riconosciuta.")
        metadata = entry["installation"]
        installation = {"software_number": metadata.get("softwareNumber") if numeric(metadata.get("softwareNumber")) else None,
                        "heating_generator_type": metadata.get("heatingGeneratorType") if numeric(metadata.get("heatingGeneratorType")) else None,
                        "circuits": []}
        for source in entry["circuits"]:
            if not isinstance(source, dict):
                raise DiagnosticError("Circuito dello snapshot non valido.")
            summary["circuits"] += 1
            circuit_type = source.get("type") if source.get("type") in ("direct", "heating", "water") else "unrecognized"
            circuit = {"type": circuit_type, "measurements": {}, "profiles": {}, "programs": {}}
            for key in MEASUREMENTS:
                value = source.get(key)
                sentinel = key == "actualTemperature" and circuit_type in ("direct", "heating") and numeric(value) and value in (-60, -40, 0)
                valid = numeric(value) and not sentinel
                quality = "numeric_without_measurement_timestamp" if valid else "sensor_disconnected_sentinel" if sentinel else "missing_or_invalid"
                summary["sentinel_measurements"] += int(sentinel)
                summary["missing_measurements"] += int(not valid and not sentinel)
                circuit["measurements"][key] = {"value": value if valid else None, "quality": quality}
            temperatures = source.get("setTemperature")
            for index in ("1", "2", "3"):
                circuit["profiles"][index] = pair(temperatures.get(index) if isinstance(temperatures, dict) else None)
            mode = source.get("operationMode")
            circuit["mode"] = pair(mode.get("type") if isinstance(mode, dict) else None)
            current = circuit["mode"].get("effective_app_value")
            circuit["mode"]["label"] = MODES.get(current, "unrecognized")
            circuit["one_time_heatup"] = pair(source.get("onetimeHeatupActive"), boolean=True)
            circuit["setback_heating"] = pair(source.get("setbackTemperatureHeating"))
            circuit["setback_absence"] = pair(source.get("setbackTemperatureAbsence"))
            programs = source.get("timeProgram")
            for number in ("1", "2"):
                program = programs.get(number) if isinstance(programs, dict) else None
                # Structural presence only; not interval validation or proof of active program.
                circuit["programs"][number] = {"days_present": sum(isinstance(program.get(day), dict) for day in DAYS) if isinstance(program, dict) else 0,
                    "three_slots_each_day": isinstance(program, dict) and all(isinstance(program.get(day), dict) and all(slot in program[day] for slot in ("1", "2", "3")) for day in DAYS)}
            installation["circuits"].append(circuit)
        report["installations"].append(installation)
    return report
