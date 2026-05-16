Your disk is still full (ENOSPC), so nothing could be written under projects/python/. After you free space, replace projects/python/main.py with the script below (single file — no extra package dirs).

What it does
Command	Purpose
python main.py compile
Rabid-compile: mount AGI from ApplePiRadio/, build both DBs, write manifest + report
python main.py serve --open
Browser hub at http://127.0.0.1:8765/ with spawnable apps
python main.py toggle deepgreen
Use hour_clock_resource_container(applepiradiokat).db
python main.py toggle radio_efficacy
Use radioEfficacy.db (stub until you extend it)
python main.py status
JSON status of mounts and active DB
Internal layout (created on first run, next to main.py):

projects/python/
  main.py
  db/hour_clock_resource_container(applepiradiokat).db
  db/radioEfficacy.db
  agi/mounted_agi_manifest.json
  compile/rabid_compile_report.json
Mounted AGI: Alexandria Alpha/Beta/Gamma, Light XRS header, wormhole DB, quantum Circuit.PY, deepGreen reference from ApplePiRadio.ps.

Spawnable browser apps: trajectory-alpha/beta/gamma, ApplePiRadioCat, deepGreen panel, radioEfficacy, quantum-lattice, hour-clock.

Free disk space first, then paste this into projects/python/main.py:


#!/usr/bin/env python3
"""
ApplePiRadioKat — .db compilation, rabid-compiler, AGI mount, browser hub.
Internal layout (relative to this file):
  db/hour_clock_resource_container(applepiradiokat).db
  db/radioEfficacy.db
  agi/mounted_agi_manifest.json
  compile/rabid_compile_report.json
Registry: https://deepgreenantennas.github.io/applepiradiokat/
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import sqlite3
import sys
import threading
import webbrowser
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse
ROOT = Path(__file__).resolve().parent
APPLEPIRADIO = ROOT.parent / "ApplePiRadio"
DB_DIR = ROOT / "db"
AGI_DIR = ROOT / "agi"
COMPILE_DIR = ROOT / "compile"
HOUR_CLOCK_DB = DB_DIR / "hour_clock_resource_container(applepiradiokat).db"
RADIO_EFFICACY_DB = DB_DIR / "radioEfficacy.db"
REGISTRY_URI = "https://deepgreenantennas.github.io/applepiradiokat/"
SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS agi_components (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, source_path TEXT,
    component_type TEXT, status TEXT NOT NULL, payload TEXT, mounted_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS hour_clock_slots (
    hour INTEGER NOT NULL CHECK (hour >= 0 AND hour <= 23),
    slot TEXT NOT NULL, resource_key TEXT NOT NULL, resource_value TEXT,
    PRIMARY KEY (hour, slot));
CREATE TABLE IF NOT EXISTS spawnable_apps (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, route TEXT NOT NULL UNIQUE,
    description TEXT, backend TEXT NOT NULL DEFAULT 'deepgreen', enabled INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS compile_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT, phase TEXT NOT NULL,
    message TEXT NOT NULL, created_at TEXT NOT NULL);
"""
SPAWNABLE_APPS = (
    ("trajectory-alpha", "Alexandria Alpha", "/apps/trajectory-alpha", "Alpha trajectory loader.", "deepgreen"),
    ("trajectory-beta", "Alexandria Beta", "/apps/trajectory-beta", "Beta trajectory loader.", "deepgreen"),
    ("trajectory-gamma", "Alexandria Gamma", "/apps/trajectory-gamma", "Gamma trajectory loader.", "deepgreen"),
    ("applepi-radio-cat", "ApplePiRadioCat", "/apps/applepi-radio-cat", "Surface-interaction cat AGI.", "deepgreen"),
    ("deepgreen-panel", "deepGreen Panel", "/apps/deepgreen", "deepGreen self-learning rail.", "deepgreen"),
    ("radio-efficacy", "radioEfficacy", "/apps/radio-efficacy", "Radio efficacy DB (create later).", "radio_efficacy"),
    ("quantum-lattice", "Quantum Lattice", "/apps/quantum-lattice", "XrC quantum circuit.", "deepgreen"),
    ("hour-clock", "Hour Clock", "/apps/hour-clock", "24-hour resource container map.", "deepgreen"),
)
TRAJECTORY_FILES = (
    ("alexandria_alpha", "Alexandria.Trajectory.Alpha.header.loader.py", "AlexandriaTrajectoryAlpha"),
    ("alexandria_beta", "Alexandria.Trajectory.Beta.header.loader.py", "AlexandriaTrajectoryBeta"),
    ("alexandria_gamma", "Alexandria.Trajectory.Gamma.header.loader.py", "AlexandriaTrajectoryGamma"),
)
def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()
def ensure_layout() -> None:
    for d in (DB_DIR, AGI_DIR, COMPILE_DIR):
        d.mkdir(parents=True, exist_ok=True)
def db_connect(path: Path) -> sqlite3.Connection:
    ensure_layout()
    c = sqlite3.connect(path)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c
