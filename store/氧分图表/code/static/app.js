function parseJSON(value, fallback) {
  try {
    return value ? JSON.parse(value) : fallback;
  } catch {
    return fallback;
  }
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function downloadText(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function normalizeInterval(value) {
  const interval = Number(value || 1000);
  return Math.min(10000, Math.max(200, Number.isFinite(interval) ? interval : 1000));
}

function normalizeChart(chart) {
  const copy = clone(chart);
  copy.notes = copy.notes || "";
  copy.versions = copy.versions || [];
  if (copy.type === "dynamic") {
    copy.labels = copy.labels || ["A", "B", "C"];
    copy.frames = copy.frames?.length ? copy.frames : [
      { time: "0", values: [10, 20, 14] },
      { time: "1", values: [16, 12, 22] },
      { time: "2", values: [25, 18, 11] },
    ];
    copy.interval_ms = normalizeInterval(copy.interval_ms);
  }
  return copy;
}

function chartToDataText(chart) {
  if (chart.type === "table") {
    const headers = chart.table?.headers || [];
    const rows = chart.table?.rows || [];
    return [headers.join(",")].concat(rows.map((row) => row.join(","))).join("\n");
  }
  if (chart.type === "frequency") return (chart.source_values || []).join("\n");
  if (chart.type === "dynamic") {
    const labels = chart.labels || [];
    const frames = chart.frames || [];
    return [["time", ...labels].join(",")]
      .concat(frames.map((frame) => [frame.time, ...(frame.values || [])].join(",")))
      .join("\n");
  }
  const labels = chart.labels || [];
  const values = chart.values || [];
  return labels.map((label, index) => `${label},${values[index] ?? 0}`).join("\n");
}

function chartPayloadFromState(state) {
  return {
    title: state.title,
    type: state.type,
    notes: state.notes || "",
    bins: state.bins,
    interval_ms: normalizeInterval(state.interval_ms),
    content: chartToDataText(state),
  };
}

function getChartMeta(chart) {
  if (chart.type === "frequency") return { labels: chart.frequency.labels, values: chart.frequency.values };
  if (chart.type === "table") return { labels: [], values: [] };
  if (chart.type === "dynamic") {
    const frames = chart.frames || [];
    return { labels: chart.labels || [], values: frames[0]?.values || [], frames, intervalMs: normalizeInterval(chart.interval_ms) };
  }
  return { labels: chart.labels || [], values: chart.values || [] };
}

function chartColors(count) {
  const colors = ["#0ea5e9", "#16a34a", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6", "#f97316", "#64748b"];
  return Array.from({ length: count }, (_, index) => colors[index % colors.length]);
}

const watermarkPlugin = {
  id: "oxygenWatermark",
  afterDraw(chart, _args, options) {
    if (!options?.enabled) return;
    const { ctx, chartArea } = chart;
    ctx.save();
    ctx.font = "12px Microsoft YaHei, Segoe UI, sans-serif";
    ctx.textAlign = "right";
    ctx.textBaseline = "bottom";
    ctx.fillStyle = "rgba(15, 23, 42, 0.48)";
    ctx.fillText("由 氧分图表 软件生成", chartArea.right - 8, chartArea.bottom - 8);
    ctx.restore();
  },
};

function createChart(canvas, { type, labels, values, frames = [], intervalMs = 1000, animation = true, watermark = false }) {
  const normalizedType = type === "frequency" ? "bar" : type;
  const isDynamic = type === "dynamic";
  const initialFrame = isDynamic ? (frames[0] || { time: "", values }) : null;
  const chartType = isDynamic ? "bar" : normalizedType === "pie" ? "pie" : normalizedType === "line" ? "line" : "bar";

  return new Chart(canvas, {
    type: chartType,
    data: {
      labels,
      datasets: [{
        label: isDynamic ? initialFrame.time || "时间" : "",
        data: isDynamic ? initialFrame.values : values,
        backgroundColor: normalizedType === "pie" ? chartColors(labels.length) : "rgba(14, 165, 233, 0.72)",
        borderColor: "rgba(14, 165, 233, 0.95)",
        borderWidth: normalizedType === "line" ? 3 : 1,
        tension: 0.35,
        fill: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: isDynamic ? "y" : "x",
      animation: animation ? { duration: isDynamic ? Math.min(650, intervalMs * 0.65) : 400 } : false,
      plugins: {
        legend: { display: normalizedType === "pie" || isDynamic },
        title: { display: isDynamic, text: initialFrame?.time ? `时间：${initialFrame.time}` : "" },
        oxygenWatermark: { enabled: watermark },
      },
      scales: normalizedType === "pie" ? {} : {
        y: { beginAtZero: !isDynamic, ticks: { color: "#64748b" }, grid: { color: "rgba(148, 163, 184, 0.18)" } },
        x: { beginAtZero: true, ticks: { color: "#64748b" }, grid: { color: "rgba(148, 163, 184, 0.1)" } },
      },
    },
    plugins: [watermarkPlugin],
  });
}

function setDynamicFrame(chart, frame) {
  chart.data.datasets[0].data = frame.values || [];
  chart.data.datasets[0].label = frame.time || "时间";
  chart.options.plugins.title.text = frame.time ? `时间：${frame.time}` : "";
  chart.update();
}

function renderChart(container) {
  if (!container || !window.Chart) return null;
  if (container._dynamicTimer) clearInterval(container._dynamicTimer);
  if (container._chartInstance) container._chartInstance.destroy();
  container._dynamicTimer = null;
  container._chartInstance = null;

  const type = container.dataset.chartType;
  const labels = parseJSON(container.dataset.labels, []);
  const values = parseJSON(container.dataset.values, []);
  const frames = parseJSON(container.dataset.frames, []);
  const intervalMs = normalizeInterval(container.dataset.intervalMs);
  if (!Array.isArray(labels) || !Array.isArray(values)) return null;

  const canvas = document.createElement("canvas");
  container.replaceChildren(canvas);
  const chart = createChart(canvas, { type, labels, values, frames, intervalMs, watermark: type === "dynamic" });

  if (type === "dynamic" && frames.length > 1) {
    let frameIndex = 0;
    container._dynamicTimer = setInterval(() => {
      frameIndex = (frameIndex + 1) % frames.length;
      setDynamicFrame(chart, frames[frameIndex]);
    }, intervalMs);
  }

  container._chartInstance = chart;
  return chart;
}

class Editor {
  constructor(root) {
    this.root = root;
    this.chartId = root.dataset.chartId;
    this.state = normalizeChart(parseJSON(document.getElementById("chart-bootstrap").textContent, {}));
    this.state.content = chartToDataText(this.state);
    this.undoStack = [];
    this.redoStack = [];
    this.autosaveTimer = null;
    this.isDirty = false;

    this.titleInput = document.getElementById("title-input");
    this.typeInput = document.getElementById("type-input");
    this.notesInput = document.getElementById("notes-input");
    this.binsInput = document.getElementById("bins-input");
    this.binsWrap = document.getElementById("bins-wrap");
    this.dynamicTools = document.getElementById("dynamic-tools");
    this.intervalInput = document.getElementById("interval-input");
    this.videoBtn = document.getElementById("export-video-btn");
    this.statusText = document.getElementById("status-text");
    this.versionList = document.getElementById("version-list");
    this.versionToggle = document.getElementById("version-toggle");
    this.previewNode = document.getElementById("preview-chart");
    this.dataEditor = document.getElementById("data-editor");

    this.bindEvents();
    this.renderAll();
  }

  bindEvents() {
    this.titleInput.addEventListener("input", () => this.updateDraft({ title: this.titleInput.value }));
    this.notesInput.addEventListener("input", () => this.updateDraft({ notes: this.notesInput.value }));
    this.binsInput.addEventListener("input", () => this.updateDraft({ bins: Number(this.binsInput.value || 8) }));
    this.intervalInput?.addEventListener("input", () => this.updateDraft({ interval_ms: normalizeInterval(this.intervalInput.value) }));
    this.typeInput.addEventListener("change", () => this.changeType(this.typeInput.value));

    document.getElementById("save-btn").addEventListener("click", () => this.save());
    document.getElementById("undo-btn").addEventListener("click", () => this.undo());
    document.getElementById("redo-btn").addEventListener("click", () => this.redo());
    document.getElementById("export-json-btn")?.addEventListener("click", () => this.exportJSON());
    document.getElementById("export-csv-btn")?.addEventListener("click", () => this.exportCSV());
    this.videoBtn?.addEventListener("click", () => this.exportDynamicVideo());
    document.getElementById("import-input")?.addEventListener("change", (event) => this.importJSON(event));
    this.versionToggle?.addEventListener("click", () => this.versionList.classList.toggle("is-collapsed"));

    window.addEventListener("beforeunload", (event) => {
      if (this.isDirty) {
        event.preventDefault();
        event.returnValue = "";
      }
    });
  }

  pushHistory() {
    this.undoStack.push(clone(this.state));
    if (this.undoStack.length > 30) this.undoStack.shift();
    this.redoStack.length = 0;
  }

  markDirty(message = "已修改，等待自动保存") {
    this.isDirty = true;
    this.statusText.textContent = message;
    clearTimeout(this.autosaveTimer);
    this.autosaveTimer = setTimeout(() => this.save(true), 1200);
  }

  updateDraft(partial) {
    this.state = normalizeChart({ ...this.state, ...partial });
    this.renderPreview();
    this.syncConditionalControls();
    this.markDirty();
  }

  changeType(type) {
    this.pushHistory();
    const previousContent = this.state.content;
    this.state.type = type;
    if (type === "frequency") {
      this.state.content = this.state.source_values ? this.state.source_values.join("\n") : previousContent;
      this.state.bins = this.state.bins || 8;
    } else if (type === "dynamic") {
      this.state = normalizeChart({
        ...this.state,
        type,
        labels: this.state.labels?.length ? this.state.labels : ["A", "B", "C"],
        frames: this.state.frames?.length ? this.state.frames : [
          { time: "0", values: [10, 20, 14] },
          { time: "1", values: [16, 12, 22] },
          { time: "2", values: [25, 18, 11] },
        ],
        interval_ms: this.state.interval_ms || 1000,
      });
      this.state.content = chartToDataText(this.state);
    } else {
      this.state.content = previousContent || chartToDataText(this.state);
    }
    this.syncInputs();
    this.renderAll();
    this.markDirty("图表类型已切换");
  }

  undo() {
    const prev = this.undoStack.pop();
    if (!prev) return;
    this.redoStack.push(clone(this.state));
    this.state = normalizeChart(prev);
    this.syncInputs();
    this.renderAll();
    this.markDirty("已撤销");
  }

  redo() {
    const next = this.redoStack.pop();
    if (!next) return;
    this.undoStack.push(clone(this.state));
    this.state = normalizeChart(next);
    this.syncInputs();
    this.renderAll();
    this.markDirty("已重做");
  }

  syncConditionalControls() {
    this.binsWrap.style.display = this.state.type === "frequency" ? "grid" : "none";
    if (this.dynamicTools) this.dynamicTools.style.display = this.state.type === "dynamic" ? "grid" : "none";
    if (this.intervalInput) this.intervalInput.value = normalizeInterval(this.state.interval_ms);
  }

  syncInputs() {
    this.state = normalizeChart(this.state);
    this.titleInput.value = this.state.title || "";
    this.notesInput.value = this.state.notes || "";
    this.typeInput.value = this.state.type;
    this.binsInput.value = this.state.bins || 8;
    this.state.content = this.state.content || chartToDataText(this.state);
    this.syncConditionalControls();
  }

  renderAll() {
    this.renderPreview();
    this.renderTableEditor();
    this.renderVersions();
  }

  renderPreview() {
    if (!this.previewNode) return;
    const meta = getChartMeta(this.state);
    this.previewNode.dataset.chartType = this.state.type;
    this.previewNode.dataset.labels = JSON.stringify(meta.labels);
    this.previewNode.dataset.values = JSON.stringify(meta.values);
    this.previewNode.dataset.frames = JSON.stringify(meta.frames || []);
    this.previewNode.dataset.intervalMs = String(meta.intervalMs || 1000);
    renderChart(this.previewNode);
    document.getElementById("chart-title").textContent = this.state.title || "";
    const typeLabel = this.typeInput.options[this.typeInput.selectedIndex]?.text || this.state.type;
    document.getElementById("chart-badge").textContent = typeLabel;
  }

  renderTableEditor() {
    this.dataEditor.innerHTML = "";
    if (this.state.type === "table") return this.dataEditor.appendChild(this.renderSpreadsheet());
    if (this.state.type === "dynamic") return this.dataEditor.appendChild(this.renderDynamicSheet());

    const wrapper = document.createElement("div");
    wrapper.className = "data-list";
    this.getEditableRows().forEach((row, index) => {
      const item = document.createElement("div");
      item.className = "data-row";
      item.innerHTML = `<input data-kind="label" value="${row.label}" /><input data-kind="value" type="number" step="any" value="${row.value}" />`;
      const labelInput = item.querySelector('[data-kind="label"]');
      const valueInput = item.querySelector('[data-kind="value"]');
      labelInput.addEventListener("input", () => this.editPairRow(index, labelInput.value, valueInput.value));
      valueInput.addEventListener("input", () => this.editPairRow(index, labelInput.value, valueInput.value));
      wrapper.appendChild(item);
    });
    const addBtn = document.createElement("button");
    addBtn.className = "secondary";
    addBtn.type = "button";
    addBtn.textContent = "新增一行";
    addBtn.addEventListener("click", () => this.addPairRow());
    wrapper.appendChild(addBtn);
    this.dataEditor.appendChild(wrapper);
  }

  renderSpreadsheet() {
    const wrap = document.createElement("div");
    wrap.className = "spreadsheet";
    wrap.appendChild(this.renderToolbar([
      ["add-row", "+ 行", () => this.addTableRow()],
      ["add-col", "+ 列", () => this.addTableColumn()],
      ["del-row", "- 行", () => this.removeTableRow()],
      ["del-col", "- 列", () => this.removeTableColumn()],
    ]));
    const table = document.createElement("table");
    table.className = "sheet-table";
    this.renderSheetHeader(table, this.state.table?.headers || [], (colIndex, input) => this.editTableHeader(colIndex, input.value));
    this.renderSheetBody(table, this.state.table?.rows || [], (rowIndex, colIndex, input) => this.editTableCell(rowIndex, colIndex, input.value));
    wrap.appendChild(table);
    return wrap;
  }

  renderDynamicSheet() {
    const wrap = document.createElement("div");
    wrap.className = "spreadsheet dynamic-sheet";
    wrap.appendChild(this.renderToolbar([
      ["add-frame", "+ 时间", () => this.addDynamicFrame()],
      ["add-item", "+ 项目", () => this.addDynamicItem()],
      ["del-frame", "- 时间", () => this.removeDynamicFrame()],
      ["del-item", "- 项目", () => this.removeDynamicItem()],
    ]));
    const table = document.createElement("table");
    table.className = "sheet-table";
    const headers = ["时间", ...(this.state.labels || [])];
    const rows = (this.state.frames || []).map((frame) => [frame.time, ...(frame.values || [])]);
    this.renderSheetHeader(table, headers, (colIndex, input) => {
      if (colIndex > 0) this.editDynamicLabel(colIndex - 1, input.value);
    }, 0);
    this.renderSheetBody(table, rows, (rowIndex, colIndex, input) => {
      if (colIndex === 0) this.editDynamicTime(rowIndex, input.value);
      else this.editDynamicValue(rowIndex, colIndex - 1, input.value);
    });
    wrap.appendChild(table);
    return wrap;
  }

  renderToolbar(items) {
    const toolbar = document.createElement("div");
    toolbar.className = "spreadsheet-toolbar";
    items.forEach(([action, label, handler]) => {
      const button = document.createElement("button");
      button.className = "secondary";
      button.type = "button";
      button.dataset.action = action;
      button.textContent = label;
      button.addEventListener("click", handler);
      toolbar.appendChild(button);
    });
    return toolbar;
  }

  renderSheetHeader(table, headers, onInput, readonlyIndex = null) {
    const thead = document.createElement("thead");
    const headRow = document.createElement("tr");
    headers.forEach((head, colIndex) => {
      const th = document.createElement("th");
      const input = document.createElement("input");
      input.value = head;
      input.className = "sheet-input sheet-header";
      input.readOnly = readonlyIndex === colIndex;
      input.addEventListener("input", () => onInput(colIndex, input));
      input.addEventListener("keydown", (event) => this.sheetKeydown(event));
      th.appendChild(input);
      headRow.appendChild(th);
    });
    thead.appendChild(headRow);
    table.appendChild(thead);
  }

  renderSheetBody(table, rows, onInput) {
    const tbody = document.createElement("tbody");
    rows.forEach((row, rowIndex) => {
      const tr = document.createElement("tr");
      row.forEach((cell, colIndex) => {
        const td = document.createElement("td");
        const input = document.createElement("input");
        input.value = cell;
        input.className = "sheet-input";
        input.addEventListener("input", () => onInput(rowIndex, colIndex, input));
        input.addEventListener("keydown", (event) => this.sheetKeydown(event));
        td.appendChild(input);
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
  }

  sheetKeydown(event) {
    if (event.key !== "Tab") return;
    event.preventDefault();
    const inputs = Array.from(this.dataEditor.querySelectorAll(".sheet-input"));
    const index = inputs.indexOf(event.target);
    inputs[index + (event.shiftKey ? -1 : 1)]?.focus();
  }

  editTableHeader(colIndex, value) {
    this.pushHistory();
    this.state.table.headers[colIndex] = value;
    this.state.content = chartToDataText(this.state);
    this.renderPreview();
    this.markDirty();
  }

  editTableCell(rowIndex, colIndex, value) {
    this.pushHistory();
    this.state.table.rows[rowIndex][colIndex] = value;
    this.state.content = chartToDataText(this.state);
    this.renderPreview();
    this.markDirty();
  }

  addTableRow() {
    this.pushHistory();
    this.state.table.rows.push(Array.from({ length: this.state.table.headers.length }, () => ""));
    this.state.content = chartToDataText(this.state);
    this.renderAll();
    this.markDirty("已新增一行");
  }

  removeTableRow() {
    if (!this.state.table.rows.length) return;
    this.pushHistory();
    this.state.table.rows.pop();
    this.state.content = chartToDataText(this.state);
    this.renderAll();
    this.markDirty("已删除一行");
  }

  addTableColumn() {
    this.pushHistory();
    this.state.table.headers.push(`列${this.state.table.headers.length + 1}`);
    this.state.table.rows.forEach((row) => row.push(""));
    this.state.content = chartToDataText(this.state);
    this.renderAll();
    this.markDirty("已新增一列");
  }

  removeTableColumn() {
    if (!this.state.table.headers.length) return;
    this.pushHistory();
    this.state.table.headers.pop();
    this.state.table.rows.forEach((row) => row.pop());
    this.state.content = chartToDataText(this.state);
    this.renderAll();
    this.markDirty("已删除一列");
  }

  editDynamicLabel(index, value) {
    this.pushHistory();
    this.state.labels[index] = value;
    this.state.content = chartToDataText(this.state);
    this.renderPreview();
    this.markDirty();
  }

  editDynamicTime(rowIndex, value) {
    this.pushHistory();
    this.state.frames[rowIndex].time = value;
    this.state.content = chartToDataText(this.state);
    this.renderPreview();
    this.markDirty();
  }

  editDynamicValue(rowIndex, colIndex, value) {
    this.pushHistory();
    this.state.frames[rowIndex].values[colIndex] = Number(value || 0);
    this.state.content = chartToDataText(this.state);
    this.renderPreview();
    this.markDirty();
  }

  addDynamicFrame() {
    this.pushHistory();
    this.state.frames.push({ time: String(this.state.frames.length), values: this.state.labels.map(() => 0) });
    this.state.content = chartToDataText(this.state);
    this.renderAll();
    this.markDirty("已新增一个时间");
  }

  removeDynamicFrame() {
    if (this.state.frames.length <= 1) return;
    this.pushHistory();
    this.state.frames.pop();
    this.state.content = chartToDataText(this.state);
    this.renderAll();
    this.markDirty("已删除一个时间");
  }

  addDynamicItem() {
    this.pushHistory();
    this.state.labels.push(`项目${this.state.labels.length + 1}`);
    this.state.frames.forEach((frame) => frame.values.push(0));
    this.state.content = chartToDataText(this.state);
    this.renderAll();
    this.markDirty("已新增一个项目");
  }

  removeDynamicItem() {
    if (this.state.labels.length <= 1) return;
    this.pushHistory();
    this.state.labels.pop();
    this.state.frames.forEach((frame) => frame.values.pop());
    this.state.content = chartToDataText(this.state);
    this.renderAll();
    this.markDirty("已删除一个项目");
  }

  getEditableRows() {
    if (this.state.type === "frequency") {
      const labels = this.state.frequency?.labels || [];
      const values = this.state.frequency?.values || [];
      return labels.map((label, index) => ({ label, value: values[index] ?? 0 }));
    }
    return (this.state.labels || []).map((label, index) => ({ label, value: this.state.values?.[index] ?? 0 }));
  }

  editPairRow(index, label, value) {
    this.pushHistory();
    this.state.labels[index] = label;
    this.state.values[index] = Number(value || 0);
    this.markDirty();
    this.renderPreview();
  }

  addPairRow() {
    this.pushHistory();
    this.state.labels = [...(this.state.labels || []), "新项"];
    this.state.values = [...(this.state.values || []), 0];
    this.renderAll();
    this.markDirty("已新增一行");
  }

  renderVersions() {
    const versions = this.state.versions || [];
    this.versionList.innerHTML = versions.length
      ? versions.map((version, index) => `
          <button class="version-item" data-version-index="${index}" type="button">
            <strong>${version.updated_at || "历史版本"}</strong>
            <span>${version.type || ""}</span>
          </button>
        `).join("")
      : '<div class="hint">暂无历史版本</div>';
    this.versionList.classList.add("is-collapsed");
    this.versionList.querySelectorAll("[data-version-index]").forEach((btn) => {
      btn.addEventListener("click", () => this.revertToVersion(Number(btn.dataset.versionIndex)));
    });
  }

  async revertToVersion(versionIndex) {
    const response = await fetch(`/api/chart/${this.chartId}/revert`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ version_index: versionIndex }),
    });
    if (!response.ok) return;
    this.state = normalizeChart(await response.json());
    this.state.content = chartToDataText(this.state);
    this.syncInputs();
    this.renderAll();
    this.statusText.textContent = "已回滚到历史版本";
  }

  async save(silent = false) {
    const response = await fetch(`/api/chart/${this.chartId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(chartPayloadFromState(this.state)),
    });
    if (!response.ok) {
      this.statusText.textContent = "保存失败";
      return;
    }
    this.state = normalizeChart(await response.json());
    this.state.content = chartToDataText(this.state);
    this.undoStack.length = 0;
    this.redoStack.length = 0;
    this.isDirty = false;
    this.statusText.textContent = silent ? "已自动保存" : "已保存";
    this.renderVersions();
  }

  exportJSON() {
    downloadText(`chart-${this.chartId}.json`, JSON.stringify(this.state, null, 2), "application/json");
  }

  exportCSV() {
    window.location.href = `/api/chart/${this.chartId}/export.csv`;
  }

  async exportDynamicVideo() {
    if (this.state.type !== "dynamic") return;
    this.videoBtn.disabled = true;
    this.statusText.textContent = "正在准备 MP4...";
    await this.save(true);
    window.location.href = `/api/chart/${this.chartId}/export.mp4`;
    setTimeout(() => {
      this.videoBtn.disabled = false;
      this.statusText.textContent = "MP4 已开始下载";
    }, 800);
  }

  async importJSON(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    const imported = JSON.parse(text);
    const response = await fetch(`/api/chart/${this.chartId}/import`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chart: imported }),
    });
    if (!response.ok) return;
    this.state = normalizeChart(await response.json());
    this.state.content = chartToDataText(this.state);
    this.syncInputs();
    this.renderAll();
    this.statusText.textContent = "已导入";
  }
}

function initIndexCharts() {
  document.querySelectorAll(".mini-chart").forEach((node) => renderChart(node));
}

function initEditor() {
  const root = document.querySelector(".editor-shell");
  if (!root) return;
  window.editor = new Editor(root);
}

function initChartForm() {
  const typeInput = document.getElementById("chart-type");
  const contentInput = document.getElementById("content-input");
  const binsWrap = document.getElementById("bins-wrap");
  const hint = document.getElementById("format-hint");
  if (!typeInput || !contentInput) return;

  const examples = {
    table: { text: "姓名,年龄,城市\n小王,28,上海\n小李,31,北京", hint: "表格：第一行是列名，后面每行是数据。" },
    bar: { text: "A,10\nB,20\nC,14", hint: "柱状图：每行一个“名称,数值”。" },
    pie: { text: "A,10\nB,20\nC,14", hint: "饼状图：每行一个“名称,数值”。" },
    line: { text: "1月,10\n2月,20\n3月,14", hint: "折线图：每行一个“名称,数值”。" },
    frequency: { text: "10\n12\n15\n18\n21\n24\n30", hint: "频数统计图：输入一组数值，系统按分组数统计。" },
    dynamic: {
      text: "time,A,B,C\n0,10,20,14\n1,16,12,22\n2,25,18,11",
      hint: "动态图表：第一列是时间，后面每列是项目；每一行表示该时间点各项目的数值。",
    },
  };

  const update = () => {
    const type = typeInput.value;
    binsWrap.style.display = type === "frequency" ? "grid" : "none";
    hint.textContent = examples[type]?.hint || "";
    if (!contentInput.value.trim()) contentInput.value = examples[type]?.text || "";
  };

  typeInput.addEventListener("change", () => {
    contentInput.value = examples[typeInput.value]?.text || contentInput.value;
    update();
  });
  update();
}

document.addEventListener("DOMContentLoaded", () => {
  initIndexCharts();
  initEditor();
  initChartForm();
});
