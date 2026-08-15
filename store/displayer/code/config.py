from pathlib import Path
import os


BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'instance' / 'aura_music.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = BASE_DIR / "uploads"
    MAX_CONTENT_LENGTH = 200 * 1024 * 1024
    ALLOWED_EXTENSIONS = {
        "png",
        "jpg",
        "jpeg",
        "webp",
        "gif",
        "bmp",
        "mp3",
        "wav",
        "ogg",
        "m4a",
        "aac",
        "flac",
        "webm",
        "mp4",
        "mov",
        "mkv",
        "avi",
        "m4v",
        "3gp",
    }
