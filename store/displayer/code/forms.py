from flask_wtf import FlaskForm
from wtforms import FileField, SelectField, StringField, SubmitField, PasswordField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class RegisterForm(FlaskForm):
    username = StringField("用户名", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("密码", validators=[DataRequired(), Length(min=6, max=128)])
    submit = SubmitField("注册")


class LoginForm(FlaskForm):
    username = StringField("用户名", validators=[DataRequired()])
    password = PasswordField("密码", validators=[DataRequired()])
    submit = SubmitField("登录")


class CollectionForm(FlaskForm):
    name = StringField("合集名称", validators=[DataRequired(), Length(min=1, max=120)])
    description = TextAreaField("简介", validators=[Optional(), Length(max=255)])
    cover = FileField("合集封面", validators=[Optional()])
    submit = SubmitField("创建合集")


class UploadForm(FlaskForm):
    title = StringField("歌曲标题", validators=[Optional(), Length(max=120)])
    artist = StringField("歌手", validators=[Optional(), Length(max=120)])
    collection_id = SelectField("归属合集", coerce=int, validators=[Optional()])
    file = FileField("音乐文件", validators=[DataRequired()])
    submit = SubmitField("上传")
