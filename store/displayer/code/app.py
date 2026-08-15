from pathlib import Path
import re
import uuid

from flask import Flask, abort, flash, redirect, render_template, send_from_directory, url_for
from flask_login import current_user, login_required, login_user, logout_user
from flask_wtf import CSRFProtect
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import inspect

from config import Config
from extensions import db, login_manager
from forms import CollectionForm, LoginForm, RegisterForm, UploadForm
from models import Collection, Song, User


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def allowed_image_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in {"png", "jpg", "jpeg", "webp", "gif"}


def get_media_category(filename: str, mime_type: str = "") -> str:
    ext = Path(filename).suffix.lstrip(".").lower()
    if ext in {"png", "jpg", "jpeg", "webp", "gif", "bmp"}:
        return "image"
    if ext in {"mp4", "webm", "mov", "mkv", "avi", "m4v", "3gp"}:
        return "video"
    if mime_type.startswith("image/"):
        return "image"
    if mime_type.startswith("video/"):
        return "video"
    return "audio"


def infer_song_info_from_filename(filename: str) -> tuple[str, str]:
    stem = Path(filename).stem.strip()
    stem = re.sub(r"\s+", " ", stem)

    separators = [
        r"\s*-\s*",
        r"\s+—\s+",
        r"\s+–\s+",
        r"\s*_\s*",
    ]
    for pattern in separators:
        parts = re.split(pattern, stem, maxsplit=1)
        if len(parts) == 2:
            left = parts[0].strip(" -_—–[](){}")
            right = parts[1].strip(" -_—–[](){}")
            if left and right:
                return right, left

    return stem, ""


def save_uploaded_file(uploaded_file, upload_dir: Path, original_name: str) -> str:
    source_name = secure_filename(original_name.strip())
    ext = Path(original_name).suffix.lstrip(".").lower()
    if not ext:
        ext = source_name.rsplit(".", 1)[1].lower()
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    uploaded_file.save(upload_dir / stored_name)
    return stored_name


