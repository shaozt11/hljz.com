// GoodThings大爆炸 - 多人协作工作台 JavaScript
// 全局变量
let currentUserId = null;
let currentUser = null;
let clockInterval = null;
let currentModule = 'home';
let modulesInitialized = {
    home: false,
    todo: false,
    mail: false,
    file: false,
    document: false,
    personalize: false
};




// 全局消息提示
function showMessage(message, type = 'info') {
    const prefix = type === 'success' ? '✅ ' : type === 'error' ? '❌ ' : 'ℹ️ ';
    alert(prefix + message);
}

// 初始化认证表单（登录/注册页面）
function initAuthForms() {
    // 登录表单
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value.trim();

            if (!username || !password) {
                showMessage('用户名和密码不能为空', 'error');
                return;
            }

            try {
                const res = await fetch('/api/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });

                if (!res.ok) {
                    showMessage('服务器响应失败，请稍后再试', 'error');
                    return;
                }

                const data = await res.json();
                if (data.code === 0) {
                    showMessage(data.msg, 'success');
                    setTimeout(() => window.location.href = '/', 1500);
                } else {
                    showMessage(data.msg || '用户名或密码错误', 'error');
                }
            } catch (err) {
                showMessage('网络错误，登录失败', 'error');
                console.error('登录报错：', err);
            }
        });
    }

    // 注册表单
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', async function (e) {
            e.preventDefault();
            const username = document.getElementById('regUsername').value.trim();
            const password = document.getElementById('regPassword').value.trim();
            const confirmPassword = document.getElementById('confirmPassword').value.trim();
            const email = document.getElementById('email').value.trim();

            if (!username || !password || !confirmPassword || !email) {
                showMessage('所有字段不能为空', 'error');
                return;
            }

            if (password !== confirmPassword) {
                showMessage('两次输入的密码不一致', 'error');
                return;
            }

            try {
                const res = await fetch('/api/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password, confirmPassword, email })
                });

                if (!res.ok) {
                    showMessage('服务器响应异常', 'error');
                    return;
                }

                const data = await res.json();
                if (data.code === 0) {
                    showMessage(data.msg, 'success');
                    setTimeout(() => window.location.href = '/login', 1500);
                } else {
                    showMessage(data.msg, 'error');
                }
            } catch (err) {
                showMessage('网络错误，注册失败', 'error');
                console.error(err);
            }
        });
    }
}

// 页面加载完成初始化
document.addEventListener('DOMContentLoaded', async function () {
    const currentPath = window.location.pathname;

    // 初始化主题（所有页面通用）
    initTheme();

    // 为登录和注册页面添加专门的表单处理
    if (currentPath === '/login' || currentPath === '/register') {
        initAuthForms();
        return;
    }

    // 检查登录状态（工作台页面）
    const user = await checkLoginStatus();
    if (!user) return;

    currentUser = user;
    currentUserId = user.id;

    // 初始化工作台（新导航结构）
    if (currentPath === '/') {
        // 更新侧边栏用户信息显示
        document.getElementById('sidebar-username').textContent = currentUser.username;
        if (currentUser.is_admin) {
            document.getElementById('sidebar-admin-panel').style.display = 'block';
        }

        // 绑定事件监听器（所有模态框和按钮）
        bindEventListeners();

        // 初始化导航
        initNavigation();

        // 默认激活首页模块
        await switchModule('home');
    }

    // 管理后台页面
    if (currentPath === '/admin') {
        const addForm = document.getElementById('add-user-form');
        if (addForm) {
            addForm.addEventListener('submit', addUser);
        }
        await loadAdminData();
    }
});

// 检查登录状态
async function checkLoginStatus() {
    try {
        const res = await fetch('/api/current-user');
        if (!res.ok) return null;
        const data = await res.json();
        if (data.code !== 0) {
            if (!window.location.pathname.includes('login') && !window.location.pathname.includes('register')) {
                window.location.href = '/login';
            }
            return null;
        }
        return data.data;
    } catch (err) {
        if (!window.location.pathname.includes('login') && !window.location.pathname.includes('register')) {
            window.location.href = '/login';
        }
        return null;
    }
}

