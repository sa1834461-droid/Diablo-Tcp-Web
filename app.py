import os
import sys
import subprocess
import threading
import requests
import time
from functools import wraps
from flask import Flask, render_template, render_template_string, request, jsonify, session, redirect, url_for
from flask_socketio import SocketIO

app = Flask(__name__)
app.secret_key = "purple_glass_unlimited_key" 
socketio = SocketIO(app, cors_allowed_origins="*")
# --- ADMIN CONFIG ---
ADMIN_PASSKEY = "8012" # Your custom passkey
active_users = set()


# --- CREDENTIAL CONFIG ---
# Hardcoded as requested
PANEL_USER = "admin"
PANEL_PASS = "changeme123"
GUILD_API_BASE = "https://danger-guild-management.vercel.app"

# --- LOGIN TEMPLATE (With Visible Credentials) ---
LOGIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Master Login | Unlimited</title>
    <style>
        body { background: #050505; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; font-family: 'Segoe UI', sans-serif; color: #fff; }
        .login-card { background: rgba(20, 10, 40, 0.8); padding: 40px; border-radius: 24px; width: 350px; border: 1px solid #a855f7; backdrop-filter: blur(10px); text-align: center; }
        .logo { font-size: 24px; font-weight: 800; color: #a855f7; letter-spacing: 3px; margin-bottom: 5px; }
        .cred-hint { font-size: 10px; color: #d946ef; margin-bottom: 25px; text-transform: uppercase; letter-spacing: 1px; }
        .input-group { text-align: left; margin-bottom: 15px; }
        .label { font-size: 10px; color: #a855f7; margin-bottom: 5px; font-weight: bold; }
        input { width: 100%; padding: 12px; background: #000; border: 1px solid #333; border-radius: 8px; color: #fff; box-sizing: border-box; }
        input:focus { border-color: #a855f7; outline: none; }
        button { background: #a855f7; color: white; border: none; width: 100%; padding: 12px; border-radius: 8px; font-weight: bold; cursor: pointer; margin-top: 10px; }
        .hint-box { margin-top: 20px; padding: 10px; background: rgba(168, 85, 247, 0.1); border-radius: 8px; border: 1px dashed #a855f7; font-size: 11px; }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="logo">TCP CONTROL PANEL</div>
        <div class="cred-hint">Unlimited Access Version</div>
        <div class="input-group">
            <div class="label">USERNAME</div>
            <input type="text" id="u" placeholder="admin">
        </div>
        <div class="input-group">
            <div class="label">PASSWORD</div>
            <input type="password" id="p" placeholder="changeme123">
        </div>
        <button onclick="doLogin()">AUTHENTICATE ➜</button>
        
        <div class="hint-box">
            <span style="color: #94a3b8">Default Access:</span><br>
            <b style="color: #fff">User: admin | Pass: changeme123</b>
        </div>
    </div>
    <script>
        async function doLogin() {
            const u = document.getElementById('u').value;
            const p = document.getElementById('p').value;
            const resp = await fetch('/api/login_auth', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({username: u, password: p})
            });
            const data = await resp.json();
            if(data.status === 'success') { window.location.href = '/'; } 
            else { alert('Access Denied'); }
        }
    </script>
</body>
</html>
"""

user_sessions = {}

def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if session.get('logged_in'): return f(*args, **kwargs)
        return redirect(url_for('login'))
    return wrap

def stream_logs(proc, name):
    try:
        for line in iter(proc.stdout.readline, ''):
            if line:
                socketio.emit('new_log', {'data': line.strip(), 'user': name})
        proc.stdout.close()
    except: pass

@app.route('/login')
def login():
    return render_template_string(LOGIN_HTML)

@app.route('/api/login_auth', methods=['POST'])
def login_auth():
    data = request.json
    if data.get('username') == PANEL_USER and data.get('password') == PANEL_PASS:
        session['logged_in'] = True
        return jsonify({"status": "success"})
    return jsonify({"status": "error"})

@app.route('/')
@login_required
def index():
    return render_template('index.html')

@app.route('/api/proxy_guild')
@login_required
def proxy_guild():
    t = request.args.get('type')
    gid = request.args.get('guild_id')
    reg = request.args.get('region')
    uid = request.args.get('uid')
    pw = request.args.get('password')
    
    urls = {
        'info': f"{GUILD_API_BASE}/guild?guild_id={gid}&region={reg}",
        'join': f"{GUILD_API_BASE}/join?guild_id={gid}&uid={uid}&password={pw}",
        'members': f"{GUILD_API_BASE}/members?guild_id={gid}&uid={uid}&password={pw}",
        'leave': f"{GUILD_API_BASE}/leave?guild_id={gid}&uid={uid}&password={pw}",
        'search': f"{GUILD_API_BASE}/search?name={gid}&region={reg}"
    }
    
    try:
        resp = requests.get(urls.get(t), timeout=15)
        return jsonify(resp.json())
    except:
        return jsonify({"success": False, "error": "API Timeout"}), 500

# Route to serve the admin page
import os

@app.route('/admin')
def admin_page():
    # Access restricted to panel login logic or simple routing
    return render_template('admin.html')

import os

import os
from flask import Flask, request, jsonify

# ... your existing app and socketio setup ...

@app.route('/api/admin/action', methods=['POST'])
def admin_api():
    data = request.json
    # Your Admin Password: 8012
    if str(data.get('passkey')) != "8012":
        return jsonify({"status": "error", "message": "UNAUTHORIZED"}), 403
    
    action = data.get('action')
    filename = data.get('filename')

    # 1. FIX: SCAN EVERY SINGLE FILE IN THE PROJECT
    if action == 'list_files':
        all_files = []
        for root, dirs, files in os.walk('.'):
            # Ignore hidden folders to keep the list clean
            if any(x in root for x in ['.git', '__pycache__', 'venv', '.replit']):
                continue
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), '.')
                all_files.append(rel_path)
        return jsonify({"status": "success", "files": sorted(all_files)})

    # 2. READ FILE
    if action == 'read':
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return jsonify({"status": "success", "content": f.read()})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})

    # 3. SAVE FILE (The Fix)
    if action == 'write':
        try:
            content = data.get('content', '')
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            return jsonify({"status": "success", "message": f"SAVED: {filename}"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})

    if action == 'broadcast':
        msg_text = data.get('message')
        socketio.emit('broadcast_msg', {'message': msg_text})
        return jsonify({"status": "success"})
@app.route('/api/control', methods=['POST'])
@login_required
def control_bot():
    data = request.json
    act = data.get('action')
    name = data.get('name')
    uid = data.get('uid')
    pw = data.get('pw')
    
    if act == 'start':
        # 1. Update bot.txt with User Input
        if uid and pw:
            try:
                with open('bot.txt', 'w', encoding='utf-8') as f:
                    f.write(f"uid={uid}\npassword={pw}")
            except Exception as e:
                return jsonify({"status": "error", "message": f"Write Error: {str(e)}"})

        # 2. Start main.py with Unbuffered Logs (-u) for Render
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        
        proc = subprocess.Popen(
            [sys.executable, '-u', 'main.py'], 
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=env
        )
        user_sessions[name] = {'proc': proc}
        threading.Thread(target=stream_logs, args=(proc, name), daemon=True).start()
        
        return jsonify({"status": "success", "message": "BOT STARTED", "running": True})
    
    elif act == 'stop' and name in user_sessions:
        user_sessions[name]['proc'].terminate()
        del user_sessions[name]
        return jsonify({"status": "success", "message": "TERMINATED", "running": False})

    return jsonify({"status": "error", "message": "ACTION FAILED"})

if __name__ == '__main__':
    # Render provides a PORT environment variable; if not found, use 10000
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
    
