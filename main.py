import os
import asyncio
from flask import (
    Flask, request, jsonify, render_template_string, redirect,
    url_for, session, send_file, abort
)
from telethon import TelegramClient
from werkzeug.utils import secure_filename

# ---------------- CONFIG (GANTI JIKA PERLU) ----------------
API_ID = 29442225
API_HASH = "23885f682b37ef4dfc73f7c209b9b817"
PHONE = "+6281334863686"         # nomor akun Telegram (user) — Telethon akan minta OTP pertama kali
STORAGE_CHAT = "me"              # 'me' = Saved Messages, atau gunakan -100.... untuk channel
UPLOAD_CACHE_DIR = "uploads"     # lokal cache untuk uploaded/downloaded files
SESSION_NAME = "cloudnode_session"
# ---------------- USERS (LOGIN) ----------------
USERS = ["bramantara", "arya", "sri", "keniya", "frisma"]
PASSWORD = "admin"
# --------------------------------------------------------

os.makedirs(UPLOAD_CACHE_DIR, exist_ok=True)

# --------- Setup asyncio loop and Telethon client ----------
# create dedicated event loop for Telethon so Flask main thread won't conflict
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

async def _start_client():
    # Start Telethon (will prompt for OTP on first run)
    await client.start(phone=PHONE)
    me = await client.get_me()
    print(f"[Telethon] Logged in as: {getattr(me, 'username', None) or getattr(me, 'first_name', None)}")

# run start on loop
loop.run_until_complete(_start_client())

def run_async(coro):
    """Helper to run coroutine on Telethon event loop synchronously"""
    return loop.run_until_complete(coro)

# ----------------- Flask app -----------------
app = Flask(__name__)
app.secret_key = os.urandom(24)

def get_username_from_caption(caption):
    """Extract username from caption format: filename:username::cloudnode"""
    if not caption:
        return None
    parts = caption.split(':')
    if len(parts) >= 2:
        return parts[1]  # username is the second part
    return None

# ----------------- HTML (single-file UI) -----------------
LOGIN_HTML = """
<!doctype html>
<html>
<head><meta name="viewport" content="width=device-width, initial-scale=1">
<title>CloudNode Login</title>
<style>
body{margin:0;font-family:Arial;background:linear-gradient(135deg,#0b1220,#07102a);height:100vh;display:flex;align-items:center;justify-content:center;color:#fff}
.box{background:#0f1724;padding:28px;border-radius:12px;width:320px;box-shadow:0 6px 18px rgba(0,0,0,.6)}
input,select{width:100%;padding:10px;margin-top:12px;border-radius:8px;border:none;background:#0b1228;color:#fff}
button{width:100%;padding:12px;margin-top:16px;border-radius:8px;border:none;background:#2563eb;color:#fff}
</style>
</head>
<body>
<div class="box">
  <h2>CloudNode Login</h2>
  <form method="post" action="{{ url_for('login') }}">
    <select name="username" required>
      {% for u in users %}
      <option value="{{u}}">{{u}}</option>
      {% endfor %}
    </select>
    <input name="password" type="password" placeholder="Password" required>
    <button type="submit">Masuk</button>
  </form>
</div>
</body>
</html>
"""

