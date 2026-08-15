const canvas = document.getElementById("canvas");
const ctx = canvas.getContext("2d");
const color = document.getElementById("color");
const size = document.getElementById("size");
const penBtn = document.getElementById("penBtn");
const eraserBtn = document.getElementById("eraserBtn");
const undoBtn = document.getElementById("undoBtn");
const clearBtn = document.getElementById("clearBtn");
const saveBtn = document.getElementById("saveBtn");
const syncBtn = document.getElementById("syncBtn");
const syncStatus = document.getElementById("syncStatus");
const refreshBtn = document.getElementById("refreshBtn");
const fileList = document.getElementById("fileList");

let drawing = false;
let erasing = false;
let last = null;
let history = [];
let sdk = null;
let syncSession = null;
let syncEnabled = false;
let applyingRemote = false;
let canvasDirty = false;
const appId = "氧分绘画";
const clientId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;

function cssSize() {
  const rect = canvas.getBoundingClientRect();
  return { width: rect.width, height: rect.height };
}

function clearSurface() {
  const { width, height } = cssSize();
  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, width, height);
}

function resizeCanvas() {
  const ratio = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const snapshot = canvas.width ? canvas.toDataURL() : null;

  canvas.width = Math.max(1, Math.floor(rect.width * ratio));
  canvas.height = Math.max(1, Math.floor(rect.height * ratio));
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  clearSurface();
  if (snapshot) restore(snapshot);
}

function restore(dataUrl) {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => {
      const { width, height } = cssSize();
      clearSurface();
      ctx.drawImage(img, 0, 0, width, height);
      resolve();
    };
    img.src = dataUrl;
  });
}

function normalizedPoint(point) {
  const { width, height } = cssSize();
  return {
    x: width ? point.x / width : 0,
    y: height ? point.y / height : 0,
  };
}

function denormalizedPoint(point) {
  const { width, height } = cssSize();
  return {
    x: point.x * width,
    y: point.y * height,
  };
}

function setSyncStatus(text, active = false) {
  syncStatus.textContent = text;
  syncStatus.classList.toggle("active", active);
  syncBtn.classList.toggle("active", active);
}

function loadRoxetBridge() {
  if (window.Roxet?.registerShellBridge) {
    sdk = window.Roxet.registerShellBridge();
    return Promise.resolve(sdk);
  }

  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `${location.protocol}//${location.hostname}:8000/sdk/roxet-bridge.js`;
    script.onload = () => {
      sdk = window.Roxet?.registerShellBridge?.() || null;
      if (sdk) resolve(sdk);
      else reject(new Error("SDK bridge not ready"));
    };
    script.onerror = () => reject(new Error("SDK bridge load failed"));
    document.head.appendChild(script);
  });
}

function currentSnapshot(reason = "snapshot") {
  return {
    reason,
    image: canvas.toDataURL("image/png"),
    width: cssSize().width,
    height: cssSize().height,
    updatedAt: Date.now(),
    clientId,
  };
}

function sendSnapshot(reason) {
  if (!syncEnabled || !syncSession || applyingRemote) return;
  syncSession.send({ type: "snapshot", payload: currentSnapshot(reason) });
}

function sendDrawOp(from, to) {
  if (!syncEnabled || !syncSession || applyingRemote) return;
  syncSession.send({
    type: "op",
    payload: {
      kind: "stroke",
      from: normalizedPoint(from),
      to: normalizedPoint(to),
      color: erasing ? "#ffffff" : color.value,
      size: Number(size.value),
      clientId,
    },
  });
}

function drawSegment(from, to, strokeColor, strokeSize) {
  ctx.strokeStyle = strokeColor;
  ctx.lineWidth = strokeSize;
  ctx.beginPath();
  ctx.moveTo(from.x, from.y);
  ctx.lineTo(to.x, to.y);
  ctx.stroke();
}

async function applyRemoteSnapshot(payload) {
  if (!payload || payload.clientId === clientId || !payload.image) return;
  applyingRemote = true;
  try {
    pushHistory();
    await restore(String(payload.image));
  } finally {
    applyingRemote = false;
  }
}

function applyRemoteOp(payload) {
  if (!payload || payload.clientId === clientId) return;
  if (payload.kind === "clear") {
    applyingRemote = true;
    pushHistory();
    clearSurface();
    history = [];
    applyingRemote = false;
    return;
  }
  if (payload.kind !== "stroke" || !payload.from || !payload.to) return;
  const from = denormalizedPoint(payload.from);
  const to = denormalizedPoint(payload.to);
  applyingRemote = true;
  drawSegment(from, to, String(payload.color || "#1f2937"), Number(payload.size || 8));
  applyingRemote = false;
}

