import os
from datetime import timedelta

# 基础配置
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SECRET_KEY = os.environ.get("SECRET_KEY") or "your-secret-key-123456"  # 生产环境替换为随机字符串

# 数据库配置（二选一）
# 方案1：SQLite（无需额外安装数据库）
SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "workbench.db")
# 方案2：MySQL（需先安装并启动MySQL）
# SQLALCHEMY_DATABASE_URI = "mysql+pymysql://用户名:密码@localhost:3306/workbench?charset=utf8mb4"

SQLALCHEMY_TRACK_MODIFICATIONS = False  # 关闭不必要的警告
PERMANENT_SESSION_LIFETIME = timedelta(days=7)  # 会话有效期