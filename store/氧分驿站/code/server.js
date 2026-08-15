import express from "express";
import multer from "multer";
import crypto from "crypto";
import fs from "fs/promises";
import path from "path";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;
const DATA_DIR = path.join(__dirname, "data");
const UPLOAD_DIR = path.join(DATA_DIR, "uploads");
const META_FILE = path.join(DATA_DIR, "records.json");
const MAX_FILE_SIZE = 500 * 1024 * 1024;

await fs.mkdir(UPLOAD_DIR, { recursive: true });

app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

const storage = multer.diskStorage({
  destination: (_req, _file, cb) => cb(null, UPLOAD_DIR),
  filename: (_req, file, cb) => {
    const safeBase = path.basename(file.originalname).replace(/[^\w.\-()\u4e00-\u9fa5]/g, "_");
    cb(null, `${Date.now()}-${crypto.randomBytes(6).toString("hex")}-${safeBase}`);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: MAX_FILE_SIZE },
});

async function loadRecords() {
  try {
    const raw = await fs.readFile(META_FILE, "utf8");
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

async function saveRecords(records) {
  await fs.mkdir(DATA_DIR, { recursive: true });
  await fs.writeFile(META_FILE, JSON.stringify(records, null, 2), "utf8");
}

function hashPassword(password) {
  return crypto.createHash("sha256").update(password).digest("hex");
}

function generateCode(existing) {
  let code = "";
  do {
    code = String(crypto.randomInt(0, 100000000)).padStart(8, "0");
  } while (existing.has(code));
  return code;
}

function retentionToMs(value) {
  const map = {
    "10m": 10 * 60 * 1000,
    "1h": 60 * 60 * 1000,
    "12h": 12 * 60 * 60 * 1000,
    "24h": 24 * 60 * 60 * 1000,
    "1d": 24 * 60 * 60 * 1000,
    "2d": 2 * 24 * 60 * 60 * 1000,
    "3d": 3 * 24 * 60 * 60 * 1000,
    "4d": 4 * 24 * 60 * 60 * 1000,
    "5d": 5 * 24 * 60 * 60 * 1000,
    "6d": 6 * 24 * 60 * 60 * 1000,
    "7d": 7 * 24 * 60 * 60 * 1000,
  };
  return map[value] || null;
}

async function cleanupExpired() {
  const records = await loadRecords();
  const now = Date.now();
  const kept = [];

  for (const record of records) {
    const expired = record.expiresAt <= now;
    if (expired) {
      await fs.rm(record.filePath, { force: true }).catch(() => {});
      continue;
    }
    kept.push(record);
  }

  if (kept.length !== records.length) {
    await saveRecords(kept);
  }
}

setInterval(() => {
  cleanupExpired().catch(() => {});
}, 60 * 1000);

await cleanupExpired();

app.post("/api/upload", upload.single("file"), async (req, res) => {
  try {
    const { retention, password } = req.body;
    if (!req.file) {
      return res.status(400).json({ message: "请选择要上传的文件。" });
    }
    if (!password || password.length < 4) {
      await fs.rm(req.file.path, { force: true }).catch(() => {});
      return res.status(400).json({ message: "请设置至少 4 位密码。" });
    }
    const duration = retentionToMs(retention);
    if (!duration) {
      await fs.rm(req.file.path, { force: true }).catch(() => {});
      return res.status(400).json({ message: "请选择有效的留存时间。" });
    }

    const records = await loadRecords();
    const code = generateCode(new Set(records.map((r) => r.code)));
    const now = Date.now();
    const record = {
      code,
      passwordHash: hashPassword(password),
      originalName: req.file.originalname,
      storedName: req.file.filename,
      filePath: req.file.path,
      mimeType: req.file.mimetype,
      size: req.file.size,
      createdAt: now,
      expiresAt: now + duration,
    };

    records.push(record);
    await saveRecords(records);

    res.json({
      code,
      expiresAt: record.expiresAt,
      originalName: record.originalName,
    });
  } catch (error) {
    res.status(500).json({ message: "上传失败。", detail: String(error?.message || error) });
  }
});

app.post("/api/lookup", async (req, res) => {
  const { code, password } = req.body || {};
  if (!code || !password) {
    return res.status(400).json({ message: "请输入提取码和密码。" });
  }

  const records = await loadRecords();
  const record = records.find((item) => item.code === String(code).trim());
  if (!record) {
    return res.status(404).json({ message: "未找到对应文件，或文件已过期删除。" });
  }
  if (record.expiresAt <= Date.now()) {
    await cleanupExpired();
    return res.status(404).json({ message: "文件已过期删除。" });
  }
  if (record.passwordHash !== hashPassword(password)) {
    return res.status(403).json({ message: "密码错误。" });
  }

  res.json({
    code: record.code,
    originalName: record.originalName,
    size: record.size,
    expiresAt: record.expiresAt,
  });
});

app.get("/api/download/:code", async (req, res) => {
  const { password } = req.query;
  const code = String(req.params.code).trim();

  const records = await loadRecords();
  const record = records.find((item) => item.code === code);
  if (!record) {
    return res.status(404).send("文件不存在或已过期。");
  }
  if (record.expiresAt <= Date.now()) {
    await cleanupExpired();
    return res.status(404).send("文件已过期删除。");
  }
  if (!password || record.passwordHash !== hashPassword(String(password))) {
    return res.status(403).send("密码错误。");
  }

  res.download(record.filePath, record.originalName);
});

app.listen(PORT, () => {
  console.log(`Oxygen Station running at http://localhost:${PORT}`);
});