// 绑定事件监听器
function bindEventListeners() {
    // 邮件模块事件
    document.getElementById('new-mail-btn')?.addEventListener('click', showMailModal);
    document.getElementById('send-mail')?.addEventListener('click', sendMail);
    document.getElementById('cancel-mail')?.addEventListener('click', closeMailModal);
    document.getElementById('close-mail-modal')?.addEventListener('click', closeMailModal);

    // 任务模块事件
    document.getElementById('new-task-btn')?.addEventListener('click', showTaskModal);
    document.getElementById('create-task')?.addEventListener('click', createTask);
    document.getElementById('cancel-task')?.addEventListener('click', closeTaskModal);
    document.getElementById('close-task-modal')?.addEventListener('click', closeTaskModal);

    // 文件模块事件
    document.getElementById('upload-file-btn')?.addEventListener('click', showFileModal);
    document.getElementById('upload-file')?.addEventListener('click', uploadFile);
    document.getElementById('cancel-file')?.addEventListener('click', closeFileModal);
    document.getElementById('close-file-modal')?.addEventListener('click', closeFileModal);

    // 文档模块事件
    document.getElementById('new-document-btn')?.addEventListener('click', createDocument);

    // 消息详情模态框事件
    document.getElementById('close-message-detail')?.addEventListener('click', closeMessageDetail);

    // 点击模态框背景关闭
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', function (e) {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    });
}

// ==================== 导航相关函数 ====================
function initNavigation() {
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', function () {
            const module = this.dataset.module;
            switchModule(module);
        });
    });
}

async function switchModule(moduleName) {
    // 更新导航激活样式
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.module === moduleName);
    });

    // 更新模块显示
    document.querySelectorAll('.module-page').forEach(page => {
        page.classList.toggle('active', page.id === `module-${moduleName}`);
    });

    currentModule = moduleName;

    // 如果该模块尚未初始化，加载数据
    if (!modulesInitialized[moduleName]) {
        await loadModuleData(moduleName);
        modulesInitialized[moduleName] = true;
    }

    // 特殊处理：首页时钟
    if (moduleName === 'home' && !clockInterval) {
        startHomeClock();
    }
}

async function loadModuleData(moduleName) {
    switch (moduleName) {
        case 'home':
            await loadNotifications();
            break;
        case 'todo':
            await loadTasks();
            break;
        case 'mail':
            await loadMessages();
            break;
        case 'file':
            await loadFiles();
            break;
        case 'document':
            await loadDocuments();
            break;
        case 'personalize':
            // 主题已在 initTheme 中初始化，无需额外加载
            break;
    }
}

function startHomeClock() {
    if (clockInterval) clearInterval(clockInterval);
    clockInterval = setInterval(() => {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('zh-CN', { hour12: false });
        document.getElementById('home-clock').textContent = timeStr;
        // 每 30 秒自动刷新一次通知列表
        if (currentModule === 'home') {
            loadNotifications();
        }
    }, 1000);
}

// ==================== 消息通知模块 ====================
async function loadNotifications() {
    try {
        const res = await fetch('/api/notifications');
        const data = await res.json();

        if (data.code === 0) {
            const listEl = document.getElementById('notification-list');
            if (data.data.length === 0) {
                listEl.innerHTML = '<div class="empty-msg">暂无通知</div>';
                return;
            }

            listEl.innerHTML = '';
            data.data.forEach(notif => {
                const item = document.createElement('div');
                item.className = 'message-item';
                item.style = 'justify-content: space-between; margin-bottom: 10px; cursor: default;';
                item.innerHTML = `
                    <div style="flex: 1;">
                        <div style="font-size: 15px; margin-bottom: 5px;">${notif.content}</div>
                        <div style="font-size: 12px; color: #999;">${notif.created_at}</div>
                    </div>
                    <button class="btn btn-danger" onclick="clearNotification(${notif.id})" style="padding: 4px 10px; font-size: 12px;">清除</button>
                `;
                listEl.appendChild(item);
            });
        }
    } catch (err) {
        console.error('加载通知失败:', err);
    }
}

