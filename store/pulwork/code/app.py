from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from datetime import datetime, date, timedelta
import hashlib
import os

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SECRET_KEY'] = 'test-secret-123456'  # 生产环境请使用环境变量
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'workbench.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)

db = SQLAlchemy(app)

# ------------------------------
# 数据库模型
# ------------------------------

# 用户模型
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(50), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    create_time = db.Column(db.DateTime, default=datetime.now)

    def set_password(self, pwd):
        self.password = hashlib.md5(pwd.encode()).hexdigest()

    def check_password(self, pwd):
        return self.password == hashlib.md5(pwd.encode()).hexdigest()

# 签到记录模型
class CheckInRecord(db.Model):
    __tablename__ = 'check_in_records'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, default=date.today)
    check_in_time = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref='records')

# 消息模型
class Message(db.Model):
    __tablename__ = "messages"
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    sender = db.relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    receiver = db.relationship("User", foreign_keys=[receiver_id], backref="received_messages")

# 任务模型
class Task(db.Model):
    __tablename__ = "tasks"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text)
    assignee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), default="todo")
    created_at = db.Column(db.DateTime, default=datetime.now)

    assignee = db.relationship("User", backref=db.backref("tasks", lazy=True))

# 文件模型
class File(db.Model):
    __tablename__ = "files"
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    uploader = db.relationship("User", backref=db.backref("uploaded_files", lazy=True))

# 文档模型（新增）
class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, default='')
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_public = db.Column(db.Boolean, default=False)  # 是否公开共享
    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    owner = db.relationship('User', backref=db.backref('documents', lazy=True))

# 聊天消息模型
class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref=db.backref('chat_messages', lazy=True))

