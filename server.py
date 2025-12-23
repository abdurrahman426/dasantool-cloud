from flask import Flask, request, jsonify
import json
from cryptography.fernet import Fernet
import threading
import telebot
import time
import os

app = Flask(__name__)

# CONFIG
API_TOKEN = '8089084583:AAHHYvq8WXmIXZselYprCFtiiszZZ6T1Y_0'
CHAT_ID = '5832287311'
FERNET_KEY = b'hTVbf272VnKlIAvorIfqJF_qrz_9CDyFSlCKDsThH8Q='
AUTH_FILE = 'auth_list.json'

fernet = Fernet(FERNET_KEY)
bot = telebot.TeleBot(API_TOKEN)

def load_auth():
    """Load authorized devices from encrypted JSON"""
    if not os.path.exists(AUTH_FILE):
        return []
    try:
        with open(AUTH_FILE, 'rb') as f:
            encrypted_data = f.read()
            decrypted = fernet.decrypt(encrypted_data)
            return json.loads(decrypted.decode('utf-8'))
    except Exception as e:
        print(f"Load auth error: {e}")
        return []

def save_auth(devices):
    """Save authorized devices to encrypted JSON"""
    try:
        data = json.dumps(devices, indent=2).encode('utf-8')
        encrypted_data = fernet.encrypt(data)
        with open(AUTH_FILE, 'wb') as f:
            f.write(encrypted_data)
        print(f"Saved {len(devices)} devices to {AUTH_FILE}")
    except Exception as e:
        print(f"Save auth error: {e}")

@app.route('/status', methods=['POST'])
def report_status():
    """PC client reports status"""
    try:
        data = request.json
        session_id = data.get("session_id")
        hostname = data.get("hostname", "Unknown")
        
        print(f"📱 PC report: {session_id} from {hostname}")
        
        auth_list = load_auth()
        is_authorized = any(d["session_id"] == session_id for d in auth_list)
        
        if is_authorized:
            bot.send_message(CHAT_ID, f"✅ Service active: {session_id}")
            return jsonify({"status": "authorized"}), 200
        
        # New unauthorized device
        if not hasattr(app, 'pending_sessions'):
            app.pending_sessions = set()
        
        if session_id not in app.pending_sessions:
            app.pending_sessions.add(session_id)
            
            message = (
                f"🚫 Unauthorized Dasantool xpon!\n\n"
                f"Device ID: `{session_id}`\n"
                f"PC: {hostname}\n"
                f"Product: {data.get('product_id', 'N/A')}\n"
                f"Serial: {data.get('serial', 'N/A')}\n"
                f"OS: {data.get('os', 'N/A')}\n\n"
                f"**Reply:**\n`1:{session_id}` authorize\n`2:{session_id}` unauthorize"
            )
            bot.send_message(CHAT_ID, message, parse_mode='Markdown')
        
        return jsonify({"status": "pending"}), 200
        
    except Exception as e:
        print(f"Report error: {e}")
        return jsonify({"status": "error"}), 500

@app.route('/status/<session_id>', methods=['GET'])
def check_authorization(session_id):
    """PC checks authorization status"""
    auth_list = load_auth()
    is_authorized = any(d["session_id"] == session_id for d in auth_list)
    status = "authorized" if is_authorized else "unauthorized"
    
    print(f"🔍 Status check: {session_id} -> {status}")
    return jsonify({"status": status})

@bot.message_handler(func=lambda m: True)
def handle_telegram_reply(message):
    """Handle Telegram authorization replies"""
    if message.chat.id != int(CHAT_ID):
        return
        
    text = message.text.strip()
    print(f"📨 Telegram: {text}")
    
    if ':' not in text:
        return
        
    try:
        cmd, session_id = text.split(':', 1)
        cmd = cmd.strip()
        session_id = session_id.strip()
        
        auth_list = load_auth()
        
        if cmd == '1':
            if not any(d["session_id"] == session_id for d in auth_list):
                auth_list.append({"session_id": session_id, "authorized_at": time.time()})
                save_auth(auth_list)
                bot.reply_to(message, f"✅ Authorized: `{session_id}`", parse_mode='Markdown')
                if hasattr(app, 'pending_sessions'):
                    app.pending_sessions.discard(session_id)
            else:
                bot.reply_to(message, f"ℹ️ Already authorized: `{session_id}`", parse_mode='Markdown')
                
        elif cmd == '2':
            auth_list = [d for d in auth_list if d["session_id"] != session_id]
            save_auth(auth_list)
            bot.reply_to(message, f"❌ Unauthorized: `{session_id}`", parse_mode='Markdown')
            
    except Exception as e:
        print(f"Telegram handler error: {e}")
        bot.reply_to(message, "❌ Invalid format. Use: `1:device_id` or `2:device_id`")

def telegram_bot_loop():
    """Keep Telegram bot alive"""
    print("🤖 Telegram bot started")
    while True:
        try:
            bot.infinity_polling(none_stop=True, timeout=10)
        except Exception as e:
            print(f"⚠️ Bot restart: {e}")
            time.sleep(5)

if __name__ == '__main__':
    print("🚀 Dasantool Cloud Server Starting...")
    print("📱 PC URL: http://YOUR_IP:8000/status")
    print("💬 Telegram ready for 1:device_id / 2:device_id")
    
    # Start Telegram bot in background
    bot_thread = threading.Thread(target=telegram_bot_loop, daemon=True)
    bot_thread.start()
    
    # Start Flask server
    app.run(host='0.0.0.0', port=8000, debug=False)