async function clearNotification(id) {
    try {
        const res = await fetch(`/api/notifications/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.code === 0) {
            await loadNotifications();
        }
    } catch (err) {
        console.error('清除通知失败:', err);
    }
}

async function clearAllNotifications() {
    if (!confirm('确定要清除全部通知吗？')) return;
    try {
        const res = await fetch('/api/notifications', { method: 'DELETE' });
        const data = await res.json();
        if (data.code === 0) {
            await loadNotifications();
        }
    } catch (err) {
        console.error('清除全部通知失败:', err);
    }
}

// ==================== 邮件模块 ====================
async function loadMessages() {
    try {
        const res = await fetch('/api/messages');
        const data = await res.json();

        if (data.code === 0) {
            const mailList = document.getElementById('mail-list');
            const messages = data.data.messages;

            if (messages.length === 0) {
                mailList.innerHTML = '<div class="empty-msg">暂无未读消息</div>';
                return;
            }

            mailList.innerHTML = '';
            messages.forEach(msg => {
                const msgDiv = document.createElement('div');
                msgDiv.className = 'message-item';
                msgDiv.innerHTML = `
                    <div style="display: flex; flex-direction: column; flex: 1; text-align: left;">
                        <div style="margin-bottom: 5px;"><strong>来自：${msg.sender}</strong></div>
                        <div style="font-size: 12px; color: #666;">${msg.created_at}</div>
                    </div>
                `;
                msgDiv.addEventListener('click', () => showMessageDetail(msg));
                mailList.appendChild(msgDiv);
            });
        }
    } catch (err) {
        console.error('加载消息失败:', err);
    }
}

function showMailModal() {
    loadUserSelect();
    document.getElementById('mail-modal').style.display = 'block';
}

async function loadUserSelect() {
    try {
        const res = await fetch('/api/users');
        const data = await res.json();

        if (data.code === 0) {
            const select = document.getElementById('receiver-select');
            select.innerHTML = '<option value="">请选择接收人</option>';

            data.data.users.forEach(user => {
                const option = document.createElement('option');
                option.value = user.id;
                option.textContent = user.username;
                select.appendChild(option);
            });
        }
    } catch (err) {
        console.error('加载用户列表失败:', err);
    }
}

async function sendMail() {
    const receiverId = document.getElementById('receiver-select').value;
    const content = document.getElementById('mail-content').value.trim();

    if (!receiverId || !content) {
        showMessage('请选择接收人并输入消息内容', 'error');
        return;
    }

    try {
        const res = await fetch('/api/messages', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ receiver_id: parseInt(receiverId), content })
        });
        const data = await res.json();

        if (data.code === 0) {
            showMessage('消息发送成功！', 'success');
            closeMailModal();
            await loadMessages();
        } else {
            showMessage(data.msg, 'error');
        }
    } catch (err) {
        showMessage('网络错误，发送失败', 'error');
    }
}

function closeMailModal() {
    document.getElementById('mail-modal').style.display = 'none';
    document.getElementById('mail-content').value = '';
    document.getElementById('receiver-select').value = '';
}

function showMessageDetail(message) {
    const contentDiv = document.getElementById('message-content');
    contentDiv.innerHTML = `
        <div style="margin-bottom: 15px;">
            <strong>发送人：</strong> ${message.sender}
        </div>
        <div style="margin-bottom: 15px;">
            <strong>发送时间：</strong> ${message.created_at}
        </div>
        <div style="margin-bottom: 20px; padding: 15px; background: #121212; border-radius: 10px; border: 1px solid #333; white-space: pre-wrap;">
            <strong>消息内容：</strong><br>
${message.content}
        </div>
        <button class="btn btn-danger" onclick="deleteMessage(${message.id})">删除消息</button>
    `;
    document.getElementById('message-detail-modal').style.display = 'block';
}

async function deleteMessage(messageId) {
    try {
        const res = await fetch(`/api/messages/${messageId}`, {
            method: 'DELETE'
        });
        const data = await res.json();

        if (data.code === 0) {
            showMessage('消息已删除', 'success');
            closeMessageDetail();
            await loadMessages();
        } else {
            showMessage(data.msg, 'error');
        }
    } catch (err) {
        showMessage('网络错误，删除失败', 'error');
    }
}

function closeMessageDetail() {
    document.getElementById('message-detail-modal').style.display = 'none';
}

// ==================== 任务模块 ====================
async function loadTasks() {
    try {
        const res = await fetch('/api/tasks');
        const data = await res.json();

        if (data.code === 0) {
            const taskList = document.getElementById('task-list');
            const tasks = data.data.tasks;

            if (tasks.length === 0) {
                taskList.innerHTML = '<div class="empty-msg">暂无任务</div>';
                return;
            }

            taskList.innerHTML = '';
            tasks.forEach(task => {
                const taskDiv = document.createElement('div');
                taskDiv.className = `task-item ${task.status === 'done' ? 'completed' : ''}`;
                taskDiv.innerHTML = `
                    <input type="checkbox" class="task-checkbox" 
                           ${task.status === 'done' ? 'checked' : ''} 
                           onchange="toggleTaskStatus(${task.id}, this.checked)">
                    <div style="display: flex; flex-direction: column; flex: 1; text-align: left;">
                        <div><strong>${task.title}</strong></div>
                        <div style="margin: 5px 0; color: #999;">${task.content || '无描述'}</div>
                    </div>
                    ${currentUser.is_admin ?
                        `<button class="btn-icon" style="background: #dc3545; margin-left: 10px;" onclick="deleteTask(${task.id})">×</button>`
                        : ''}
                `;
                taskList.appendChild(taskDiv);
            });
        }
    } catch (err) {
        console.error('加载任务失败:', err);
    }
}

function showTaskModal() {
    loadTaskUserSelect();
    document.getElementById('task-modal').style.display = 'block';
}

async function loadTaskUserSelect() {
    try {
        const select = document.getElementById('task-assignee');
        select.innerHTML = '<option value="">请选择负责人</option>';

        if (!currentUser.is_admin) {
            const option = document.createElement('option');
            option.value = currentUserId;
            option.textContent = currentUser.username;
            select.appendChild(option);
            select.value = currentUserId;
            return;
        }

        const res = await fetch('/api/users');
        const data = await res.json();

        if (data.code === 0) {
            const selfOption = document.createElement('option');
            selfOption.value = currentUserId;
            selfOption.textContent = currentUser.username + ' (自己)';
            select.appendChild(selfOption);

            data.data.users.forEach(user => {
                const option = document.createElement('option');
                option.value = user.id;
                option.textContent = user.username;
                select.appendChild(option);
            });
        }
    } catch (err) {
        console.error('加载用户列表失败:', err);
    }
}

async function createTask() {
    const title = document.getElementById('task-title').value.trim();
    const content = document.getElementById('task-content').value.trim();
    const assigneeId = document.getElementById('task-assignee').value;

    if (!title || !assigneeId) {
        showMessage('请输入任务标题并选择负责人', 'error');
        return;
    }

    try {
        const res = await fetch('/api/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title,
                content,
                assignee_id: parseInt(assigneeId)
            })
        });
        const data = await res.json();

        if (data.code === 0) {
            showMessage('任务创建成功！', 'success');
            closeTaskModal();
            await loadTasks();
        } else {
            showMessage(data.msg, 'error');
        }
    } catch (err) {
        showMessage('网络错误，创建失败', 'error');
    }
}

function closeTaskModal() {
    document.getElementById('task-modal').style.display = 'none';
    document.getElementById('task-title').value = '';
    document.getElementById('task-content').value = '';
    document.getElementById('task-assignee').value = '';
}

async function toggleTaskStatus(taskId, isDone) {
    try {
        const res = await fetch(`/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: isDone ? 'done' : 'todo' })
        });
        const data = await res.json();

        if (data.code === 0) {
            await loadTasks();
        } else {
            showMessage(data.msg, 'error');
            const checkbox = document.querySelector(`input[onchange*="toggleTaskStatus(${taskId}"]`);
            if (checkbox) checkbox.checked = !isDone;
        }
    } catch (err) {
        showMessage('网络错误，更新失败', 'error');
        const checkbox = document.querySelector(`input[onchange*="toggleTaskStatus(${taskId}"]`);
        if (checkbox) checkbox.checked = !isDone;
    }
}

