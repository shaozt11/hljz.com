from datetime import datetime

from flask_login import UserMixin

from extensions import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    collections = db.relationship("Collection", backref="owner", lazy=True, cascade="all, delete-orphan")
    songs = db.relationship("Song", backref="owner", lazy=True, cascade="all, delete-orphan")


class Collection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.String(255), default="")
    cover_filename = db.Column(db.String(255), default="")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    songs = db.relationship("Song", backref="collection", lazy=True)


class Song(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    artist = db.Column(db.String(120), default="")
    filename = db.Column(db.String(255), nullable=False, unique=True)
    original_filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(120), default="")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    collection_id = db.Column(db.Integer, db.ForeignKey("collection.id"), nullable=True, index=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))