def active_backend() -> str:
    if not HOUR_CLOCK_DB.exists():
        compile_dbs()
    with db_connect(HOUR_CLOCK_DB) as c:
        row = c.execute("SELECT value FROM meta WHERE key='active_backend'").fetchone()
    return row["value"] if row else "deepgreen"
def active_db_path() -> Path:
    return RADIO_EFFICACY_DB if active_backend() == "radio_efficacy" else HOUR_CLOCK_DB
def set_backend(name: str) -> str:
    if name not in ("deepgreen", "radio_efficacy"):
        raise ValueError("Use deepgreen or radio_efficacy")
    with db_connect(HOUR_CLOCK_DB) as c:
        c.execute(
            "INSERT INTO meta(key,value) VALUES('active_backend',?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (name,),
        )
        c.commit()
    return name
def _load_py(module_name: str, path: Path) -> Any | None:
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location(module_name, path)
    if not spec or not spec.loader:
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
def mount_agi() -> list[dict]:
    ensure_layout()
    out: list[dict] = []
    xrs = APPLEPIRADIO / "Light.objective.humidifer.resonance.hpp"
    out.append({"id": "light_objective_xrs", "name": "Light Objective XRS", "source_path": str(xrs),
                "component_type": "xrs_db", "status": "mounted" if xrs.is_file() else "missing",
                "payload": {"registry_uri": REGISTRY_URI}})
    for cid, fname, cls in TRAJECTORY_FILES:
        p = APPLEPIRADIO / fname
        mod = _load_py(f"apr.{cid}", p)
        out.append({"id": cid, "name": cls, "source_path": str(p), "component_type": "trajectory_loader",
                    "status": "mounted" if mod and hasattr(mod, cls) else "missing", "payload": {}})
    circuit = APPLEPIRADIO / "FINALFANTASY.XrC.X12.Ratio.QUANTUM....." / "Circuit.PY"
    out.append({"id": "quantum_circuit", "name": "FinalFantasy Circuit", "source_path": str(circuit),
                "component_type": "quantum_circuit", "status": "mounted" if circuit.is_file() else "missing",
                "payload": {}})
    worm = APPLEPIRADIO / "wormholedb.Stargate.IMAGESFINDERINTEGER"
    out.append({"id": "wormhole_db", "name": "Stargate Wormhole DB", "source_path": str(worm),
                "component_type": "stargate_db", "status": "mounted" if worm.is_file() else "missing", "payload": {}})
    out.append({"id": "deepgreen_agi", "name": "deepGreen AGI", "source_path": str(ROOT.parent / "ApplePiRadio.ps"),
                "component_type": "deepgreen", "status": "mounted", "payload": {}})
    (AGI_DIR / "mounted_agi_manifest.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out
def _seed_db(conn: sqlite3.Connection, backend: str) -> None:
    for k, v in {"registry_uri": REGISTRY_URI, "active_backend": backend, "compiled_at": _utc(), "schema_version": "1"}.items():
        conn.execute("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (k, v))
    for hour in range(24):
        conn.execute(
            "INSERT INTO hour_clock_slots(hour,slot,resource_key,resource_value) VALUES(?,?,?,?) "
            "ON CONFLICT(hour,slot) DO UPDATE SET resource_key=excluded.resource_key, resource_value=excluded.resource_value",
            (hour, "primary", f"applepiradiokat.hour.{hour:02d}", json.dumps({"hour": hour, "registry": REGISTRY_URI})),
        )
    for aid, name, route, desc, be in SPAWNABLE_APPS:
        conn.execute(
            "INSERT INTO spawnable_apps(id,name,route,description,backend,enabled) VALUES(?,?,?,?,?,1) "
            "ON CONFLICT(id) DO UPDATE SET name=excluded.name, route=excluded.route, description=excluded.description, backend=excluded.backend",
            (aid, name, route, desc, be),
        )
def compile_dbs() -> dict:
    components = mount_agi()
    reports = {}
    for path, backend in ((HOUR_CLOCK_DB, "deepgreen"), (RADIO_EFFICACY_DB, "radio_efficacy")):
        with db_connect(path) as c:
            _seed_db(c, backend)
            for comp in components:
                c.execute(
                    "INSERT INTO agi_components(id,name,source_path,component_type,status,payload,mounted_at) "
                    "VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, status=excluded.status, payload=excluded.payload, mounted_at=excluded.mounted_at",
                    (comp["id"], comp["name"], comp.get("source_path"), comp["component_type"], comp["status"],
                     json.dumps(comp.get("payload", {})), _utc()),
                )
            c.execute("INSERT INTO compile_log(phase,message,created_at) VALUES(?,?,?)",
                      ("rabid", f"Compiled {path.name}", _utc()))
            c.commit()
        reports[path.name] = str(path)
    report = {
        "mounted": sum(1 for x in components if x["status"] == "mounted"),
        "total_components": len(components),
        "apps": len(SPAWNABLE_APPS),
        "active_backend": active_backend(),
        "databases": reports,
        "registry_uri": REGISTRY_URI,
    }
    (COMPILE_DIR / "rabid_compile_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report
def list_apps() -> list[dict]:
    if not active_db_path().exists():
        compile_dbs()
    with db_connect(active_db_path()) as c:
        return [dict(r) for r in c.execute(
            "SELECT id,name,route,description,backend FROM spawnable_apps WHERE enabled=1 ORDER BY name"
        )]
def _html_page(title: str, body: str) -> bytes:
    doc = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>{title}</title>
<style>body{{font-family:system-ui;max-width:52rem;margin:2rem auto;padding:0 1rem;background:#0d1f12;color:#c8f0d0}}
a{{color:#6fcf97}}.card{{border:1px solid #2d5a3d;border-radius:8px;padding:1rem;margin:.75rem 0;background:#142818}}
button{{background:#2d6a4f;color:#fff;border:0;padding:.5rem 1rem;border-radius:6px;cursor:pointer;margin:.25rem}}
.muted{{color:#7cb892;font-size:.9rem}} nav a{{margin-right:1rem}}</style></head>
<body><nav><a href="/">Hub</a><a href="/api/status">Status JSON</a></nav><h1>{title}</h1>{body}</body></html>"""
    return doc.encode("utf-8")
def _json(data: Any) -> bytes:
    return json.dumps(data, indent=2).encode("utf-8")
class HubHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: Any) -> None:
        pass
    def _send(self, code: int, body: bytes, ctype: str = "text/html; charset=utf-8") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/status":
            self._send(200, _json({
                "registry_uri": REGISTRY_URI,
                "active_backend": active_backend(),
                "active_db": active_db_path().name,
                "apps": list_apps(),
            }), "application/json")
            return
        if path == "/api/apps":
            self._send(200, _json(list_apps()), "application/json")
            return
        if path.startswith("/apps/"):
            app_id = path.removeprefix("/apps/").strip("/") or "unknown"
            apps = {a["id"]: a for a in list_apps()}
            app = apps.get(app_id, {"name": app_id, "description": "Spawned shell app."})
            body = f'<p class="muted">Backend: <strong>{active_backend()}</strong> · {active_db_path().name}</p>'
            body += f'<p>{app.get("description","")}</p><p><a href="/">← Hub</a></p>'
            if app_id == "hour-clock":
                with db_connect(active_db_path()) as c:
                    slots = [dict(r) for r in c.execute("SELECT hour,resource_key FROM hour_clock_slots ORDER BY hour")]
                body += "<pre>" + json.dumps(slots, indent=2) + "</pre>"
            self._send(200, _html_page(app.get("name", app_id), body))
            return
        cards = "".join(
            f'<motion-div class="card"><h3><a href="{a["route"]}">{a["name"]}</a></h3>'
            f'<p class="muted">{a["description"]} · {a["backend"]}</p></motion-div>'
            for a in list_apps()
        )
        toggle = (
            f'<p>Active: <strong>{active_backend()}</strong> ({active_db_path().name})</p>'
            f'<form method="post" action="/api/toggle">'
            f'<button name="backend" value="deepgreen">deepGreen</button> '
            f'<button name="backend" value="radio_efficacy">radioEfficacy</button></form>'
        )
        self._send(200, _html_page("ApplePiRadioKat Hub", toggle + cards))
    def do_POST(self) -> None:
        if urlparse(self.path).path == "/api/toggle":
            length = int(self.headers.get("Content-Length", 0))
            qs = parse_qs(self.rfile.read(length).decode("utf-8", errors="replace"))
            set_backend(qs.get("backend", ["deepgreen"])[0])
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
            return
        self._send(405, b"Method not allowed")
def serve(port: int, open_browser: bool) -> None:
    if not HOUR_CLOCK_DB.exists():
        compile_dbs()
    url = f"http://127.0.0.1:{port}/"
    print(f"ApplePiRadioKat hub → {url}")
    if open_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    ThreadingHTTPServer(("127.0.0.1", port), HubHandler).serve_forever()
def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ApplePiRadioKat db + rabid compiler + hub")
    sub = p.add_subparsers(dest="cmd")
    sub.add_parser("compile", help="Rabid-compile AGI into .db files")
    t = sub.add_parser("toggle", help="Switch active backend")
    t.add_argument("backend", choices=["deepgreen", "radio_efficacy"])
    s = sub.add_parser("serve", help="Browser hub")
    s.add_argument("--port", type=int, default=8765)
    s.add_argument("--open", action="store_true")
    sub.add_parser("status", help="Print status JSON")
    args = p.parse_args(argv)
    cmd = args.cmd or "compile"
    if cmd == "compile":
        print(json.dumps(compile_dbs(), indent=2))
    elif cmd == "toggle":
        set_backend(args.backend)
        print(f"Active: {args.backend} → {active_db_path().name}")
    elif cmd == "serve":
        try:
            serve(args.port, args.open)
        except KeyboardInterrupt:
            print("\nStopped.")
    elif cmd == "status":
        if not HOUR_CLOCK_DB.exists():
            compile_dbs()
        print(json.dumps({"active_backend": active_backend(), "active_db": str(active_db_path()), "apps": list_apps()}, indent=2))
    else:
        p.print_help()
        return 1
    return 0
if __name__ == "__main__":
    sys.exit(main())