# 文档评论模型
class DocumentComment(db.Model):
    __tablename__ = 'document_comments'
    id = db.Column(db.Integer, primary_key=True)
    doc_id = db.Column(db.Integer, db.ForeignKey('documents.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref=db.backref('document_comments', lazy=True))
    document = db.relationship('Document', backref=db.backref('comments', lazy=True, cascade='all, delete-orphan'))

# 通知模型
class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    user = db.relationship('User', backref=db.backref('notifications', lazy=True))

# 首次运行建表
with app.app_context():
    db.create_all()

# ------------------------------
# 消息模块 API
# ------------------------------
@app.route('/api/messages', methods=['GET'])
def api_get_messages():
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    user_id = session['user_id']
    
    messages = Message.query.filter_by(receiver_id=user_id).all()
    msg_list = []
    for msg in messages:
        msg_list.append({
            "id": msg.id,
            "sender": msg.sender.username,
            "content": msg.content,
            "created_at": msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return jsonify({"code": 0, "data": {"messages": msg_list}})

@app.route('/api/messages', methods=['POST'])
def api_send_message():
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    
    data = request.json
    receiver_id = data.get('receiver_id')
    content = data.get('content', '').strip()
    
    if not receiver_id or not content:
        return jsonify({"code": -1, "msg": "接收人和内容不能为空"})
    
    receiver = User.query.get(receiver_id)
    if not receiver:
        return jsonify({"code": -1, "msg": "接收人不存在"})
    
    message = Message(
        sender_id=session['user_id'],
        receiver_id=receiver_id,
        content=content
    )
    db.session.add(message)
    
    sender = User.query.get(session['user_id'])
    notif = Notification(user_id=receiver_id, content=f"用户{sender.username}向你发送了邮件")
    db.session.add(notif)
    
    db.session.commit()
    
    return jsonify({"code": 0, "msg": "消息发送成功"})

@app.route('/api/messages/<int:message_id>', methods=['DELETE'])
def api_delete_message(message_id):
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    
    message = Message.query.get(message_id)
    if not message:
        return jsonify({"code": -1, "msg": "消息不存在"})
    
    if message.receiver_id != session['user_id']:
        return jsonify({"code": -1, "msg": "无权限删除此消息"})
    
    db.session.delete(message)
    db.session.commit()
    
    return jsonify({"code": 0, "msg": "消息已删除"})

@app.route('/api/users', methods=['GET'])
def api_get_users():
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    
    users = User.query.filter(User.id != session['user_id']).all()
    user_list = []
    for user in users:
        user_list.append({
            "id": user.id,
            "username": user.username
        })
    
    return jsonify({"code": 0, "data": {"users": user_list}})

# ------------------------------
# 任务模块 API
# ------------------------------
@app.route('/api/tasks', methods=['GET'])
def api_get_tasks():
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    
    if session.get('is_admin'):
        tasks = Task.query.all()
    else:
        tasks = Task.query.filter_by(assignee_id=session['user_id']).all()
        
    task_list = []
    for task in tasks:
        task_list.append({
            "id": task.id,
            "title": task.title,
            "content": task.content,
            "assignee": task.assignee.username,
            "assignee_id": task.assignee_id,
            "status": task.status,
            "created_at": task.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return jsonify({"code": 0, "data": {"tasks": task_list}})

@app.route('/api/tasks', methods=['POST'])
def api_create_task():
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    
    data = request.json
    title = data.get('title', '').strip()
    content = data.get('content', '').strip()
    assignee_id = data.get('assignee_id')
    
    if not title or not assignee_id:
        return jsonify({"code": -1, "msg": "标题和负责人都不能为空"})
    
    assignee = User.query.get(assignee_id)
    if not assignee:
        return jsonify({"code": -1, "msg": "负责人不存在"})
    
    task = Task(
        title=title,
        content=content,
        assignee_id=assignee_id
    )
    db.session.add(task)
    
    if session.get('is_admin'):
        # 聚合待办通知
        base_content = "管理员为你新增了"
        existing_notif = Notification.query.filter(
            Notification.user_id == assignee_id,
            Notification.content.like(f"{base_content}%条待办"),
            Notification.is_read == False
        ).first()
        
        if existing_notif:
            import re
            match = re.search(r"新增了(\d+)条待办", existing_notif.content)
            if match:
                count = int(match.group(1)) + 1
                existing_notif.content = f"{base_content}{count}条待办"
                existing_notif.created_at = datetime.now()
        else:
            notif = Notification(user_id=assignee_id, content=f"{base_content}1条待办")
            db.session.add(notif)
        
    db.session.commit()
    
    return jsonify({
        "code": 0, 
        "msg": "任务创建成功",
        "data": {
            "id": task.id,
            "title": task.title,
            "assignee": assignee.username,
            "status": task.status
        }
    })

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def api_update_task(task_id):
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"code": -1, "msg": "任务不存在"})
    
    data = request.json
    status = data.get('status')
    
    if status and status in ['todo', 'done']:
        task.status = status
        db.session.commit()
        return jsonify({"code": 0, "msg": f"任务状态更新为{status}"})
    
    return jsonify({"code": -1, "msg": "无效的状态值"})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def api_delete_task(task_id):
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    
    task = Task.query.get(task_id)
    if not task:
        return jsonify({"code": -1, "msg": "任务不存在"})
    
    if not session.get('is_admin'):
        return jsonify({"code": -1, "msg": "无权限删除此任务"})
    
    db.session.delete(task)
    db.session.commit()
    
    return jsonify({"code": 0, "msg": "任务已删除"})

# ------------------------------
# 网盘模块 API
# ------------------------------
@app.route('/api/files', methods=['GET'])
def api_get_files():
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    
    files = File.query.all()
    file_list = []
    for file in files:
        file_list.append({
            "id": file.id,
            "file_name": file.file_name,
            "file_size": file.file_size,
            "uploader": file.uploader.username,
            "uploader_id": file.uploader_id,
            "created_at": file.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    
    return jsonify({"code": 0, "data": {"files": file_list}})

@app.route('/api/files', methods=['POST'])
def api_upload_file():
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    
    if 'file' not in request.files:
        return jsonify({"code": -1, "msg": "没有选择文件"})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"code": -1, "msg": "文件名不能为空"})
    
    upload_dir = os.path.join(BASE_DIR, 'uploads')
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    
    # 简单处理文件名，防止路径遍历
    safe_filename = os.path.basename(file.filename)
    file_path = os.path.join(upload_dir, safe_filename)
    file.save(file_path)
    
    file_record = File(
        file_name=safe_filename,
        file_size=os.path.getsize(file_path),
        uploader_id=session['user_id'],
        file_path=file_path
    )
    db.session.add(file_record)
    db.session.commit()
    
    return jsonify({
        "code": 0, 
        "msg": "文件上传成功",
        "data": {
            "id": file_record.id,
            "file_name": file_record.file_name,
            "file_size": file_record.file_size
        }
    })

@app.route('/api/files/<int:file_id>', methods=['DELETE'])
def api_delete_file(file_id):
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    
    if not session.get('is_admin'):
        return jsonify({"code": -1, "msg": "只有管理员可以删除文件"})
    
    file = File.query.get(file_id)
    if not file:
        return jsonify({"code": -1, "msg": "文件不存在"})
    
    if os.path.exists(file.file_path):
        os.remove(file.file_path)
    
    db.session.delete(file)
    db.session.commit()
    
    return jsonify({"code": 0, "msg": "文件已删除"})

@app.route('/api/files/<int:file_id>/download')
def api_download_file(file_id):
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    
    file = File.query.get(file_id)
    if not file:
        return jsonify({"code": -1, "msg": "文件不存在"})
    
    if not os.path.exists(file.file_path):
        return jsonify({"code": -1, "msg": "文件已丢失"})
    
    return send_file(file.file_path, as_attachment=True, download_name=file.file_name)

# ------------------------------
# 文档模块 API（新增）
# ------------------------------
@app.route('/api/documents', methods=['GET'])
def api_get_documents():
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    user_id = session['user_id']
    # 公开文档 OR 自己拥有的私有文档
    docs = Document.query.filter(
        (Document.is_public == True) | (Document.owner_id == user_id)
    ).order_by(Document.updated_at.desc()).all()
    doc_list = []
    for doc in docs:
        doc_list.append({
            "id": doc.id,
            "filename": doc.filename,
            "owner_id": doc.owner_id,
            "is_owner": doc.owner_id == user_id,
            "is_public": doc.is_public,
            "created_at": doc.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": doc.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    return jsonify({"code": 0, "data": doc_list})

@app.route('/api/documents', methods=['POST'])
def api_create_document():
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    data = request.json or {}
    filename = data.get('filename', '').strip()
    if not filename:
        filename = f"新文档_{datetime.now().strftime('%Y%m%d%H%M%S')}.md"
    if not (filename.endswith('.md') or filename.endswith('.txt')):
        filename += '.md'
    # 可选：检查同名文件
    existing = Document.query.filter_by(owner_id=session['user_id'], filename=filename).first()
    if existing:
        return jsonify({"code": -1, "msg": "文件名已存在"})
    doc = Document(
        filename=filename,
        content='',
        owner_id=session['user_id'],
        is_public=False
    )
    db.session.add(doc)
    db.session.commit()
    return jsonify({
        "code": 0,
        "msg": "文档创建成功",
        "data": {
            "id": doc.id,
            "filename": doc.filename
        }
    })

@app.route('/api/documents/<int:doc_id>', methods=['GET'])
def api_get_document(doc_id):
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"code": -1, "msg": "文档不存在"})
    # 如果不是公开且不是所有者，则无权限
    if not doc.is_public and doc.owner_id != session['user_id']:
        return jsonify({"code": -1, "msg": "无权限查看此文档"})
    return jsonify({
        "code": 0,
        "data": {
            "id": doc.id,
            "filename": doc.filename,
            "content": doc.content,
            "owner_id": doc.owner_id,
            "is_public": doc.is_public,
            "created_at": doc.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": doc.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        }
    })

@app.route('/api/documents/<int:doc_id>', methods=['PUT'])
def api_update_document(doc_id):
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"code": -1, "msg": "文档不存在"})
    # 权限：公开文档任何人可更新，私有文档仅所有者
    if not doc.is_public and doc.owner_id != session['user_id']:
        return jsonify({"code": -1, "msg": "无权限修改此文档"})
    data = request.json
    if 'content' in data:
        doc.content = data['content']
    if 'filename' in data:
        new_name = data['filename'].strip()
        if new_name:
            if not (new_name.endswith('.md') or new_name.endswith('.txt')):
                new_name += '.md'
            # 可选：检查重名（排除自身）
            existing = Document.query.filter_by(owner_id=session['user_id'], filename=new_name).first()
            if existing and existing.id != doc.id:
                return jsonify({"code": -1, "msg": "文件名已存在"})
            doc.filename = new_name
    db.session.commit()
    return jsonify({"code": 0, "msg": "文档已更新"})

@app.route('/api/documents/<int:doc_id>', methods=['DELETE'])
def api_delete_document(doc_id):
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"code": -1, "msg": "文档不存在"})
    if doc.owner_id != session['user_id']:
        return jsonify({"code": -1, "msg": "无权限删除此文档"})
    db.session.delete(doc)
    db.session.commit()
    return jsonify({"code": 0, "msg": "文档已删除"})

@app.route('/api/documents/<int:doc_id>/share', methods=['POST'])
def api_share_document(doc_id):
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"code": -1, "msg": "文档不存在"})
    if doc.owner_id != session['user_id']:
        return jsonify({"code": -1, "msg": "只有文档所有者可以共享"})
    if doc.is_public:
        return jsonify({"code": -1, "msg": "文档已经是公开状态"})
    doc.is_public = True
    db.session.commit()
    return jsonify({"code": 0, "msg": "文档已共享给所有人"})