async function deleteTask(taskId) {
    if (!confirm('确定要删除这个任务吗？')) return;

    try {
        const res = await fetch(`/api/tasks/${taskId}`, {
            method: 'DELETE'
        });
        const data = await res.json();

        if (data.code === 0) {
            showMessage('任务已删除', 'success');
            await loadTasks();
        } else {
            showMessage(data.msg, 'error');
        }
    } catch (err) {
        showMessage('网络错误，删除失败', 'error');
    }
}

// ==================== 网盘模块 ====================
async function loadFiles() {
    try {
        const res = await fetch('/api/files');
        const data = await res.json();

        if (data.code === 0) {
            const fileList = document.getElementById('file-list');
            const files = data.data.files;

            if (files.length === 0) {
                fileList.innerHTML = '<div class="empty-msg">暂无文件</div>';
                return;
            }

            fileList.innerHTML = '';
            files.forEach(file => {
                const fileDiv = document.createElement('div');
                fileDiv.className = 'file-item';
                fileDiv.innerHTML = `
                    <div class="file-info">
                        <div class="file-name">${file.file_name}</div>
                        <div class="file-meta">
                            <span class="file-size">${formatFileSize(file.file_size)}</span>
                            <span class="file-uploader">上传者：${file.uploader}</span>
                            <span>时间：${file.created_at}</span>
                        </div>
                    </div>
                    <button class="btn btn-primary" onclick="downloadFile(${file.id})" style="margin-left: 10px;">下载</button>
                    ${currentUser.is_admin ?
                        `<button class="btn btn-danger" onclick="deleteFile(${file.id})" style="margin-left: 10px;">删除</button>`
                        : ''}
                `;
                fileList.appendChild(fileDiv);
            });
        }
    } catch (err) {
        console.error('加载文件列表失败:', err);
    }
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function showFileModal() {
    document.getElementById('file-modal').style.display = 'block';
}

async function uploadFile() {
    const fileInput = document.getElementById('file-input');
    const file = fileInput.files[0];

    if (!file) {
        showMessage('请选择要上传的文件', 'error');
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    try {
        const res = await fetch('/api/files', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();

        if (data.code === 0) {
            showMessage('文件上传成功！', 'success');
            closeFileModal();
            await loadFiles();
        } else {
            showMessage(data.msg, 'error');
        }
    } catch (err) {
        showMessage('网络错误，上传失败', 'error');
    }
}

function closeFileModal() {
    document.getElementById('file-modal').style.display = 'none';
    document.getElementById('file-input').value = '';
}

async function downloadFile(fileId) {
    try {
        const res = await fetch(`/api/files/${fileId}/download`);
        if (!res.ok) {
            showMessage('文件下载失败', 'error');
            return;
        }

        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = ''; // 浏览器会自动使用原始文件名
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (err) {
        showMessage('网络错误，下载失败', 'error');
    }
}

async function deleteFile(fileId) {
    if (!confirm('确定要删除这个文件吗？此操作不可恢复！')) return;

    try {
        const res = await fetch(`/api/files/${fileId}`, {
            method: 'DELETE'
        });
        const data = await res.json();

        if (data.code === 0) {
            showMessage('文件已删除', 'success');
            await loadFiles();
        } else {
            showMessage(data.msg, 'error');
        }
    } catch (err) {
        showMessage('网络错误，删除失败', 'error');
    }
}

// ==================== 文档模块（模态框编辑 + 共享功能）====================
async function loadDocuments() {
    try {
        const res = await fetch('/api/documents');
        const data = await res.json();
        if (data.code === 0) {
            const docList = document.getElementById('document-list');
            const docs = data.data;
            if (docs.length === 0) {
                docList.innerHTML = '<div class="empty-msg">暂无文档，点击右上角 + 创建</div>';
                return;
            }
            docList.innerHTML = '';
            docs.forEach(doc => {
                const div = document.createElement('div');
                div.className = 'document-item';
                // 构建操作按钮
                let actionsHtml = '';

                // 所有者相关按钮
                if (doc.is_owner) {
                    if (doc.is_public) {
                        // 已共享：显示取消共享
                        actionsHtml += `<button onclick="unshareDocument(${doc.id})" class="btn-unshare">取消共享</button>`;
                    } else {
                        // 未共享：显示共享
                        actionsHtml += `<button onclick="shareDocument(${doc.id})" class="btn-share">共享</button>`;
                    }
                    // 所有者可以重命名和删除（无论是否共享）
                    actionsHtml += `<button onclick="renameDocument(${doc.id}, '${doc.filename}')" class="btn-rename">重命名</button>`;
                    actionsHtml += `<button onclick="deleteDocument(${doc.id})" class="btn-delete">删除</button>`;
                }
                // 所有人都可以导出
                actionsHtml += `<button onclick="exportDocument(${doc.id})" class="btn-export">导出</button>`;

                // 文档名称点击跳转到独立编辑页面
                div.innerHTML = `
                    <div class="document-info" onclick="openDocument(${doc.id})" style="cursor:pointer;">
                        <div class="document-name">${doc.filename} ${doc.is_public ? '🌐' : ''}</div>
                        <div class="document-meta">所有者ID: ${doc.owner_id} | 更新于 ${doc.updated_at}</div>
                    </div>
                    <div class="document-actions">
                        ${actionsHtml}
                    </div>
                `;
                docList.appendChild(div);
            });
        }
    } catch (err) {
        console.error('加载文档失败:', err);
    }
}

// 创建新文档
async function createDocument() {
    const filename = prompt('请输入文档名称（默认为“新文档.md”）:', '新文档.md');
    if (filename === null) return;
    const finalName = filename.trim() || `新文档_${Date.now()}.md`;
    try {
        const res = await fetch('/api/documents', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: finalName })
        });
        const data = await res.json();
        if (data.code === 0) {
            showMessage('文档创建成功', 'success');
            await loadDocuments();
            // 自动跳转到新文档编辑页
            openDocument(data.data.id);
        } else {
            showMessage(data.msg, 'error');
        }
    } catch (err) {
        showMessage('网络错误', 'error');
    }
}

// 打开文档编辑页面（跳转到独立页面）
function openDocument(docId) {
    window.location.href = `/document?id=${docId}`;
}

// 共享文档
async function shareDocument(docId) {
    if (!confirm('确定要将此文档共享给所有人吗？')) return;
    try {
        const res = await fetch(`/api/documents/${docId}/share`, {
            method: 'POST'
        });
        const data = await res.json();
        if (data.code === 0) {
            showMessage('共享成功', 'success');
            await loadDocuments(); // 刷新列表
        } else {
            showMessage(data.msg, 'error');
        }
    } catch (err) {
        showMessage('共享失败', 'error');
    }
}

// 取消共享文档
async function unshareDocument(docId) {
    if (!confirm('确定要取消共享此文档吗？文档将变为私有。')) return;
    try {
        const res = await fetch(`/api/documents/${docId}/unshare`, {
            method: 'POST'
        });
        const data = await res.json();
        if (data.code === 0) {
            showMessage('已取消共享', 'success');
            await loadDocuments(); // 刷新列表
        } else {
            showMessage(data.msg, 'error');
        }
    } catch (err) {
        showMessage('操作失败', 'error');
    }
}

// 重命名文档
async function renameDocument(docId, oldName) {
    const newName = prompt('输入新文件名（包含.md）', oldName);
    if (!newName || newName === oldName) return;
    try {
        const res = await fetch(`/api/documents/${docId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: newName })
        });
        const data = await res.json();
        if (data.code === 0) {
            showMessage('重命名成功', 'success');
            await loadDocuments(); // 刷新列表
        } else {
            showMessage(data.msg, 'error');
        }
    } catch (err) {
        showMessage('重命名失败', 'error');
    }
}

// 删除文档
async function deleteDocument(docId) {
    if (!confirm('确定要删除此文档吗？')) return;
    try {
        const res = await fetch(`/api/documents/${docId}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        if (data.code === 0) {
            showMessage('文档已删除', 'success');
            await loadDocuments(); // 刷新列表
        } else {
            showMessage(data.msg, 'error');
        }
    } catch (err) {
        showMessage('删除失败', 'error');
    }
}

// 导出文档
async function exportDocument(docId) {
    try {
        const res = await fetch(`/api/documents/${docId}/export`);
        if (!res.ok) {
            showMessage('导出失败', 'error');
            return;
        }
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = ''; // 使用服务器返回的文件名
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
    } catch (err) {
        showMessage('导出失败', 'error');
    }
}

// ==================== 通用功能 ====================
// 退出登录
async function logout() {
    try {
        const res = await fetch('/api/logout', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await res.json();
        showMessage(data.msg || '退出成功', 'success');
        setTimeout(() => window.location.href = '/login', 1000);
    } catch (err) {
        showMessage('网络错误，退出失败', 'error');
    }
}

// 进入管理员面板
function goToAdmin() {
    window.location.href = '/admin';
}

// 管理员功能
function refreshData() {
    if (window.location.pathname.includes('/admin')) {
        loadAdminData();
    }
}

function showUserManagement() {
    // 兼容旧版，如果页面上还有模态框则打开
    const modal = document.getElementById('user-management-modal');
    if (modal) {
        modal.style.display = 'block';
        loadManagementUsers();
    }
}

function closeUserManagement() {
    const modal = document.getElementById('user-management-modal');
    if (modal) modal.style.display = 'none';
}

async function loadAdminData() {
    try {
        document.getElementById('admin-username').textContent = currentUser?.username || 'Admin';

        const statsRes = await fetch('/api/admin/statistics');
        if (statsRes.ok) {
            const stats = await statsRes.json();
            if (stats.code === 0) {
                document.getElementById('total-users').textContent = stats.data.total_users;
            }
        }

        const usersRes = await fetch('/api/admin/users');
        if (usersRes.ok) {
            const users = await usersRes.json();
            if (users.code === 0) {
                window.adminUsersData = users.data;
                filterUsers();
            }
        }
    } catch (err) {
        console.error(err);
    }
}

function filterUsers() {
    const searchStr = document.getElementById('user-search')?.value.toLowerCase() || '';
    const tableBody = document.getElementById('users-table-body');
    if (!tableBody || !window.adminUsersData) return;

    tableBody.innerHTML = '';
    window.adminUsersData.forEach(user => {
        if (user.username.toLowerCase().includes(searchStr)) {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${user.username}</td>
                <td>${user.email}</td>
                <td>${user.create_time}</td>
                <td>
                    <button class="edit-btn" onclick="editAdminUser(${user.id}, '${user.username}', '${user.email}')">修改</button>
                    <button class="delete-btn" onclick="deleteAdminUser(${user.id})">删除</button>
                </td>
            `;
            tableBody.appendChild(tr);
        }
    });
}

async function loadManagementUsers() {
    try {
        const usersRes = await fetch('/api/admin/users');
        if (usersRes.ok) {
            const users = await usersRes.json();
            if (users.code === 0) {
                const tbody = document.getElementById('management-users-table');
                if (!tbody) return;
                tbody.innerHTML = '';
                users.data.forEach(user => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td>${user.username}</td>
                        <td>${user.email}</td>
                        <td>
                            <button class="edit-btn" onclick="editAdminUser(${user.id}, '${user.username}', '${user.email}')">修改密码/邮箱</button>
                            <button class="delete-btn" onclick="deleteAdminUser(${user.id})">删除</button>
                        </td>
                    `;
                    tbody.appendChild(tr);
                });
            }
        }
    } catch (err) {
        console.error(err);
    }
}

async function deleteAdminUser(id) {
    if (!confirm("确认删除？")) return;
    try {
        const res = await fetch('/api/admin/user/operate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'delete', id })
        });
        const data = await res.json();
        if (data.code === 0) {
            showMessage('删除成功', 'success');
            loadAdminData();
        } else {
            showMessage(data.msg, 'error');
        }
    } catch (err) {
        console.error(err);
    }
}

