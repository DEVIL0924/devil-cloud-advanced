from flask import Flask, render_template, request, redirect, session, flash, jsonify, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os, json, subprocess, zipfile, psutil, re, time, shutil, hashlib, random, string
from datetime import datetime, timedelta
import threading
import logging

app = Flask(__name__)
app.secret_key = "devil-cloud-advanced-secret-key-2024"
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max file size

# -------------------------------
# PATHS AND CONFIGURATION
# -------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOTS_DIR = os.path.join(BASE_DIR, "bots")
USERS_DIR = os.path.join(BASE_DIR, "users")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
BOTS_FILE = os.path.join(DATA_DIR, "bots.json")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")

# Create directories
for dir_path in [BOTS_DIR, USERS_DIR, LOGS_DIR, DATA_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# -------------------------------
# CONFIGURATION LOAD/SAVE
# -------------------------------
def load_config():
    default_config = {
        "site_name": "DEVIL CLOUD HOSTING",
        "admin_password": "admin123",
        "default_user_storage": 500,  # MB
        "default_user_bot_limit": 10,
        "allowed_extensions": [".py", ".php", ".js", ".txt", ".zip"],
        "theme": "dark",
        "auto_start_bots": False,
        "maintenance_mode": False
    }
    
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return {**default_config, **json.load(f)}
        except:
            return default_config
    else:
        save_config(default_config)
        return default_config

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

def load_bots():
    if os.path.exists(BOTS_FILE):
        try:
            with open(BOTS_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_bots(bots):
    with open(BOTS_FILE, 'w') as f:
        json.dump(bots, f, indent=4)

def load_stats():
    default_stats = {
        "total_bots": 0,
        "running_bots": 0,
        "total_users": 0,
        "total_uploads": 0,
        "uptime": datetime.now().isoformat()
    }
    
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except:
            return default_stats
    return default_stats

def save_stats(stats):
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=4)

# -------------------------------
# USER MANAGEMENT FUNCTIONS
# -------------------------------
def create_user(username, email, password, is_admin=False):
    users = load_users()
    
    if username in users:
        return False, "Username already exists"
    
    user_id = hashlib.md5(f"{username}{email}".encode()).hexdigest()[:10]
    
    users[username] = {
        "id": user_id,
        "email": email,
        "password": generate_password_hash(password),
        "is_admin": is_admin,
        "created_at": datetime.now().isoformat(),
        "storage_limit": 500,  # MB
        "bot_limit": 10,
        "active": True,
        "bots": []
    }
    
    # Create user directory
    user_dir = os.path.join(USERS_DIR, username)
    os.makedirs(user_dir, exist_ok=True)
    
    save_users(users)
    
    # Update stats
    stats = load_stats()
    stats["total_users"] = len(users)
    save_stats(stats)
    
    return True, user_id

def authenticate_user(username, password):
    users = load_users()
    
    if username not in users:
        return False, None
    
    user = users[username]
    
    if not user["active"]:
        return False, None
    
    if check_password_hash(user["password"], password):
        return True, user
    
    return False, None

# -------------------------------
# BOT MANAGEMENT FUNCTIONS
# -------------------------------
def detect_language(filename):
    ext = os.path.splitext(filename)[1].lower()
    language_map = {
        '.py': 'python',
        '.php': 'php',
        '.js': 'node',
        '.sh': 'bash',
        '.txt': 'text'
    }
    return language_map.get(ext, 'unknown')

def auto_install_dependencies(filepath, language):
    if language != 'python':
        return
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
    except:
        return
    
    libs = set()
    
    # Find imports
    import_patterns = [
        r'^\s*import\s+([a-zA-Z0-9_\.]+)',
        r'^\s*from\s+([a-zA-Z0-9_\.]+)\s+import'
    ]
    
    for pattern in import_patterns:
        matches = re.findall(pattern, content, re.MULTILINE)
        for match in matches:
            lib = match.split('.')[0]
            if lib and lib not in ['os', 'sys', 'time', 'json', 're', 'math', 'random', 'subprocess', 'threading', 'asyncio', 'flask']:
                libs.add(lib)
    
    # Install each library
    for lib in libs:
        try:
            subprocess.run(['pip', 'install', '-q', lib], timeout=30)
        except:
            pass

def create_bot(username, filename, original_name):
    bots = load_bots()
    users = load_users()
    
    if username not in users:
        return False
    
    user = users[username]
    
    # Check bot limit
    if len(user.get("bots", [])) >= user["bot_limit"]:
        return False
    
    bot_id = hashlib.md5(f"{username}{filename}{time.time()}".encode()).hexdigest()[:8]
    language = detect_language(filename)
    
    bot_data = {
        "id": bot_id,
        "name": original_name,
        "filename": filename,
        "username": username,
        "language": language,
        "status": "stopped",
        "pid": None,
        "created_at": datetime.now().isoformat(),
        "last_started": None,
        "cpu_usage": 0,
        "memory_usage": 0,
        "restart_count": 0,
        "log_file": f"{username}_{bot_id}.log"
    }
    
    bots[bot_id] = bot_data
    save_bots(bots)
    
    # Add to user's bot list
    if "bots" not in user:
        user["bots"] = []
    user["bots"].append(bot_id)
    save_users(users)
    
    # Update stats
    stats = load_stats()
    stats["total_bots"] = len(bots)
    save_stats(stats)
    
    return bot_id

def start_bot(bot_id):
    bots = load_bots()
    
    if bot_id not in bots:
        return False
    
    bot = bots[bot_id]
    
    if bot["status"] == "running":
        return True
    
    bot_path = os.path.join(BOTS_DIR, bot["filename"])
    log_path = os.path.join(LOGS_DIR, bot["log_file"])
    
    if not os.path.exists(bot_path):
        return False
    
    # Create log file if not exists
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    
    try:
        if bot["language"] == "python":
            cmd = ["python3", bot_path]
        elif bot["language"] == "php":
            cmd = ["php", bot_path]
        elif bot["language"] == "node":
            cmd = ["node", bot_path]
        else:
            cmd = ["bash", bot_path]
        
        with open(log_path, 'a') as log_file:
            process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True
            )
        
        bot["pid"] = process.pid
        bot["status"] = "running"
        bot["last_started"] = datetime.now().isoformat()
        save_bots(bots)
        
        # Auto install dependencies for Python
        if bot["language"] == "python":
            threading.Thread(target=auto_install_dependencies, args=(bot_path, "python")).start()
        
        return True
    except Exception as e:
        print(f"Error starting bot: {e}")
        return False