DASH_HTML = """
<!doctype html>
<html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>CloudNode - Dashboard</title>
    <style>
        :root {
            --primary: #0072ff;
            --primary-dark: #005cc7;
            --secondary: #1e293b;
            --dark: #0f172a;
            --darker: #020617;
            --light: #f8fafc;
            --gray: #64748b;
            --gray-dark: #475569;
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, var(--darker) 0%, var(--dark) 100%);
            color: var(--light);
            line-height: 1.6;
            min-height: 100vh;
        }

        .app-container {
            display: flex;
            min-height: 100vh;
        }

        /* Sidebar Styles */
        .sidebar {
            width: 250px;
            background: var(--secondary);
            border-right: 1px solid rgba(255,255,255,0.1);
            display: flex;
            flex-direction: column;
        }

        .sidebar-header {
            padding: 24px 20px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            background: var(--dark);
        }

        .sidebar-header h1 {
            font-size: 1.5rem;
            font-weight: 600;
            color: var(--light);
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .sidebar-header h1::before {
            content: "🌩";
            font-size: 1.8rem;
        }

        .nav-section {
            padding: 20px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }

        .nav-section h3 {
            padding: 0 20px 12px 20px;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--gray);
        }

        .nav-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 20px;
            color: var(--light);
            text-decoration: none;
            transition: all 0.2s ease;
            border-left: 3px solid transparent;
        }

        .nav-item:hover {
            background: rgba(255,255,255,0.05);
            border-left-color: var(--primary);
        }

        .nav-item.active {
            background: rgba(0, 114, 255, 0.1);
            border-left-color: var(--primary);
            color: var(--primary);
        }

        .nav-item i {
            font-style: normal;
            font-size: 1.2rem;
        }

        .user-info {
            margin-top: auto;
            padding: 20px;
            background: var(--dark);
            border-top: 1px solid rgba(255,255,255,0.1);
        }

        .user-info .username {
            font-weight: 600;
            margin-bottom: 4px;
        }

        .user-info .status {
            font-size: 0.875rem;
            color: var(--success);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .status::before {
            content: "";
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--success);
        }

        /* Main Content Styles */
        .main-content {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        .top-bar {
            background: var(--secondary);
            padding: 16px 24px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .breadcrumb {
            font-size: 1.25rem;
            font-weight: 600;
        }

        .logout-btn {
            background: var(--danger);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.875rem;
            transition: background 0.2s ease;
        }

        .logout-btn:hover {
            background: #dc2626;
        }

        .content-area {
            flex: 1;
            padding: 24px;
            overflow-y: auto;
        }

        /* Card Styles */
        .card {
            background: var(--secondary);
            border-radius: 8px;
            border: 1px solid rgba(255,255,255,0.1);
            margin-bottom: 24px;
            overflow: hidden;
        }

        .card-header {
            padding: 20px 24px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            background: rgba(0, 0, 0, 0.2);
        }

        .card-header h2 {
            font-size: 1.25rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 10px;
        }

        .card-body {
            padding: 24px;
        }

        /* Upload Section */
        .upload-area {
            border: 2px dashed rgba(255,255,255,0.2);
            border-radius: 8px;
            padding: 40px 24px;
            text-align: center;
            transition: all 0.3s ease;
            background: rgba(0, 0, 0, 0.1);
        }

        .upload-area:hover {
            border-color: var(--primary);
            background: rgba(0, 114, 255, 0.05);
        }

        .upload-icon {
            font-size: 3rem;
            margin-bottom: 16px;
            opacity: 0.7;
        }

        .upload-text {
            margin-bottom: 20px;
            color: var(--gray);
        }

        .file-input-wrapper {
            position: relative;
            display: inline-block;
        }

        .file-input {
            position: absolute;
            left: 0;
            top: 0;
            opacity: 0;
            width: 100%;
            height: 100%;
            cursor: pointer;
        }

        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            font-size: 0.875rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }

        .btn-primary {
            background: var(--primary);
            color: white;
        }

        .btn-primary:hover {
            background: var(--primary-dark);
        }

        .btn-outline {
            background: transparent;
            color: var(--light);
            border: 1px solid var(--gray-dark);
        }

        .btn-outline:hover {
            background: rgba(255,255,255,0.05);
            border-color: var(--gray);
        }

        .btn-danger {
            background: var(--danger);
            color: white;
        }

        .btn-danger:hover {
            background: #dc2626;
        }

        .btn-success {
            background: var(--success);
            color: white;
        }

        .upload-status {
            margin-top: 16px;
            padding: 12px;
            border-radius: 6px;
            background: rgba(0, 0, 0, 0.3);
            font-size: 0.875rem;
        }

        /* Files Grid */
        .files-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
        }

        .file-card {
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 20px;
            transition: all 0.2s ease;
        }

        .file-card:hover {
            border-color: var(--primary);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        }

        .file-icon {
            font-size: 2rem;
            margin-bottom: 12px;
            opacity: 0.8;
        }

        .file-name {
            font-weight: 600;
            margin-bottom: 8px;
            word-break: break-word;
        }

        .file-meta {
            font-size: 0.875rem;
            color: var(--gray);
            margin-bottom: 16px;
        }

        .file-actions {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .file-actions .btn {
            flex: 1;
            min-width: 80px;
            justify-content: center;
            padding: 6px 12px;
            font-size: 0.75rem;
        }

        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 60px 24px;
            color: var(--gray);
        }

        .empty-state .icon {
            font-size: 4rem;
            margin-bottom: 16px;
            opacity: 0.5;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .app-container {
                flex-direction: column;
            }
            
            .sidebar {
                width: 100%;
                order: 2;
            }
            
            .main-content {
                order: 1;
            }
            
            .files-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="app-container">
        <!-- Sidebar -->
        <div class="sidebar">
            <div class="sidebar-header">
                <h1>CloudNode</h1>
            </div>
            
            <div class="nav-section">
                <h3>Storage</h3>
                <a href="#" class="nav-item active">
                    <i>📁</i>
                    <span>File Browser</span>
                </a>
                <a href="#" class="nav-item">
                    <i>📊</i>
                    <span>Storage Reports</span>
                </a>
                <a href="#" class="nav-item">
                    <i>🔄</i>
                    <span>Snapshots</span>
                </a>
            </div>
            
            <div class="nav-section">
                <h3>System</h3>
                <a href="#" class="nav-item">
                    <i>⚙️</i>
                    <span>System Settings</span>
                </a>
                <a href="#" class="nav-item">
                    <i>👥</i>
                    <span>Users & Groups</span>
                </a>
                <a href="#" class="nav-item">
                    <i>🛡️</i>
                    <span>Security</span>
                </a>
            </div>
            
            <div class="user-info">
                <div class="username">{{ user }}</div>
                <div class="status">Connected</div>
            </div>
        </div>

        <!-- Main Content -->
        <div class="main-content">
            <div class="top-bar">
                <div class="breadcrumb">File Browser</div>
                <form method="post" action="{{ url_for('logout') }}">
                    <button type="submit" class="logout-btn">Logout</button>
                </form>
            </div>
            
            <div class="content-area">
                <!-- Upload Card -->
                <div class="card">
                    <div class="card-header">
                        <h2>📤 Upload Files</h2>
                    </div>
                    <div class="card-body">
                        <div class="upload-area" id="uploadArea">
                            <div class="upload-icon">📁</div>
                            <div class="upload-text">
                                <h3>Drag & Drop files here</h3>
                                <p>or click to browse files</p>
                            </div>
                            <div class="file-input-wrapper">
                                <input id="fileinput" type="file" class="file-input">
                                <button class="btn btn-primary" onclick="document.getElementById('fileinput').click(); return false;">
                                    <span>Browse Files</span>
                                </button>
                            </div>
                            <button class="btn btn-success" onclick="upload()" style="margin-left: 10px;">
                                <span>Upload to Cloud</span>
                            </button>
                        </div>
                        <div id="upload-msg" class="upload-status">
                            Select a file to upload
                        </div>
                    </div>
                </div>

                <!-- Files List Card -->
                <div class="card">
                    <div class="card-header">
                        <h2>📂 Cloud Storage Files</h2>
                    </div>
                    <div class="card-body">
                        <div id="files" class="files-grid">
                            <div class="empty-state">
                                <div class="icon">📁</div>
                                <h3>No files found</h3>
                                <p>Upload your first file to get started</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script>
        async function upload() {
            const f = document.getElementById('fileinput').files[0];
            if(!f) { 
                document.getElementById('upload-msg').innerText = 'Please select a file first';
                document.getElementById('upload-msg').style.background = 'rgba(239, 68, 68, 0.2)';
                return; 
            }
            
            const fd = new FormData();
            fd.append('file', f);
            // username is embedded by server-side render
            const res = await fetch('/upload', { method: 'POST', body: fd });
            const j = await res.json();
            
            if (j.error) {
                document.getElementById('upload-msg').innerText = 'Upload failed: ' + j.error;
                document.getElementById('upload-msg').style.background = 'rgba(239, 68, 68, 0.2)';
            } else {
                document.getElementById('upload-msg').innerText = `✅ Upload successful! File ID: ${j.file_id || j.id}`;
                document.getElementById('upload-msg').style.background = 'rgba(16, 185, 129, 0.2)';
                loadList();
            }
        }

        async function loadList() {
            const el = document.getElementById('files');
            el.innerHTML = '<div class="empty-state"><div class="icon">⏳</div><h3>Loading files...</h3></div>';
            
            const res = await fetch('/list');
            const arr = await res.json();
            
            if (!Array.isArray(arr)) { 
                el.innerHTML = '<div class="empty-state"><div class="icon">⚠️</div><h3>Error loading files</h3></div>'; 
                return; 
            }
            
            if (arr.length === 0) { 
                el.innerHTML = '<div class="empty-state"><div class="icon">📁</div><h3>No files found</h3><p>Upload your first file to get started</p></div>'; 
                return; 
            }

            el.innerHTML = '';
            for (const f of arr) {
                const fileExt = f.name ? f.name.split('.').pop().toLowerCase() : '';
                const fileIcon = getFileIcon(fileExt);
                const fileSize = formatFileSize(f.size || 0);
                
                const fileCard = document.createElement('div');
                fileCard.className = 'file-card';
                fileCard.innerHTML = `
                    <div class="file-icon">${fileIcon}</div>
                    <div class="file-name">${f.name || ('file-' + f.id)}</div>
                    <div class="file-meta">${fileSize} • ID: ${f.id}</div>
                    <div class="file-actions">
                        <button class="btn btn-primary" onclick="window.open('/media/${f.id}', '_blank')">
                            👁️ View
                        </button>
                        <button class="btn btn-outline" onclick="downloadFile('${f.id}', '${f.name || ''}')">
                            📥 Download
                        </button>
                        <button class="btn btn-danger" onclick="deleteFile(${f.id})">
                            🗑️ Delete
                        </button>
                    </div>
                `;
                el.appendChild(fileCard);
            }
        }

        function getFileIcon(ext) {
            const iconMap = {
                'pdf': '📕',
                'doc': '📘',
                'docx': '📘',
                'txt': '📄',
                'zip': '📦',
                'rar': '📦',
                'jpg': '🖼️',
                'jpeg': '🖼️',
                'png': '🖼️',
                'gif': '🖼️',
                'mp4': '🎥',
                'avi': '🎥',
                'mov': '🎥',
                'mp3': '🎵',
                'wav': '🎵'
            };
            return iconMap[ext] || '📄';
        }

        function formatFileSize(bytes) {
            if (bytes === 0) return '0 B';
            const k = 1024;
            const sizes = ['B', 'KB', 'MB', 'GB'];
            const i = Math.floor(Math.log(bytes) / Math.log(k));
            return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
        }

        function downloadFile(id, name) {
            const a = document.createElement('a');
            a.href = '/media/' + id;
            a.download = name || '';
            document.body.appendChild(a);
            a.click();
            a.remove();
        }

        async function deleteFile(id) {
            if (!confirm(`Are you sure you want to delete file ID ${id}? This action cannot be undone.`)) return;
            
            const r = await fetch('/delete/' + id, { method: 'DELETE' });
            const j = await r.json();
            
            if (j.ok || j.success) {
                loadList();
            } else {
                alert('Delete failed: ' + (j.error || 'Unknown error'));
            }
        }

        // Load files when page loads
        loadList();

        // Drag and drop functionality
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileinput');

        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = 'var(--primary)';
            uploadArea.style.background = 'rgba(0, 114, 255, 0.1)';
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.style.borderColor = 'rgba(255,255,255,0.2)';
            uploadArea.style.background = 'rgba(0, 0, 0, 0.1)';
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.style.borderColor = 'rgba(255,255,255,0.2)';
            uploadArea.style.background = 'rgba(0, 0, 0, 0.1)';
            
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                document.getElementById('upload-msg').innerText = `File selected: ${e.dataTransfer.files[0].name}`;
                document.getElementById('upload-msg').style.background = 'rgba(0, 0, 0, 0.3)';
            }
        });

        fileInput.addEventListener('change', () => {
            if (fileInput.files.length) {
                document.getElementById('upload-msg').innerText = `File selected: ${fileInput.files[0].name}`;
                document.getElementById('upload-msg').style.background = 'rgba(0, 0, 0, 0.3)';
            }
        });
    </script>
<body>
</html>
"""