@app.route('/api/documents/<int:doc_id>/unshare', methods=['POST'])
def api_unshare_document(doc_id):
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"code": -1, "msg": "文档不存在"})
    if doc.owner_id != session['user_id']:
        return jsonify({"code": -1, "msg": "只有文档所有者可以取消共享"})
    if not doc.is_public:
        return jsonify({"code": -1, "msg": "文档已经是私有状态"})
    doc.is_public = False
    db.session.commit()
    return jsonify({"code": 0, "msg": "文档已取消共享"})

@app.route('/api/documents/<int:doc_id>/comments', methods=['GET'])
def api_get_doc_comments(doc_id):
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    comments = DocumentComment.query.filter_by(doc_id=doc_id).order_by(DocumentComment.created_at.asc()).all()
    res = []
    for c in comments:
        res.append({
            "id": c.id,
            "username": c.user.username,
            "content": c.content,
            "created_at": c.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "user_id": c.user_id
        })
    return jsonify({"code": 0, "data": res})

@app.route('/api/documents/<int:doc_id>/comments', methods=['POST'])
def api_add_doc_comment(doc_id):
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"code": -1, "msg": "文档不存在"})
    
    data = request.json or {}
    content = data.get('content', '').strip()
    if not content:
        return jsonify({"code": -1, "msg": "评论不能为空"})
    
    comm = DocumentComment(doc_id=doc_id, user_id=session['user_id'], content=content)
    db.session.add(comm)
    
    # 聚合评论通知
    base_content = f"你的文稿{doc.filename}下新增加了"
    existing_notif = Notification.query.filter(
        Notification.user_id == doc.owner_id,
        Notification.content.like(f"{base_content}%条留言"),
        Notification.is_read == False
    ).first()
    
    if existing_notif:
        import re
        match = re.search(r"新增加了(\d+)条留言", existing_notif.content)
        if match:
            count = int(match.group(1)) + 1
            existing_notif.content = f"{base_content}{count}条留言"
            existing_notif.created_at = datetime.now()
    else:
        notif = Notification(user_id=doc.owner_id, content=f"{base_content}1条留言")
        db.session.add(notif)
        
    db.session.commit()
    return jsonify({"code": 0, "msg": "评论成功"})