def stop_bot(bot_id):
    bots = load_bots()
    
    if bot_id not in bots:
        return False
    
    bot = bots[bot_id]
    
    if bot["status"] != "running" or not bot["pid"]:
        bot["status"] = "stopped"
        save_bots(bots)
        return True
    
    try:
        process = psutil.Process(bot["pid"])
        for child in process.children(recursive=True):
            child.terminate()
        process.terminate()
        process.wait(timeout=5)
    except:
        try:
            os.kill(bot["pid"], 9)
        except:
            pass
    
    bot["status"] = "stopped"
    bot["pid"] = None
    save_bots(bots)
    
    return True

def get_bot_logs(bot_id, lines=100):
    bots = load_bots()
    
    if bot_id not in bots:
        return ""
    
    bot = bots[bot_id]
    log_path = os.path.join(LOGS_DIR, bot["log_file"])
    
    if not os.path.exists(log_path):
        return "No logs available"
    
    try:
        with open(log_path, 'r') as f:
            content = f.readlines()
        return "".join(content[-lines:])
    except:
        return "Error reading logs"

# -------------------------------
# ROUTES
# -------------------------------
@app.route('/')
def index():
    if session.get('logged_in'):
        return redirect('/dashboard')
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect('/dashboard')
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if username == 'admin':
            config = load_config()
            if password == config.get('admin_password', 'admin123'):
                session['logged_in'] = True
                session['username'] = 'admin'
                session['is_admin'] = True
                flash('Logged in as admin successfully!', 'success')
                return redirect('/admin')
        
        success, user = authenticate_user(username, password)
        if success:
            session['logged_in'] = True
            session['username'] = username
            session['is_admin'] = user['is_admin']
            flash('Logged in successfully!', 'success')
            return redirect('/dashboard')
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if session.get('logged_in'):
        return redirect('/dashboard')
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not username or not email or not password:
            flash('All fields are required', 'error')
        elif password != confirm_password:
            flash('Passwords do not match', 'error')
        elif len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
        else:
            success, message = create_user(username, email, password)
            if success:
                flash('Account created successfully! Please login.', 'success')
                return redirect('/login')
            else:
                flash(message, 'error')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully', 'info')
    return redirect('/login')