# ----------------- ROUTES -----------------

@app.route("/", methods=["GET", "POST"])
def login():
    # simple login page; store username in session
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username in USERS and password == PASSWORD:
            session['user'] = username
            return redirect(url_for("dashboard"))
        return "Login failed", 403
    return render_template_string(LOGIN_HTML, users=USERS)

@app.route("/dashboard")
def dashboard():
    if 'user' not in session:
        return redirect(url_for("login"))
    return render_template_string(DASH_HTML, user=session['user'])

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/upload", methods=["POST"])
def upload_route():
    if 'user' not in session:
        return jsonify({"error": "not authenticated"}), 401

    if 'file' not in request.files:
        return jsonify({"error": "no file provided"}), 400

    f = request.files['file']
    username = session.get('user', 'unknown')

    if f.filename == "":
        return jsonify({"error": "empty filename"}), 400

    filename = secure_filename(f.filename)
    local_path = os.path.join(UPLOAD_CACHE_DIR, filename)
    # If filename collision, suffix with number
    base, ext = os.path.splitext(filename)
    i = 1
    while os.path.exists(local_path):
        filename = f"{base}_{i}{ext}"
        local_path = os.path.join(UPLOAD_CACHE_DIR, filename)
        i += 1

    f.save(local_path)

    caption = f"{filename}:{username}::cloudnode"

    async def do_send():
        # send file to STORAGE_CHAT
        msg = await client.send_file(STORAGE_CHAT, local_path, caption=caption)
        return msg.id

    try:
        msg_id = run_async(do_send())
        return jsonify({"success": True, "file_id": msg_id, "file_name": filename})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/list", methods=["GET"])
