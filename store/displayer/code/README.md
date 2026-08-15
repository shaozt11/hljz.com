# DisPlayer

一个基于 Flask 的在线音乐软件，支持：

- 用户注册 / 登录
- 音乐上传
- 音乐合集分类
- 在线播放
- 删除歌曲 / 合集

## 启动

```powershell
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
python app.py
```

然后访问 `http://127.0.0.1:5000`

## 说明

- 支持上传常见音频格式：`mp3`、`wav`、`ogg`、`m4a`、`aac`、`flac`、`webm`、`mp4`
- 播放依赖浏览器对音频编码的原生支持
- 数据库默认使用 `instance/aura_music.db`