@app.route('/api/documents/<int:doc_id>/comments/<int:cid>', methods=['DELETE'])
def api_delete_doc_comment(doc_id, cid):
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    comm = DocumentComment.query.get(cid)
    if not comm:
        return jsonify({"code": -1, "msg": "评论不存在"})
    doc = Document.query.get(doc_id)
    
    if session.get('is_admin') or (doc and doc.owner_id == session['user_id']):
        db.session.delete(comm)
        db.session.commit()
        return jsonify({"code": 0, "msg": "评论已删除"})
    return jsonify({"code": -1, "msg": "无权限"})

@app.route('/api/documents/<int:doc_id>/export', methods=['GET'])
def api_export_document(doc_id):
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    doc = Document.query.get(doc_id)
    if not doc:
        return jsonify({"code": -1, "msg": "文档不存在"})
    # 公开文档或所有者可导出
    if not doc.is_public and doc.owner_id != session['user_id']:
        return jsonify({"code": -1, "msg": "无权限导出此文档"})
    from io import BytesIO
    file_data = BytesIO()
    file_data.write(doc.content.encode('utf-8'))
    file_data.seek(0)
    return send_file(
        file_data,
        as_attachment=True,
        download_name=doc.filename,
        mimetype='text/markdown'
    )

# ------------------------------
# 聊天室 API
# ------------------------------
@app.route('/api/chat/messages', methods=['GET'])
def api_get_chat_messages():
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    # 支持 since_id 参数，只返回比该 ID 更新的消息
    since_id = request.args.get('since_id', 0, type=int)
    if since_id > 0:
        msgs = ChatMessage.query.filter(ChatMessage.id > since_id).order_by(ChatMessage.id.asc()).all()
    else:
        # 默认返回最近 100 条
        msgs = ChatMessage.query.order_by(ChatMessage.id.desc()).limit(100).all()
        msgs.reverse()
    msg_list = []
    for msg in msgs:
        msg_list.append({
            "id": msg.id,
            "user_id": msg.user_id,
            "username": msg.user.username,
            "content": msg.content,
            "created_at": msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    return jsonify({"code": 0, "data": msg_list})

@app.route('/api/chat/messages', methods=['POST'])
def api_send_chat_message():
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    data = request.json or {}
    content = data.get('content', '').strip()
    if not content:
        return jsonify({"code": -1, "msg": "消息内容不能为空"})
    msg = ChatMessage(
        user_id=session['user_id'],
        content=content
    )
    db.session.add(msg)
    db.session.commit()
    return jsonify({
        "code": 0,
        "msg": "发送成功",
        "data": {
            "id": msg.id,
            "user_id": msg.user_id,
            "username": msg.user.username,
            "content": msg.content,
            "created_at": msg.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
    })

# ------------------------------
# 页面路由
# ------------------------------
@app.route('/')
def index():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('index.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/admin')
def admin():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect('/login')
    return render_template('admin.html')

@app.route('/document')
def document_page():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('document.html')

@app.route('/chat')
def chat_page():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('chat.html')

# ------------------------------
# 用户注册、登录、退出
# ------------------------------
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.json
    username = data.get('username','').strip()
    password = data.get('password','').strip()
    confirm = data.get('confirmPassword','').strip()
    email = data.get('email','').strip()

    if not username or not password or not confirm or not email:
        return jsonify({"code":-1,"msg":"所有字段不能为空"})
    if password != confirm:
        return jsonify({"code":-1,"msg":"两次密码不一致"})
    if User.query.filter_by(username=username).first():
        return jsonify({"code":-1,"msg":"用户名已存在"})
    if User.query.filter_by(email=email).first():
        return jsonify({"code":-1,"msg":"邮箱已被注册"})

    u = User(username=username, email=email)
    u.set_password(password)
    if username.lower() == 'admin':
        u.is_admin = True
    db.session.add(u)
    db.session.commit()
    return jsonify({"code":0,"msg":"注册成功"})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    username = data.get('username','').strip()
    password = data.get('password','').strip()

    u = User.query.filter_by(username=username).first()
    if not u or not u.check_password(password):
        return jsonify({"code":-1,"msg":"用户名或密码错误"})

    session['user_id'] = u.id
    session['username'] = u.username
    session['is_admin'] = u.is_admin
    session.permanent = True
    return jsonify({"code":0,"msg":"登录成功"})

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({"code":0,"msg":"已退出登录"})

@app.route('/api/current-user', methods=['GET'])
def api_current_user():
    if 'user_id' not in session:
        return jsonify({"code":-1,"msg":"未登录"})
    u = User.query.get(session['user_id'])
    if not u:
        session.clear()
        return jsonify({"code":-1,"msg":"用户不存在"})
    return jsonify({
        "code":0,
        "data":{
            "id": u.id,
            "username":u.username,
            "is_admin":u.is_admin,
            "email":u.email,
            "create_time":u.create_time.strftime("%Y-%m-%d %H:%M:%S")
        }
    })

# ------------------------------
# ------------------------------
# 通知 API
# ------------------------------
@app.route('/api/notifications', methods=['GET'])
def api_get_notifications():
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    nots = Notification.query.filter_by(user_id=session['user_id']).order_by(Notification.id.desc()).all()
    res = []
    for n in nots:
        res.append({
            "id": n.id,
            "content": n.content,
            "is_read": n.is_read,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    return jsonify({"code": 0, "data": res})

@app.route('/api/notifications/<int:nid>', methods=['DELETE'])
def api_delete_notification(nid):
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    n = Notification.query.get(nid)
    if n and n.user_id == session['user_id']:
        db.session.delete(n)
        db.session.commit()
    return jsonify({"code": 0, "msg": "已清除"})

@app.route('/api/notifications', methods=['DELETE'])
def api_delete_all_notifications():
    if 'user_id' not in session:
        return jsonify({"code": -1, "msg": "未登录"})
    Notification.query.filter_by(user_id=session['user_id']).delete()
    db.session.commit()
    return jsonify({"code": 0, "msg": "全部清除"})

# ------------------------------
# 签到
# ------------------------------
@app.route('/api/check-in', methods=['POST'])
def api_checkin():
    if 'user_id' not in session:
        return jsonify({"code":-1,"msg":"请先登录"})
    uid = session['user_id']
    today = date.today()
    if CheckInRecord.query.filter_by(user_id=uid, date=today).first():
        return jsonify({"code":-1,"msg":"今日已签到"})
    r = CheckInRecord(user_id=uid, date=today)
    db.session.add(r)
    db.session.commit()
    return jsonify({"code":0,"msg":"签到成功"})

@app.route('/api/check-in-status', methods=['GET'])
def api_checkin_status():
    if 'user_id' not in session:
        return jsonify({"code":-1,"msg":"未登录"})
    uid = session['user_id']
    today = date.today()
    has = CheckInRecord.query.filter_by(user_id=uid, date=today).first()
    return jsonify({"code":0,"data":{"is_check_in":has is not None}})

@app.route('/api/checkin-list', methods=['GET'])
def api_checkin_list():
    if 'user_id' not in session:
        return jsonify({"code":-1,"msg":"未登录"})
    today = date.today()
    records = CheckInRecord.query.filter_by(date=today).all()
    arr = []
    for r in records:
        arr.append({
            "username": r.user.username,
            "time": r.check_in_time.strftime("%H:%M:%S")
        })
    return jsonify({"code":0,"data":arr})

# ------------------------------
# 管理员：统计、用户列表
# ------------------------------
@app.route('/api/admin/statistics', methods=['GET'])
def admin_stats():
    if not session.get('is_admin'):
        return jsonify({"code":-1,"msg":"无权限"})
    total = User.query.count()
    today = date.today()
    checked = CheckInRecord.query.filter_by(date=today).count()
    rate = round(checked/total*100,2) if total>0 else 0
    return jsonify({
        "code":0,
        "data":{
            "total_users":total,
            "today_check_in":checked,
            "check_in_rate":rate
        }
    })

@app.route('/api/admin/users', methods=['GET'])
def admin_users():
    if not session.get('is_admin'):
        return jsonify({"code":-1,"msg":"无权限"})
    users = User.query.all()
    today = date.today()
    arr = []
    for u in users:
        has = CheckInRecord.query.filter_by(user_id=u.id, date=today).first()
        arr.append({
            "id":u.id,
            "username":u.username,
            "email":u.email,
            "is_check_in":has is not None,
            "create_time":u.create_time.strftime("%Y-%m-%d %H:%M:%S")
        })
    return jsonify({"code":0,"data":arr})

# ------------------------------
# 管理员：增删改用户
# ------------------------------
@app.route('/api/admin/user/operate', methods=['POST'])
def admin_user_operate():
    if not session.get('is_admin'):
        return jsonify({"code":-1,"msg":"无权限"})
    data = request.json
    typ = data.get('type')

    if typ == 'add':
        username = data.get('username','').strip()
        pwd = data.get('password','').strip()
        email = data.get('email','').strip()
        if not username or not pwd or not email:
            return jsonify({"code":-1,"msg":"字段不能为空"})
        if User.query.filter_by(username=username).first():
            return jsonify({"code":-1,"msg":"用户名已存在"})
        u = User(username=username, email=email)
        u.set_password(pwd)
        db.session.add(u)
        db.session.commit()
        return jsonify({"code":0,"msg":"添加成功"})

    if typ == 'delete':
        uid = data.get('id')
        u = User.query.get(uid)
        if not u:
            return jsonify({"code":-1,"msg":"用户不存在"})
        CheckInRecord.query.filter_by(user_id=uid).delete()
        db.session.delete(u)
        db.session.commit()
        return jsonify({"code":0,"msg":"删除成功"})

    if typ == 'edit':
        uid = data.get('id')
        u = User.query.get(uid)
        if not u:
            return jsonify({"code":-1,"msg":"用户不存在"})
        username = data.get('username','').strip()
        email = data.get('email','').strip()
        pwd = data.get('password','').strip()
        if username: u.username = username
        if email: u.email = email
        if pwd and len(pwd)>=6: u.set_password(pwd)
        db.session.commit()
        return jsonify({"code":0,"msg":"修改成功"})

    return jsonify({"code":-1,"msg":"无效操作"})

# ------------------------------
# 管理员强制签到 / 取消签到
# ------------------------------
@app.route('/api/admin/force-checkin/<int:user_id>', methods=['POST'])
def admin_force_checkin(user_id):
    if not session.get('is_admin'):
        return jsonify({"code":-1,"msg":"无权限"})
    today = date.today()
    if CheckInRecord.query.filter_by(user_id=user_id, date=today).first():
        return jsonify({"code":-1,"msg":"该用户今日已签到"})
    r = CheckInRecord(user_id=user_id, date=today)
    db.session.add(r)
    db.session.commit()
    return jsonify({"code":0,"msg":"强制签到成功"})

@app.route('/api/admin/cancel-checkin/<int:user_id>', methods=['POST'])
def admin_cancel_checkin(user_id):
    if not session.get('is_admin'):
        return jsonify({"code":-1,"msg":"无权限"})
    today = date.today()
    cnt = CheckInRecord.query.filter_by(user_id=user_id, date=today).delete()
    if cnt == 0:
        return jsonify({"code":-1,"msg":"该用户今日未签到"})
    db.session.commit()
    return jsonify({"code":0,"msg":"已取消今日签到"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)