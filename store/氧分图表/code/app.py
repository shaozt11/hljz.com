from __future__ import annotations

import csv
import io
import json
import math
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from flask import Flask, Response, flash, jsonify, redirect, render_template, request, url_for
from PIL import Image, ImageDraw, ImageFont
import imageio.v2 as imageio
import numpy as np


BASE_DIR = Path(__file__).resolve().parent
INSTANCE_DIR = BASE_DIR / "instance"
DATA_FILE = INSTANCE_DIR / "charts.json"
WATERMARK_TEXT = "由 氧分图表 软件生成"

CHART_TYPES = {
    "table": "表格",
    "bar": "柱状图",
    "pie": "饼状图",
    "frequency": "频数统计图",
    "line": "折线图",
    "dynamic": "动态图表",
}


app = Flask(__name__)
app.secret_key = "chart-studio-secret-key"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_storage() -> None:
    INSTANCE_DIR.mkdir(exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")


def load_charts() -> list[dict]:
    ensure_storage()
    try:
        charts = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        return charts if isinstance(charts, list) else []
    except json.JSONDecodeError:
        return []


def save_charts(charts: list[dict]) -> None:
    ensure_storage()
    DATA_FILE.write_text(json.dumps(charts, ensure_ascii=False, indent=2), encoding="utf-8")


def chart_sort_key(chart: dict) -> str:
    return chart.get("updated_at") or chart.get("created_at") or ""


def normalize_chart(chart: dict) -> dict:
    chart = dict(chart)
    chart.setdefault("versions", [])
    chart.setdefault("notes", "")
    chart.setdefault("locked", False)
    return chart


def find_chart(chart_id: str) -> tuple[list[dict], dict | None, int | None]:
    charts = [normalize_chart(chart) for chart in load_charts()]
    for index, chart in enumerate(charts):
        if chart.get("id") == chart_id:
            return charts, chart, index
    return charts, None, None


def parse_table(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("表格数据不能为空")
    headers = [item.strip() for item in lines[0].split(",") if item.strip()]
    if len(headers) < 2:
        raise ValueError("表格首行至少需要 2 个列名，使用英文逗号分隔")

    rows = []
    for line in lines[1:]:
        cells = [item.strip() for item in line.split(",")]
        if len(cells) != len(headers):
            raise ValueError("表格每行列数必须和列名一致")
        rows.append(cells)

    return {"headers": headers, "rows": rows}


def parse_pairs(text: str) -> dict:
    labels = []
    values = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = [item.strip() for item in line.split(",")]
        if len(parts) != 2:
            raise ValueError("每行需要 2 列，格式为：名称,数值")
        label, value_text = parts
        try:
            value = float(value_text)
        except ValueError as exc:
            raise ValueError(f"数值无效：{value_text}") from exc
        labels.append(label)
        values.append(value)

    if not labels:
        raise ValueError("数据不能为空")

    return {"labels": labels, "values": values}


def parse_dynamic(text: str) -> dict:
    table = parse_table(text)
    headers = table["headers"]
    if len(headers) < 3:
        raise ValueError("动态图表至少需要 3 列：时间,项目1,项目2")

    labels = headers[1:]
    frames = []
    for row in table["rows"]:
        values = []
        for value_text in row[1:]:
            try:
                values.append(float(value_text))
            except ValueError as exc:
                raise ValueError(f"数值无效：{value_text}") from exc
        frames.append({"time": row[0], "values": values})

    if not frames:
        raise ValueError("动态图表至少需要 1 个时间帧")

    return {"labels": labels, "frames": frames}


def parse_interval_ms(value: str | int | float | None) -> int:
    try:
        interval = int(float(value or 1000))
    except (TypeError, ValueError):
        interval = 1000
    return min(10000, max(200, interval))


def get_ui_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def draw_dynamic_frame(
    chart: dict,
    frame: dict,
    size: tuple[int, int] = (1280, 720),
    display_time: str | None = None,
) -> Image.Image:
    width, height = size
    image = Image.new("RGB", size, "#ffffff")
    draw = ImageDraw.Draw(image)
    title_font = get_ui_font(34)
    label_font = get_ui_font(22)
    small_font = get_ui_font(18)
    watermark_font = get_ui_font(18)

    labels = chart.get("labels", [])
    values = [float(value) for value in frame.get("values", [])]
    max_value = max(values) if values else 1
    max_value = max(max_value, 1)

    draw.text((60, 42), chart.get("title", ""), fill="#0f172a", font=title_font)
    draw.text((60, 92), f"时间：{display_time if display_time is not None else frame.get('time', '')}", fill="#475569", font=label_font)

    left_label = 80
    left_bar = 220
    right = width - 90
    top = 165
    row_gap = 20
    row_count = max(1, len(labels))
    bar_height = min(48, max(24, int((height - 260 - row_gap * (row_count - 1)) / row_count)))
    color = "#38bdf8"
    border = "#0ea5e9"

    for index, label in enumerate(labels):
        y = top + index * (bar_height + row_gap)
        value = values[index] if index < len(values) else 0
        bar_width = int((right - left_bar) * (value / max_value))
        draw.text((left_label, y + 8), str(label), fill="#334155", font=label_font)
        draw.rounded_rectangle((left_bar, y, right, y + bar_height), radius=6, fill="#f1f5f9", outline="#e2e8f0")
        draw.rounded_rectangle((left_bar, y, left_bar + bar_width, y + bar_height), radius=6, fill=color, outline=border)
        draw.text((left_bar + bar_width + 12, y + 8), f"{value:g}", fill="#0f172a", font=small_font)

    text_box = draw.textbbox((0, 0), WATERMARK_TEXT, font=watermark_font)
    text_width = text_box[2] - text_box[0]
    draw.text((width - 48 - text_width, height - 42), WATERMARK_TEXT, fill="#64748b", font=watermark_font)
    return image


def ease_in_out(progress: float) -> float:
    progress = min(1.0, max(0.0, progress))
    return progress * progress * (3 - 2 * progress)


def interpolate_values(start: list[float], end: list[float], progress: float) -> list[float]:
    eased = ease_in_out(progress)
    length = max(len(start), len(end))
    values = []
    for index in range(length):
        start_value = start[index] if index < len(start) else 0
        end_value = end[index] if index < len(end) else 0
        values.append(start_value + (end_value - start_value) * eased)
    return values


def build_dynamic_mp4(chart: dict) -> bytes:
    chart = serialize_chart(chart)
    if chart.get("type") != "dynamic":
        raise ValueError("只有动态图表可以合成为视频")

    frames = chart.get("frames", [])
    if not frames:
        raise ValueError("动态图表没有可导出的时间帧")

    fps = 30
    interval_ms = parse_interval_ms(chart.get("interval_ms"))
    transition_frames = max(2, round(fps * interval_ms / 1000))

    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp:
        temp_path = Path(temp.name)
    try:
        with imageio.get_writer(
            temp_path,
            fps=fps,
            codec="libx264",
            pixelformat="yuv420p",
            macro_block_size=16,
            ffmpeg_params=["-movflags", "+faststart"],
        ) as writer:
            for index, frame in enumerate(frames):
                next_frame = frames[index + 1] if index + 1 < len(frames) else frame
                for step in range(transition_frames):
                    progress = step / transition_frames
                    values = interpolate_values(frame.get("values", []), next_frame.get("values", []), progress)
                    display_frame = {"time": frame.get("time", ""), "values": values}
                    image = draw_dynamic_frame(chart, display_frame, display_time=frame.get("time", ""))
                    writer.append_data(np.asarray(image))

            final_frame = frames[-1]
            image = draw_dynamic_frame(chart, final_frame, display_time=final_frame.get("time", ""))
            for _ in range(max(6, fps // 2)):
                writer.append_data(np.asarray(image))
        return temp_path.read_bytes()
    finally:
        temp_path.unlink(missing_ok=True)


def build_frequency(values: list[float], bins: int = 8) -> dict:
    if not values:
        raise ValueError("频数统计数据不能为空")

    minimum = min(values)
    maximum = max(values)
    if math.isclose(minimum, maximum):
        return {"labels": [f"{minimum:g}"], "values": [len(values)]}

    bins = max(2, int(bins))
    step = (maximum - minimum) / bins
    counts = [0 for _ in range(bins)]
    for value in values:
        index = int((value - minimum) / step) if step else 0
        if index >= bins:
            index = bins - 1
        counts[index] += 1

    labels = []
    for index in range(bins):
        start = minimum + step * index
        end = start + step
        labels.append(f"{start:.2f} - {end:.2f}")

    return {"labels": labels, "values": counts}


def chart_from_payload(chart_type: str, form: dict) -> dict:
    title = form.get("title", "").strip()
    if not title:
        raise ValueError("请输入标题")

    notes = form.get("notes", "").strip()

    if chart_type == "table":
        table = parse_table(form.get("content", ""))
        return {"title": title, "type": chart_type, "table": table, "notes": notes}

    if chart_type in {"bar", "pie", "line"}:
        pairs = parse_pairs(form.get("content", ""))
        return {"title": title, "type": chart_type, **pairs, "notes": notes}

    if chart_type == "dynamic":
        dynamic = parse_dynamic(form.get("content", ""))
        interval_ms = parse_interval_ms(form.get("interval_ms"))
        return {"title": title, "type": chart_type, **dynamic, "interval_ms": interval_ms, "notes": notes}

    if chart_type == "frequency":
        values = []
        for token in form.get("content", "").replace("\n", ",").split(","):
            token = token.strip()
            if not token:
                continue
            try:
                values.append(float(token))
            except ValueError as exc:
                raise ValueError(f"数值无效：{token}") from exc
        bins_text = form.get("bins", "8").strip() or "8"
        try:
            bins = int(bins_text)
        except ValueError as exc:
            raise ValueError("分组数必须是整数") from exc
        frequency = build_frequency(values, bins=bins)
        return {"title": title, "type": chart_type, "source_values": values, "frequency": frequency, "bins": bins, "notes": notes}

    raise ValueError("不支持的图表类型")


def serialize_chart(chart: dict) -> dict:
    chart = normalize_chart(chart)
    if chart.get("type") == "frequency" and "frequency" not in chart:
        chart["frequency"] = build_frequency(chart.get("source_values", []), bins=chart.get("bins", 8))
    if chart.get("type") == "dynamic":
        chart["interval_ms"] = parse_interval_ms(chart.get("interval_ms"))
    return chart


def build_visual_dataset(chart: dict) -> tuple[list[str], list[float]]:
    chart = serialize_chart(chart)
    if chart["type"] == "frequency":
        return chart["frequency"]["labels"], chart["frequency"]["values"]
    if chart["type"] == "table":
        return [], []
    if chart["type"] == "dynamic":
        frames = chart.get("frames", [])
        return chart.get("labels", []), frames[0]["values"] if frames else []
    return chart.get("labels", []), chart.get("values", [])


def chart_to_content(chart: dict) -> str:
    chart = serialize_chart(chart)
    chart_type = chart.get("type")
    if chart_type == "table":
        return "\n".join(
            [",".join(chart["table"]["headers"])]
            + [",".join(row) for row in chart["table"]["rows"]]
        )
    if chart_type == "frequency":
        return "\n".join(str(v) for v in chart.get("source_values", []))
    if chart_type == "dynamic":
        return "\n".join(
            [",".join(["time"] + chart.get("labels", []))]
            + [
                ",".join([str(frame.get("time", ""))] + [str(value) for value in frame.get("values", [])])
                for frame in chart.get("frames", [])
            ]
        )
    return "\n".join(f"{label},{value}" for label, value in zip(chart.get("labels", []), chart.get("values", [])))


def snapshot_chart(chart: dict) -> dict:
    chart = serialize_chart(chart)
    chart_type = chart.get("type")
    snapshot = {
        "title": chart.get("title", ""),
        "type": chart_type,
        "notes": chart.get("notes", ""),
        "updated_at": now_iso(),
    }
    if chart_type == "table":
        snapshot["table"] = chart["table"]
    elif chart_type == "frequency":
        snapshot["source_values"] = chart.get("source_values", [])
        snapshot["frequency"] = chart["frequency"]
        snapshot["bins"] = chart.get("bins", 8)
    elif chart_type == "dynamic":
        snapshot["labels"] = chart.get("labels", [])
        snapshot["frames"] = chart.get("frames", [])
        snapshot["interval_ms"] = parse_interval_ms(chart.get("interval_ms"))
    else:
        snapshot["labels"], snapshot["values"] = build_visual_dataset(chart)
    return snapshot


def update_chart_from_form(chart: dict, form: dict) -> dict:
    chart_type = form.get("chart_type", chart.get("type", "bar"))
    payload = chart_from_payload(chart_type, form)
    old_versions = list(chart.get("versions", []))
    old_versions.append(snapshot_chart(chart))
    if len(old_versions) > 20:
        old_versions = old_versions[-20:]

    chart.update(payload)
    chart["versions"] = old_versions
    chart["updated_at"] = now_iso()
    return chart


@app.route("/")
def index():
    charts = sorted([serialize_chart(chart) for chart in load_charts()], key=chart_sort_key, reverse=True)
    return render_template("index.html", charts=charts, chart_types=CHART_TYPES)


@app.route("/new", methods=["GET", "POST"])
def new_chart():
    if request.method == "POST":
        chart_type = request.form.get("chart_type", "bar")
        try:
            payload = chart_from_payload(chart_type, request.form)
        except ValueError as exc:
            flash(str(exc), "error")
            return render_template("chart_form.html", chart_types=CHART_TYPES, form=request.form, default_type=chart_type)

        charts = load_charts()
        chart_id = uuid.uuid4().hex
        payload.update({"id": chart_id, "created_at": now_iso(), "updated_at": now_iso(), "versions": []})
        charts.append(payload)
        save_charts(charts)
        flash("图表已创建", "success")
        return redirect(url_for("chart_edit", chart_id=chart_id))

    default_form = {"title": "", "content": "A,10\nB,20\nC,14", "bins": "8", "notes": ""}
    return render_template("chart_form.html", chart_types=CHART_TYPES, form=default_form, default_type="bar")


@app.route("/chart/<chart_id>")
def chart_detail(chart_id: str):
    return redirect(url_for("chart_edit", chart_id=chart_id))


@app.route("/chart/<chart_id>/edit")
def chart_edit(chart_id: str):
    _, chart, _ = find_chart(chart_id)
    if chart is None:
        flash("图表不存在", "error")
        return redirect(url_for("index"))
    chart = serialize_chart(chart)
    labels, values = build_visual_dataset(chart)
    return render_template("chart_edit.html", chart=chart, chart_types=CHART_TYPES, chart_labels=labels, chart_values=values)


@app.route("/chart/<chart_id>/detail")
def chart_detail_page(chart_id: str):
    return redirect(url_for("chart_edit", chart_id=chart_id))


@app.route("/api/chart/<chart_id>", methods=["GET"])
def api_get_chart(chart_id: str):
    _, chart, _ = find_chart(chart_id)
    if chart is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify(serialize_chart(chart))


@app.route("/api/chart/<chart_id>", methods=["PUT"])
def api_update_chart(chart_id: str):
    charts, chart, index = find_chart(chart_id)
    if chart is None or index is None:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(force=True, silent=True) or {}
    current = serialize_chart(chart)
    form_like = {
        "title": payload.get("title", current.get("title", "")),
        "chart_type": payload.get("type", current.get("type", "bar")),
        "content": payload.get("content", ""),
        "bins": str(payload.get("bins", current.get("bins", 8))),
        "interval_ms": payload.get("interval_ms", current.get("interval_ms", 1000)),
        "notes": payload.get("notes", current.get("notes", "")),
    }

    try:
        if payload.get("content") is None:
            form_like["content"] = chart_to_content(current)

        updated = update_chart_from_form(current, form_like)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    charts[index] = updated
    save_charts(charts)
    return jsonify(serialize_chart(updated))


@app.route("/api/chart/<chart_id>/revert", methods=["POST"])
def api_revert_chart(chart_id: str):
    charts, chart, index = find_chart(chart_id)
    if chart is None or index is None:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(force=True, silent=True) or {}
    version_index = int(payload.get("version_index", -1))
    versions = chart.get("versions", [])
    if not versions:
        return jsonify({"error": "no_versions"}), 400
    if version_index < 0:
        version_index = len(versions) - 1
    if version_index >= len(versions):
        return jsonify({"error": "bad_version"}), 400

    restored = dict(versions[version_index])
    restored["id"] = chart["id"]
    restored["created_at"] = chart.get("created_at")
    restored["versions"] = versions[:version_index]
    restored["updated_at"] = now_iso()
    charts[index] = restored
    save_charts(charts)
    return jsonify(serialize_chart(restored))


@app.route("/api/chart/<chart_id>/export")
def api_export_chart(chart_id: str):
    _, chart, _ = find_chart(chart_id)
    if chart is None:
        return jsonify({"error": "not_found"}), 404
    return jsonify(serialize_chart(chart))


@app.route("/api/chart/<chart_id>/import", methods=["POST"])
def api_import_chart(chart_id: str):
    charts, chart, index = find_chart(chart_id)
    if chart is None or index is None:
        return jsonify({"error": "not_found"}), 404

    payload = request.get_json(force=True, silent=True) or {}
    imported = payload.get("chart")
    if not isinstance(imported, dict):
        return jsonify({"error": "invalid_payload"}), 400

    imported = serialize_chart(imported)
    imported["id"] = chart["id"]
    imported["created_at"] = chart.get("created_at")
    imported["versions"] = chart.get("versions", []) + [snapshot_chart(chart)]
    imported["updated_at"] = now_iso()
    charts[index] = imported
    save_charts(charts)
    return jsonify(serialize_chart(imported))


@app.route("/api/chart/<chart_id>/export.csv")
def api_export_csv(chart_id: str):
    _, chart, _ = find_chart(chart_id)
    if chart is None:
        return jsonify({"error": "not_found"}), 404
    chart = serialize_chart(chart)

    output = io.StringIO()
    writer = csv.writer(output)
    if chart["type"] == "table":
        writer.writerow(chart["table"]["headers"])
        writer.writerows(chart["table"]["rows"])
    elif chart["type"] == "frequency":
        writer.writerow(["value"])
        for value in chart.get("source_values", []):
            writer.writerow([value])
    elif chart["type"] == "dynamic":
        writer.writerow(["time"] + chart.get("labels", []))
        for frame in chart.get("frames", []):
            writer.writerow([frame.get("time", "")] + frame.get("values", []))
    else:
        writer.writerow(["label", "value"])
        for label, value in zip(chart.get("labels", []), chart.get("values", [])):
            writer.writerow([label, value])

    return Response(output.getvalue(), mimetype="text/csv; charset=utf-8", headers={"Content-Disposition": f"attachment; filename={chart['id']}.csv"})


@app.route("/api/chart/<chart_id>/export.mp4")
def api_export_mp4(chart_id: str):
    _, chart, _ = find_chart(chart_id)
    if chart is None:
        return jsonify({"error": "not_found"}), 404
    try:
        mp4_bytes = build_dynamic_mp4(chart)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    filename = quote(f"{chart.get('title') or chart_id}.mp4")
    return Response(
        mp4_bytes,
        mimetype="video/mp4",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=6305)
