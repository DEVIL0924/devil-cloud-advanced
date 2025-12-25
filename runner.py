import psutil, json, subprocess, time, os, signal
from datetime import datetime

DATA_DIR = "data"
BOTS_FILE = os.path.join(DATA_DIR, "bots.json")
LOGS_DIR = "logs"

def monitor_bots():
    print("🔧 DEVIL CLOUD - Bot Monitor Started")
    
    while True:
        try:
            if not os.path.exists(BOTS_FILE):
                time.sleep(10)
                continue
            
            with open(BOTS_FILE, 'r') as f:
                bots = json.load(f)
            
            updated = False
            
            for bot_id, bot in list(bots.items()):
                if bot.get("status") == "running" and bot.get("pid"):
                    pid = bot["pid"]
                    
                    # Check if process is still running
                    if not psutil.pid_exists(pid):
                        print(f"⚠️ Bot {bot_id} crashed, restarting...")
                        
                        # Update status
                        bot["status"] = "stopped"
                        bot["pid"] = None
                        bots[bot_id] = bot
                        updated = True
                        
                        # Auto-restart
                        restart_bot(bot)
            
            if updated:
                with open(BOTS_FILE, 'w') as f:
                    json.dump(bots, f, indent=4)
            
            time.sleep(5)
            
        except Exception as e:
            print(f"❌ Monitor error: {e}")
            time.sleep(10)

def restart_bot(bot):
    """Restart a crashed bot"""
    try:
        bot_path = os.path.join("bots", bot["filename"])
        
        if not os.path.exists(bot_path):
            print(f"❌ Bot file not found: {bot_path}")
            return
        
        log_path = os.path.join(LOGS_DIR, bot.get("log_file", f"bot_{int(time.time())}.log"))
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        
        with open(log_path, 'a') as log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"\n[{timestamp}] 🔄 Bot auto-restarted\n")
            
            if bot["language"] == "python":
                cmd = ["python3", bot_path]
            elif bot["language"] == "php":
                cmd = ["php", bot_path]
            elif bot["language"] == "node":
                cmd = ["node", bot_path]
            else:
                cmd = ["bash", bot_path]
            
            process = subprocess.Popen(
                cmd,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                start_new_session=True
            )
        
        # Update bot data
        bot["status"] = "running"
        bot["pid"] = process.pid
        bot["last_started"] = datetime.now().isoformat()
        bot["restart_count"] = bot.get("restart_count", 0) + 1
        
        print(f"✅ Bot {bot.get('name', 'unknown')} restarted (PID: {process.pid})")
        
    except Exception as e:
        print(f"❌ Failed to restart bot: {e}")

if __name__ == "__main__":
    # Ensure directories exist
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    monitor_bots()
