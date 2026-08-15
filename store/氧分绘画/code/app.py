from __future__ import annotations

import base64
import json
import re
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_from_directory


BASE_DIR = Path(__file__).resolve().parent
RESULT_DIR = BASE_DIR / "result"
RESULT_DIR.mkdir(parents=True, exist_ok=True)

app = Flask(__name__)


def _slugify(name: str) -> str:
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", name)
    return name.strip("-") or "drawing"


def _result_files():
    files = []
    for path in sorted(RESULT_DIR.glob("*.png"), reverse=True):
        stat = path.stat()
        files.append(
            {
                "name": path.name,
                "size": stat.st_size,
                "mtime": stat.st_mtime,
                "url": f"/result/{path.name}",
            }
        )
    return files


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/files")
def api_files():
    return jsonify({"files": _result_files()})


@app.post("/save")
def save():
    payload = request.get_json(silent=True) or {}
    data_url = payload.get("image")
    title = payload.get("title") or "drawing"

    if not data_url or not isinstance(data_url, str):
        return jsonify({"ok": False, "error": "missing image"}), 400

    if "," not in data_url:
        return jsonify({"ok": False, "error": "invalid image data"}), 400

    _, encoded = data_url.split(",", 1)
    try:
        image_bytes = base64.b64decode(encoded)
    except Exception:
        return jsonify({"ok": False, "error": "cannot decode image"}), 400

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"{timestamp}-{_slugify(title)}.png"
    output_path = RESULT_DIR / filename
    output_path.write_bytes(image_bytes)

    meta_path = output_path.with_suffix(".json")
    meta_path.write_text(
        json.dumps(
            {
                "title": title,
                "filename": filename,
                "saved_at": timestamp,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return jsonify({"ok": True, "filename": filename, "url": f"/result/{filename}"})


@app.get("/result/<path:filename>")
def result_file(filename: str):
    return send_from_directory(RESULT_DIR, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6303, debug=True)
