#!/usr/bin/env python3
"""Minimal DS-SLAM visualizer backend with shared config support."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from config_loader import load_config  # noqa: E402


def gui_safe_config(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "project": {
            "name": config["project"].get("name", "DS-SLAM"),
            "profile": config["project"].get("profile", "dev"),
        },
        "visualization": {
            "host": config["visualization"]["host"],
            "port": config["visualization"]["port"],
            "ws_path": config["visualization"]["ws_path"],
        },
    }


def create_app(profile: str = "dev") -> FastAPI:
    config = load_config(profile)
    app = FastAPI(title="DS-SLAM Visualizer")
    app.state.config = config
    app.state.clients = []

    static_dir = Path(config["_resolved"]["visualization"]["static_dir"]["win"])
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    async def index():
        index_path = static_dir / "index.html"
        if index_path.exists():
            return FileResponse(index_path)
        return JSONResponse(
            {
                "service": "DS-SLAM Visualizer",
                "status": "ok",
                "config": gui_safe_config(config),
            }
        )

    @app.get("/api/status")
    async def status():
        return {
            "clients": len(app.state.clients),
            "profile": config["project"].get("profile", profile),
            "host": config["visualization"]["host"],
            "port": config["visualization"]["port"],
            "ws_path": config["visualization"]["ws_path"],
        }

    @app.get("/api/config")
    async def api_config():
        return gui_safe_config(config)

    @app.post("/api/frame")
    async def inject_frame(frame: dict[str, Any]):
        message = json.dumps(frame)
        dead = []
        for client in app.state.clients:
            try:
                await client.send_text(message)
            except Exception:
                dead.append(client)
        for client in dead:
            app.state.clients.remove(client)
        return {"status": "ok", "clients": len(app.state.clients)}

    @app.websocket(config["visualization"]["ws_path"])
    async def ws_slam(ws: WebSocket):
        await ws.accept()
        app.state.clients.append(ws)
        try:
            while True:
                data = await ws.receive_text()
                if data:
                    payload = json.loads(data)
                    if payload.get("type") == "ping":
                        await ws.send_text(json.dumps({"type": "pong"}))
        finally:
            if ws in app.state.clients:
                app.state.clients.remove(ws)

    return app


app = create_app()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="dev")
    args = parser.parse_args()
    config = load_config(args.profile)

    import uvicorn

    uvicorn.run(
        create_app(args.profile),
        host=config["visualization"]["host"],
        port=int(config["visualization"]["port"]),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
