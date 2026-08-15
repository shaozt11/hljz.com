from __future__ import annotations

from flask import Flask, jsonify, render_template_string

app = Flask(__name__)

HTML = r"""
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>SDK Demo</title>
    <style>
      :root {
        color-scheme: dark;
        --bg: #08111f;
        --panel: rgba(10, 17, 33, 0.78);
        --line: rgba(255, 255, 255, 0.12);
        --text: #f8fafc;
        --muted: #93a4c3;
        --accent: #ff8c00;
      }
      * { box-sizing: border-box; }
      body {
        margin: 0;
        font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
        color: var(--text);
        background:
          radial-gradient(circle at top left, rgba(255, 140, 0, 0.18), transparent 34%),
          radial-gradient(circle at right bottom, rgba(14, 165, 233, 0.18), transparent 28%),
          var(--bg);
      }
      .wrap {
        min-height: 100vh;
        padding: 24px;
        display: grid;
        gap: 16px;
        grid-template-columns: 360px minmax(0, 1fr);
      }
      .card {
        padding: 18px;
        border: 1px solid var(--line);
        border-radius: 18px;
        background: var(--panel);
        backdrop-filter: blur(18px);
        box-shadow: 0 24px 70px rgba(0, 0, 0, 0.35);
      }
      h1, h2, p { margin: 0; }
      h1 { font-size: 24px; }
      h2 { font-size: 16px; margin-bottom: 12px; }
      .muted { color: var(--muted); font-size: 13px; line-height: 1.5; }
      .actions { display: grid; gap: 10px; margin-top: 16px; }
      button, input, textarea { font: inherit; }
      button {
        min-height: 40px;
        border: 1px solid var(--line);
        border-radius: 12px;
        color: var(--text);
        background: rgba(255, 255, 255, 0.06);
        text-align: left;
        padding: 0 14px;
      }
      button.primary { background: rgba(255, 140, 0, 0.18); border-color: rgba(255, 140, 0, 0.42); }
      input, textarea {
        width: 100%;
        border: 1px solid var(--line);
        border-radius: 12px;
        color: var(--text);
        background: rgba(255, 255, 255, 0.05);
        padding: 10px 12px;
      }
      textarea { min-height: 180px; resize: vertical; }
      .log { display: grid; gap: 10px; }
      .log-list {
        min-height: 420px;
        display: grid;
        gap: 8px;
        align-content: start;
      }
      .entry {
        padding: 10px 12px;
        border: 1px solid var(--line);
        border-radius: 12px;
        background: rgba(255, 255, 255, 0.04);
        font-size: 13px;
        line-height: 1.5;
        white-space: pre-wrap;
      }
      .grid { display: grid; gap: 12px; }
    </style>
  </head>
  <body>
    <div class="wrap">
      <section class="card">
        <h1>SDK Demo</h1>
        <p class="muted">演示 SDK v2 的结果文件、原生弹窗、断点协同。</p>
        <div class="actions">
          <button class="primary" id="btnAlert">打开原生 alert</button>
          <button id="btnConfirm">打开原生 confirm</button>
          <button id="btnPrompt">打开原生 prompt</button>
          <button id="btnWrite">写入 result/paint-state.json</button>
          <button id="btnRead">读取 result/paint-state.json</button>
          <button id="btnList">扫描 result 文件夹</button>
          <button id="btnJoin">加入协同房间</button>
          <button id="btnSend">发送一条画笔事件</button>
          <button id="btnSnapshot">请求协同快照</button>
        </div>
        <div class="grid" style="margin-top: 16px;">
          <label class="muted">结果数据</label>
          <textarea id="payload">{ "strokes": [] }</textarea>
          <label class="muted">状态</label>
          <input id="status" value="未连接" readonly />
        </div>
      </section>
      <section class="card log">
        <h2>日志</h2>
        <div class="log-list" id="log"></div>
      </section>
    </div>
    <script>
      const bridge = document.createElement("script")
      bridge.src = `${location.protocol}//${location.hostname}:8000/sdk/roxet-bridge.js`
      bridge.onload = () => {
        const sdk = window.Roxet && window.Roxet.registerShellBridge ? window.Roxet.registerShellBridge() : null
        const appId = "SDKDemo"
        const log = (message) => {
          const node = document.createElement("div")
          node.className = "entry"
          node.textContent = typeof message === "string" ? message : JSON.stringify(message, null, 2)
          document.getElementById("log").prepend(node)
        }
        const setStatus = (value) => { document.getElementById("status").value = value }
        const ensureSdk = () => {
          if (!sdk) throw new Error("bridge not ready")
          return sdk
        }
        let channel = null
        document.getElementById("btnAlert").onclick = async () => {
          await ensureSdk().ui.alert({ title: "SDK Demo", message: "这是系统原生 alert 弹窗。" })
          log("alert 已确认")
        }
        document.getElementById("btnConfirm").onclick = async () => {
          const ok = await ensureSdk().ui.confirm({ title: "SDK Demo", message: "是否继续当前示例？" })
          log("confirm => " + ok)
        }
        document.getElementById("btnPrompt").onclick = async () => {
          const value = await ensureSdk().ui.prompt({ title: "SDK Demo", message: "请输入一个名字", defaultValue: "Roxet" })
          log("prompt => " + value)
        }
        document.getElementById("btnWrite").onclick = async () => {
          const data = document.getElementById("payload").value
          const result = await ensureSdk().storage.write(appId, "paint-state.json", data)
          log({ write: result })
        }
        document.getElementById("btnRead").onclick = async () => {
          const data = await ensureSdk().storage.read(appId, "paint-state.json")
          document.getElementById("payload").value = data
          log({ read: data })
        }
        document.getElementById("btnList").onclick = async () => {
          const items = await ensureSdk().storage.list(appId)
          log(items)
        }
        document.getElementById("btnJoin").onclick = async () => {
          if (channel) channel.leave()
          channel = ensureSdk().sync.join({ appId })
          channel.onMessage((event) => {
            log({ sync: event })
            if (event.type === "snapshot" && event.payload) {
              document.getElementById("payload").value = JSON.stringify(event.payload, null, 2)
            }
          })
          channel.requestSnapshot()
          setStatus("已加入协同房间")
        }
        document.getElementById("btnSend").onclick = async () => {
          const value = JSON.parse(document.getElementById("payload").value || "{}")
          await ensureSdk().storage.write(appId, "paint-state.json", JSON.stringify(value, null, 2))
          if (!channel) {
            channel = ensureSdk().sync.join({ appId })
            channel.onMessage((event) => {
              log({ sync: event })
            })
          }
          channel.send({ type: "op", payload: { kind: "stroke", point: { x: Date.now() % 400, y: Date.now() % 240 } } })
          log("sent op")
        }
        document.getElementById("btnSnapshot").onclick = async () => {
          if (!channel) {
            channel = ensureSdk().sync.join({ appId })
            channel.onMessage((event) => log({ sync: event }))
          }
          channel.requestSnapshot()
          setStatus("请求了快照")
        }
        log("SDK Demo loaded")
      }
      document.head.appendChild(bridge)
    </script>
  </body>
</html>
"""


@app.get("/")
def index():
  return render_template_string(HTML)


@app.get("/health")
def health():
  return jsonify({"ok": True})


if __name__ == "__main__":
  app.run(host="0.0.0.0", port=5010, debug=True)