def list_route():
    # returns list of recent messages in storage chat that include files, filtered by username
    async def do_list():
        msgs = await client.get_messages(STORAGE_CHAT, limit=100)
        out = []
        current_user = session.get('user')
        
        for m in msgs:
            if not m.file:
                continue
                
            # Check if message belongs to current user
            caption_username = get_username_from_caption(m.text)
            if caption_username != current_user:
                continue
                
            # file wrapper: name, size, ext, mime_type may be present
            fname = getattr(m.file, "name", None)
            if not fname:
                # fallback: build a filename from id and ext
                ext = getattr(m.file, "ext", None) or ''
                fname = f"{m.id}{('.' + ext) if ext else ''}"
            size = getattr(m.file, "size", None) or 0
            out.append({"id": m.id, "name": fname, "size": size})
        return out

    try:
        res = run_async(do_list())
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/media/<int:msg_id>")
def media_route(msg_id):
    """
    Serve the media for a given Telegram message id.
    Downloads to local cache (UPLOAD_CACHE_DIR/dl_{msg_id}_{name}) if not present,
    then returns file via send_file.
    Checks if the file belongs to the current user.
    """
    if 'user' not in session:
        abort(401)
        
    current_user = session.get('user')

    async def get_msg():
        msg = await client.get_messages(STORAGE_CHAT, ids=msg_id)
        return msg

    try:
        msg = run_async(get_msg())
    except Exception as e:
        return abort(500, description=f"Telegram error: {e}")

    if not msg:
        return abort(404, description="Message not found")

    if not msg.file:
        return abort(404, description="Message has no media")
        
    # Check ownership
    caption_username = get_username_from_caption(msg.text)
    if caption_username != current_user:
        return abort(403, description="Access denied - this file does not belong to you")

    # determine cache filename
    fname = getattr(msg.file, "name", None)
    ext = getattr(msg.file, "ext", None) or ''
    if not fname:
        fname = f"msg_{msg_id}{('.' + ext) if ext else ''}"

    cache_name = f"dl_{msg_id}__{secure_filename(fname)}"
    cache_path = os.path.join(UPLOAD_CACHE_DIR, cache_name)

    # if not cached, download to cache_path
    if not os.path.exists(cache_path):
        async def do_download():
            # download_media returns the downloaded path
            res = await msg.download_media(file=cache_path)
            return res

        try:
            res = run_async(do_download())
            # some Telethon versions return None and write to path - ensure file exists
            if not res and not os.path.exists(cache_path):
                return abort(500, description="Failed to download media")
        except Exception as e:
            return abort(500, description=f"Download error: {e}")

    # serve file
    return send_file(cache_path, as_attachment=False)

@app.route("/delete/<int:msg_id>", methods=["DELETE"])
def delete_route(msg_id):
    if 'user' not in session:
        return jsonify({"error": "not authenticated"}), 401
        
    current_user = session.get('user')

    async def check_ownership_and_delete():
        # First check if the message belongs to the current user
        msg = await client.get_messages(STORAGE_CHAT, ids=msg_id)
        if not msg:
            return {"error": "Message not found"}
            
        caption_username = get_username_from_caption(msg.text)
        if caption_username != current_user:
            return {"error": "Access denied - this file does not belong to you"}
            
        # If ownership confirmed, delete the message
        result = await client.delete_messages(STORAGE_CHAT, msg_id)
        return {"success": True}

    try:
        result = run_async(check_ownership_and_delete())
        if "error" in result:
            return jsonify(result), 403
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------ Run app ------------
if __name__ == "__main__":
    print("Starting CloudNode (Flask + Telethon). If this is first run, expect OTP prompt in terminal.")
    app.run(host="0.0.0.0", port=8080)
