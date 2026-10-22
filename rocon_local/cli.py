"""Interactive credentials stay in memory. Only explicitly requested private exports."""
from __future__ import annotations

import argparse
import getpass
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from .client import CloudReader, DiagnosticError, probe_local, read_local_status
from .inspection import inspect_snapshot

ROOT = Path(__file__).resolve().parents[1]


def shape(value):
    """Structural preview: replace every user-controlled key and value."""
    if isinstance(value, dict):
        return {"type": "object", "fields": len(value)}
    if isinstance(value, list):
        return {"type": "array", "items": len(value)}
    return {"type": type(value).__name__}


def private_target(output: str):
    target = Path(output).resolve()
    private = (ROOT / "_private").resolve()
    if not private.is_relative_to(ROOT.resolve()) or not target.is_relative_to(private) or target == private:
        raise DiagnosticError("Gli export devono essere dentro _private del progetto.")
    if target.exists():
        raise FileExistsError("Il file di destinazione esiste già.")
    return target


def save_private(data, output: str):
    target = private_target(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    # Refuse overwrites and symlink targets; 0600 also protects POSIX exports.
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    with os.fdopen(os.open(target, flags, 0o600), "w", encoding="utf-8") as stream:
        json.dump({"acquired_at": datetime.now(timezone.utc).isoformat(),
                   "note": "Ora acquisizione, non ora delle misure. Dati privati, non pubblicare.",
                   "data": data}, stream, indent=2, ensure_ascii=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Diagnostica RoCon in sola lettura")
    sub = parser.add_subparsers(dest="command", required=True)
    cloud = sub.add_parser("cloud", help="Login interattivo e lettura installazioni/circuiti")
    cloud.add_argument("--output", required=True, help="Nuovo file dentro _private/")
    probe = sub.add_parser("probe", help="Porte 80/443/22 su un solo G1 privato")
    probe.add_argument("host")
    lan = sub.add_parser("lan", help="Lettura API LAN candidata; richiede API key locale già disponibile")
    lan.add_argument("host")
    lan.add_argument("--circuit", choices=("direct", "water"), required=True)
    lan.add_argument("--output", required=True)
    inspect = sub.add_parser("inspect", help="Analizza offline uno snapshot già acquisito")
    inspect.add_argument("snapshot")
    inspect.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command in ("cloud", "lan", "inspect"):
            private_target(args.output)
        if args.command == "cloud":
            username = input("Username cloud Daikin: ").strip()
            password = getpass.getpass("Password cloud Daikin (nascosta): ")
            reader = CloudReader()
            reader.login(username, password)
            password = None
            username = None
            data = reader.snapshot()
            save_private(data, args.output)
            print("Lettura salvata in _private. Nessun comando inviato alla caldaia.")
            print(json.dumps(shape(data)))
        elif args.command == "probe":
            print(json.dumps(probe_local(args.host), indent=2))
        elif args.command == "inspect":
            try:
                snapshot = json.loads(Path(args.snapshot).read_text(encoding="utf-8-sig"))
            except (ValueError, UnicodeError):
                raise DiagnosticError("Snapshot JSON non valido.") from None
            report = inspect_snapshot(snapshot)
            save_private(report, args.output)
            print(json.dumps(report["summary"]))
        else:
            api_key = getpass.getpass("API key LAN G1 già configurata (nascosta): ")
            data = read_local_status(args.host, api_key, args.circuit)
            api_key = None
            save_private(data, args.output)
            print("Risposta LAN salvata in _private; protocollo da verificare.")
        return 0
    except (DiagnosticError, OSError, EOFError, KeyboardInterrupt) as exc:
        # Do not include arbitrary exception text (may contain credential-bearing URLs).
        message = str(exc) if isinstance(exc, DiagnosticError) else "Operazione interrotta o file non scrivibile; nessun dettaglio privato stampato."
        print(message)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