def ensure_collection_cover_column():
    inspector = inspect(db.engine)
    if not inspector.has_table("collection"):
        return
    columns = {column["name"] for column in inspector.get_columns("collection")}
    if "cover_filename" in columns:
        return
    with db.engine.begin() as connection:
        connection.exec_driver_sql("ALTER TABLE collection ADD COLUMN cover_filename VARCHAR(255) DEFAULT ''")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    CSRFProtect(app)
    db.init_app(app)
    login_manager.init_app(app)

    with app.app_context():
        db.create_all()
        ensure_collection_cover_column()

    @app.route("/")
    def index():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        form = RegisterForm()
        if form.validate_on_submit():
            username = form.username.data.strip()
            existing = User.query.filter_by(username=username).first()
            if existing:
                flash("用户名已存在。", "error")
            else:
                user = User(
                    username=username,
                    password_hash=generate_password_hash(form.password.data),
                )
                db.session.add(user)
                db.session.commit()
                flash("注册成功，请登录。", "success")
                return redirect(url_for("login"))
        return render_template("register.html", form=form)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data.strip()).first()
            if user and check_password_hash(user.password_hash, form.password.data):
                login_user(user)
                return redirect(url_for("dashboard"))
            flash("用户名或密码错误。", "error")
        return render_template("login.html", form=form)

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        collections = Collection.query.filter_by(user_id=current_user.id).order_by(Collection.created_at.desc()).all()
        songs = Song.query.filter_by(user_id=current_user.id).order_by(Song.uploaded_at.desc()).all()
        return render_template("dashboard.html", collections=collections, songs=songs)

    @app.route("/collections/new", methods=["GET", "POST"])
    @login_required
    def new_collection():
        form = CollectionForm()
        if form.validate_on_submit():
            cover_filename = ""
            cover_file = form.cover.data
            if cover_file and getattr(cover_file, "filename", ""):
                raw_cover_name = cover_file.filename.strip()
                if "." not in raw_cover_name:
                    flash("合集封面文件必须包含扩展名。", "error")
                    return render_template("collection_form.html", form=form)
                if not allowed_image_file(raw_cover_name):
                    flash("合集封面只支持 png、jpg、jpeg、webp、gif。", "error")
                    return render_template("collection_form.html", form=form)
                cover_filename = save_uploaded_file(cover_file, Path(app.config["UPLOAD_FOLDER"]), raw_cover_name)

            collection = Collection(
                name=form.name.data.strip(),
                description=(form.description.data or "").strip(),
                cover_filename=cover_filename,
                user_id=current_user.id,
            )
            db.session.add(collection)
            db.session.commit()
            flash("音乐合集已创建。", "success")
            return redirect(url_for("dashboard"))
        return render_template("collection_form.html", form=form)

    @app.route("/upload", methods=["GET", "POST"])
    @login_required
    def upload():
        form = UploadForm()
        collections = Collection.query.filter_by(user_id=current_user.id).order_by(Collection.name.asc()).all()
        form.collection_id.choices = [(0, "不归类")] + [(c.id, c.name) for c in collections]

        if form.validate_on_submit():
            file = form.file.data
            if not file or not file.filename:
                flash("请选择音乐文件。", "error")
                return render_template("upload.html", form=form)

            raw_filename = file.filename.strip()
            if "." not in raw_filename:
                flash("文件名必须包含扩展名。", "error")
                return render_template("upload.html", form=form)

            if not allowed_file(raw_filename):
                flash("暂不支持该文件格式。", "error")
                return render_template("upload.html", form=form)

            original_filename = Path(raw_filename).name
            stored_filename = save_uploaded_file(file, Path(app.config["UPLOAD_FOLDER"]), raw_filename)

            title_input = (form.title.data or "").strip()
            artist_input = (form.artist.data or "").strip()
            if not title_input and not artist_input:
                title = Path(raw_filename).stem.strip() or "未命名歌曲"
                artist = ""
            else:
                inferred_title, inferred_artist = infer_song_info_from_filename(raw_filename)
                title = title_input or inferred_title
                artist = artist_input or inferred_artist

            song = Song(
                title=title,
                artist=artist,
                filename=stored_filename,
                original_filename=original_filename,
                mime_type=file.mimetype or "",
                user_id=current_user.id,
                collection_id=form.collection_id.data or None,
            )
            db.session.add(song)
            db.session.commit()
            flash("上传成功。", "success")
            return redirect(url_for("dashboard"))

        return render_template("upload.html", form=form)

    @app.route("/collections/<int:collection_id>")
    @login_required
    def collection_detail(collection_id: int):
        collection = Collection.query.filter_by(id=collection_id, user_id=current_user.id).first_or_404()
        songs = Song.query.filter_by(collection_id=collection.id, user_id=current_user.id).order_by(Song.uploaded_at.desc()).all()
        return render_template("collection_detail.html", collection=collection, songs=songs)

    @app.route("/collection-cover/<int:collection_id>")
    @login_required
    def collection_cover(collection_id: int):
        collection = Collection.query.filter_by(id=collection_id, user_id=current_user.id).first_or_404()
        if not collection.cover_filename:
            abort(404)
        return send_from_directory(app.config["UPLOAD_FOLDER"], collection.cover_filename, as_attachment=False)

    @app.route("/play/<int:song_id>")
    @login_required
    def play_song(song_id: int):
        song = Song.query.filter_by(id=song_id, user_id=current_user.id).first_or_404()
        media_category = get_media_category(song.filename, song.mime_type)
        if song.collection_id:
            related_songs = (
                Song.query.filter(
                    Song.user_id == current_user.id,
                    Song.collection_id == song.collection_id,
                    Song.id != song.id,
                )
                .order_by(Song.uploaded_at.desc())
                .limit(6)
                .all()
            )
        else:
            related_songs = (
                Song.query.filter(
                    Song.user_id == current_user.id,
                    Song.id != song.id,
                )
                .order_by(Song.uploaded_at.desc())
                .limit(6)
                .all()
            )

        return render_template(
            "play.html",
            song=song,
            related_songs=related_songs,
            media_category=media_category,
        )

    @app.route("/media/<int:song_id>")
    @login_required
    def media(song_id: int):
        song = Song.query.filter_by(id=song_id, user_id=current_user.id).first_or_404()
        return send_from_directory(app.config["UPLOAD_FOLDER"], song.filename, as_attachment=False)

    @app.route("/songs/<int:song_id>/delete", methods=["POST"])
    @login_required
    def delete_song(song_id: int):
        song = Song.query.filter_by(id=song_id, user_id=current_user.id).first_or_404()
        file_path = Path(app.config["UPLOAD_FOLDER"]) / song.filename
        if file_path.exists():
            file_path.unlink()
        db.session.delete(song)
        db.session.commit()
        flash("歌曲已删除。", "success")
        return redirect(url_for("dashboard"))

    @app.route("/collections/<int:collection_id>/delete", methods=["POST"])
    @login_required
    def delete_collection(collection_id: int):
        collection = Collection.query.filter_by(id=collection_id, user_id=current_user.id).first_or_404()
        for song in collection.songs:
            song.collection_id = None
        if collection.cover_filename:
            cover_path = Path(app.config["UPLOAD_FOLDER"]) / collection.cover_filename
            if cover_path.exists():
                cover_path.unlink()
        db.session.delete(collection)
        db.session.commit()
        flash("合集已删除，歌曲已保留。", "success")
        return redirect(url_for("dashboard"))

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=6302)