@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect('/login')
    
    username = session['username']
    users = load_users()
    
    if username not in users and username != 'admin':
        session.clear()
        return redirect('/login')
    
    # Get user's bots
    user_bots = []
    bots = load_bots()
    
    if username == 'admin':
        user_bots = list(bots.values())
    else:
        user = users[username]
        for bot_id in user.get('bots', []):
            if bot_id in bots:
                user_bots.append(bots[bot_id])
    
    # Get stats
    stats = load_stats()
    
    return render_template('dashboard.html',
                         username=username,
                         is_admin=session.get('is_admin', False),
                         bots=user_bots,
                         stats=stats,
                         users_count=len(users))

@app.route('/upload', methods=['GET', 'POST'])
def upload_bot():
    if not session.get('logged_in'):
        return redirect('/login')
    
    username = session['username']
    
    if request.method == 'POST':
        if 'bot_file' not in request.files:
            flash('No file selected', 'error')
            return redirect('/upload')
        
        file = request.files['bot_file']
        bot_name = request.form.get('bot_name', '').strip() or file.filename
        
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect('/upload')
        
        # Check file extension
        allowed_ext = load_config().get('allowed_extensions', ['.py', '.php', '.js', '.txt', '.zip'])
        if not any(file.filename.lower().endswith(ext) for ext in allowed_ext):
            flash('File type not allowed', 'error')
            return redirect('/upload')
        
        # Save file
        filename = secure_filename(f"{username}_{int(time.time())}_{file.filename}")
        filepath = os.path.join(BOTS_DIR, filename)
        file.save(filepath)
        
        # Handle ZIP files
        if filename.lower().endswith('.zip'):
            try:
                extract_dir = os.path.join(BOTS_DIR, filename[:-4])
                os.makedirs(extract_dir, exist_ok=True)
                
                with zipfile.ZipFile(filepath, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Look for main files
                main_files = ['main.py', 'bot.py', 'index.php', 'app.js', 'server.js']
                for main_file in main_files:
                    if os.path.exists(os.path.join(extract_dir, main_file)):
                        filename = f"{filename[:-4]}/{main_file}"
                        break
                else:
                    # Use first Python/PHP/JS file found
                    for root, dirs, files in os.walk(extract_dir):
                        for f in files:
                            if f.endswith(('.py', '.php', '.js')):
                                filename = f"{filename[:-4]}/{f}"
                                break
                        break
                
                os.remove(filepath)
            except Exception as e:
                flash(f'Error extracting ZIP: {str(e)}', 'error')
                return redirect('/upload')
        
        # Create bot record
        bot_id = create_bot(username, filename, bot_name)
        
        if bot_id:
            flash(f'Bot uploaded successfully! ID: {bot_id}', 'success')
            
            # Auto-start if configured
            config = load_config()
            if config.get('auto_start_bots', False):
                start_bot(bot_id)
                flash('Bot started automatically', 'info')
        else:
            flash('Failed to upload bot. Check your bot limit.', 'error')
        
        return redirect('/dashboard')
    
    return render_template('upload.html')

@app.route('/start/<bot_id>')
def start_bot_route(bot_id):
    if not session.get('logged_in'):
        return redirect('/login')
    
    username = session['username']
    bots = load_bots()
    
    if bot_id not in bots:
        flash('Bot not found', 'error')
        return redirect('/dashboard')
    
    bot = bots[bot_id]
    
    # Check permission
    if username != 'admin' and bot['username'] != username:
        flash('Access denied', 'error')
        return redirect('/dashboard')
    
    if start_bot(bot_id):
        flash('Bot started successfully', 'success')
    else:
        flash('Failed to start bot', 'error')
    
    return redirect('/dashboard')

@app.route('/stop/<bot_id>')
def stop_bot_route(bot_id):
    if not session.get('logged_in'):
        return redirect('/login')
    
    username = session['username']
    bots = load_bots()
    
    if bot_id not in bots:
        flash('Bot not found', 'error')
        return redirect('/dashboard')
    
    bot = bots[bot_id]
    
    # Check permission
    if username != 'admin' and bot['username'] != username:
        flash('Access denied', 'error')
        return redirect('/dashboard')
    
    if stop_bot(bot_id):
        flash('Bot stopped successfully', 'success')
    else:
        flash('Failed to stop bot', 'error')
    
    return redirect('/dashboard')

@app.route('/restart/<bot_id>')
def restart_bot_route(bot_id):
    if not session.get('logged_in'):
        return redirect('/login')
    
    username = session['username']
    bots = load_bots()
    
    if bot_id not in bots:
        flash('Bot not found', 'error')
        return redirect('/dashboard')
    
    bot = bots[bot_id]
    
    # Check permission
    if username != 'admin' and bot['username'] != username:
        flash('Access denied', 'error')
        return redirect('/dashboard')
    
    stop_bot(bot_id)
    time.sleep(2)
    start_bot(bot_id)
    
    flash('Bot restarted successfully', 'success')
    return redirect('/dashboard')

@app.route('/delete/<bot_id>')
def delete_bot_route(bot_id):
    if not session.get('logged_in'):
        return redirect('/login')
    
    username = session['username']
    bots = load_bots()
    
    if bot_id not in bots:
        flash('Bot not found', 'error')
        return redirect('/dashboard')
    
    bot = bots[bot_id]
    
    # Check permission
    if username != 'admin' and bot['username'] != username:
        flash('Access denied', 'error')
        return redirect('/dashboard')
    
    # Stop bot if running
    if bot['status'] == 'running':
        stop_bot(bot_id)
    
    # Remove bot file
    bot_path = os.path.join(BOTS_DIR, bot['filename'])
    if os.path.exists(bot_path):
        # If it's a directory, remove the whole directory
        if '/' in bot['filename']:
            dir_path = os.path.dirname(bot_path)
            shutil.rmtree(dir_path, ignore_errors=True)
        else:
            os.remove(bot_path)
    
    # Remove log file
    log_path = os.path.join(LOGS_DIR, bot['log_file'])
    if os.path.exists(log_path):
        os.remove(log_path)
    
    # Remove from bots list
    del bots[bot_id]
    save_bots(bots)
    
    # Remove from user's bot list
    users = load_users()
    if bot['username'] in users:
        user = users[bot['username']]
        if 'bots' in user and bot_id in user['bots']:
            user['bots'].remove(bot_id)
            save_users(users)
    
    flash('Bot deleted successfully', 'success')
    return redirect('/dashboard')

@app.route('/logs/<bot_id>')
def view_logs(bot_id):
    if not session.get('logged_in'):
        return redirect('/login')
    
    username = session['username']
    bots = load_bots()
    
    if bot_id not in bots:
        flash('Bot not found', 'error')
        return redirect('/dashboard')
    
    bot = bots[bot_id]
    
    # Check permission
    if username != 'admin' and bot['username'] != username:
        flash('Access denied', 'error')
        return redirect('/dashboard')
    
    logs = get_bot_logs(bot_id,