async function editAdminUser(id, oldUser, oldEmail) {
    const newUsername = prompt("输入新用户名 (留空不改):", oldUser) || "";
    const newEmail = prompt("输入新邮箱 (留空不改):", oldEmail) || "";
    const newPassword = prompt("输入新密码 (至少6位，留空不改):", "") || "";

    try {
        const res = await fetch('/api/admin/user/operate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                type: 'edit',
                id,
                username: newUsername !== oldUser ? newUsername : '',
                email: newEmail !== oldEmail ? newEmail : '',
                password: newPassword
            })
        });
        const data = await res.json();
        if (data.code === 0) {
            showMessage('修改成功', 'success');
            loadAdminData();
        } else {
            showMessage(data.msg, 'error');
        }
    } catch (err) {
        console.error(err);
    }
}

// 管理后台 - 添加用户表单
async function addUser(e) {
    e.preventDefault();
    const username = document.getElementById('new-username').value.trim();
    const password = document.getElementById('new-password').value.trim();
    const email = document.getElementById('new-email').value.trim();

    if (!username || !password || !email) {
        showMessage('所有字段不能为空', 'error');
        return;
    }

    try {
        const res = await fetch('/api/admin/user/operate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type: 'add', username, password, email })
        });
        const data = await res.json();
        if (data.code === 0) {
            showMessage('用户创建成功', 'success');
            document.getElementById('new-username').value = '';
            document.getElementById('new-password').value = '';
            document.getElementById('new-email').value = '';
            loadAdminData();
        } else {
            showMessage(data.msg, 'error');
        }
    } catch (err) {
        showMessage('网络错误', 'error');
    }
}

// ==================== 个性化 - 主题切换 ====================
function initTheme() {
    const saved = localStorage.getItem('pulwork-theme') || 'dark';
    applyTheme(saved);
}

function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('pulwork-theme', theme);

    // 更新切换按钮状态
    const toggle = document.getElementById('theme-toggle');
    if (toggle) {
        toggle.checked = (theme === 'light');
    }
    const label = document.getElementById('theme-label');
    if (label) {
        label.textContent = theme === 'light' ? '☀️ 白天模式' : '🌙 黑夜模式';
    }
}

function toggleTheme() {
    const current = localStorage.getItem('pulwork-theme') || 'dark';
    const next = current === 'dark' ? 'light' : 'dark';
    applyTheme(next);
}

// 页面关闭时清理定时器
window.addEventListener('beforeunload', function () {
    if (clockInterval) clearInterval(clockInterval);
});