async function enableSync() {
  if (syncEnabled) return;
  try {
    const bridge = await loadRoxetBridge();
    syncSession = bridge.sync.join({ appId });
    syncSession.onMessage((event) => {
      if (event.type === "snapshot") {
        void applyRemoteSnapshot(event.payload);
      } else if (event.type === "op") {
        applyRemoteOp(event.payload);
      }
    });
    syncEnabled = true;
    setSyncStatus("协同已开启", true);
    bridge.notify?.("断点协同已开启", "success");
    syncSession.requestSnapshot();
    if (canvasDirty) {
      window.setTimeout(() => sendSnapshot("join"), 300);
    }
  } catch (error) {
    syncEnabled = false;
    setSyncStatus("协同不可用");
    console.error(error);
  }
}

function disableSync() {
  syncSession?.leave?.();
  syncSession = null;
  syncEnabled = false;
  setSyncStatus("未连接");
}

function pushHistory() {
  history.push(canvas.toDataURL("image/png"));
  if (history.length > 20) history.shift();
}

function pointerPos(evt) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: evt.clientX - rect.left,
    y: evt.clientY - rect.top,
  };
}

function draw(evt) {
  if (!drawing) return;
  const pos = pointerPos(evt);
  const from = last;
  drawSegment(from, pos, erasing ? "#ffffff" : color.value, Number(size.value));
  canvasDirty = true;
  sendDrawOp(from, pos);
  last = pos;
}

canvas.addEventListener("pointerdown", (evt) => {
  drawing = true;
  canvas.setPointerCapture(evt.pointerId);
  last = pointerPos(evt);
  pushHistory();
});

canvas.addEventListener("pointermove", draw);
canvas.addEventListener("pointerup", () => {
  drawing = false;
  last = null;
  sendSnapshot("stroke");
});
canvas.addEventListener("pointercancel", () => {
  drawing = false;
  last = null;
  sendSnapshot("cancel");
});

penBtn.onclick = () => {
  erasing = false;
  penBtn.classList.add("active");
  eraserBtn.classList.remove("active");
};

eraserBtn.onclick = () => {
  erasing = true;
  eraserBtn.classList.add("active");
  penBtn.classList.remove("active");
};

undoBtn.onclick = async () => {
  if (!history.length) return;
  const snapshot = history.pop();
  await restore(snapshot);
  canvasDirty = true;
  sendSnapshot("undo");
};

clearBtn.onclick = () => {
  pushHistory();
  clearSurface();
  history = [];
  canvasDirty = true;
  if (syncEnabled && syncSession && !applyingRemote) {
    syncSession.send({ type: "op", payload: { kind: "clear", clientId } });
    sendSnapshot("clear");
  }
};

saveBtn.onclick = async () => {
  const res = await fetch("/save", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image: canvas.toDataURL("image/png"), title: "drawing" }),
  });
  const data = await res.json();
  if (data.ok) {
    const shell = sdk || window.Roxet?.registerShellBridge?.();
    shell?.notify?.("Saved", "success");
    sendSnapshot("save");
    loadFiles();
  }
};

refreshBtn.onclick = loadFiles;
syncBtn.onclick = () => {
  if (syncEnabled) {
    disableSync();
  } else {
    void enableSync();
  }
};

function fileCard(file) {
  const wrap = document.createElement("div");
  wrap.className = "file-card";
  const img = document.createElement("img");
  img.src = file.url;
  img.alt = file.name;
  const meta = document.createElement("div");
  meta.className = "file-meta";
  meta.innerHTML = `<span>${file.name}</span><span>${Math.round(file.size / 1024)} KB</span>`;
  wrap.appendChild(img);
  wrap.appendChild(meta);
  return wrap;
}

async function loadFiles() {
  const res = await fetch("/api/files");
  const data = await res.json();
  fileList.innerHTML = "";
  if (!data.files.length) {
    fileList.innerHTML = '<div class="file-meta">No saved files yet</div>';
    return;
  }
  data.files.slice(0, 6).forEach((file) => fileList.appendChild(fileCard(file)));
}

window.addEventListener("resize", resizeCanvas);
window.addEventListener("beforeunload", disableSync);
resizeCanvas();
loadFiles();
