const modalBackdrop = document.querySelector("#modalBackdrop");
const modalTitle = document.querySelector("#modalTitle");
const modalDesc = document.querySelector("#modalDesc");
const modalClose = document.querySelector("#modalClose");
const uploadForm = document.querySelector("#uploadForm");
const downloadForm = document.querySelector("#downloadForm");
const result = document.querySelector("#result");
const fileInput = document.querySelector("#fileInput");
const fileChip = document.querySelector("#fileChip");
const retentionGroup = document.querySelector("#retentionGroup");
const retentionInput = uploadForm.querySelector('input[name="retention"]');
const homeButtons = [...document.querySelectorAll("[data-open]")];

let currentMode = "upload";

function setMode(mode) {
  currentMode = mode;
  uploadForm.classList.toggle("active", mode === "upload");
  downloadForm.classList.toggle("active", mode === "download");
  modalTitle.textContent = mode === "upload" ? "上传文件" : "下载文件";
  modalDesc.textContent =
    mode === "upload"
      ? "选择文件后设置留存时间和密码，系统会生成 8 位提取码。"
      : "输入提取码和密码，验证后即可下载。";
  result.className = "result";
  result.textContent = "";
}

function openModal(mode) {
  setMode(mode);
  modalBackdrop.classList.add("show");
  modalBackdrop.setAttribute("aria-hidden", "false");
  document.body.classList.add("no-scroll");
  if (mode === "upload") {
    setTimeout(() => fileInput.focus(), 120);
  } else {
    setTimeout(() => downloadForm.querySelector('input[name="code"]').focus(), 120);
  }
}

function closeModal() {
  modalBackdrop.classList.remove("show");
  modalBackdrop.setAttribute("aria-hidden", "true");
  document.body.classList.remove("no-scroll");
}

homeButtons.forEach((btn) => btn.addEventListener("click", () => openModal(btn.dataset.open)));
modalClose.addEventListener("click", closeModal);
modalBackdrop.addEventListener("click", (e) => {
  if (e.target === modalBackdrop) closeModal();
});
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
});

fileInput.addEventListener("change", () => {
  fileChip.textContent = fileInput.files?.[0]?.name || "选择文件";
});
fileChip.addEventListener("click", () => fileInput.click());
fileChip.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    fileInput.click();
  }
});
fileChip.tabIndex = 0;
fileChip.setAttribute("role", "button");

retentionGroup.addEventListener("click", (e) => {
  const btn = e.target.closest(".seg");
  if (!btn) return;
  retentionInput.value = btn.dataset.value;
  retentionGroup.querySelectorAll(".seg").forEach((el) => el.classList.toggle("active", el === btn));
});

function timeLabel(ms) {
  const map = [
    [7 * 24 * 60 * 60 * 1000, "7天"],
    [24 * 60 * 60 * 1000, "1天"],
    [12 * 60 * 60 * 1000, "12小时"],
    [60 * 60 * 1000, "1小时"],
    [10 * 60 * 1000, "10分钟"],
  ];
  const hit = map.find(([limit]) => ms >= limit);
  return hit ? hit[1] : "即将过期";
}

uploadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const formData = new FormData(uploadForm);
  result.className = "result";
  result.textContent = "上传中...";

  try {
    const resp = await fetch("/api/upload", {
      method: "POST",
      body: formData,
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.message || "上传失败");

    const expiresIn = new Date(data.expiresAt).getTime() - Date.now();
    result.className = "result ok";
    result.innerHTML = `上传成功。提取码 <b>${data.code}</b>，留存 ${timeLabel(expiresIn)}。`;
    uploadForm.reset();
    fileChip.textContent = "选择文件";
    retentionInput.value = "10m";
    retentionGroup.querySelector(".seg[data-value='10m']")?.classList.add("active");
    retentionGroup.querySelectorAll(".seg").forEach((el) => {
      if (el.dataset.value !== "10m") el.classList.remove("active");
    });
  } catch (err) {
    result.className = "result err";
    result.textContent = err.message;
  }
});

downloadForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const formData = new FormData(downloadForm);
  const code = String(formData.get("code") || "").trim();
  const password = String(formData.get("password") || "");
  result.className = "result";
  result.textContent = "验证中...";

  try {
    const resp = await fetch("/api/lookup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code, password }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.message || "验证失败");

    result.className = "result ok";
    result.innerHTML = `验证通过，开始下载：<b>${data.originalName}</b>`;
    window.location.href = `/api/download/${encodeURIComponent(code)}?password=${encodeURIComponent(password)}`;
    downloadForm.reset();
  } catch (err) {
    result.className = "result err";
    result.textContent = err.message;
  }
});

setMode("upload");
