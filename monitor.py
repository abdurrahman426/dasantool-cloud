import subprocess, os, requests, json, threading, time, platform
from cryptography.fernet import Fernet
import uuid

API_TOKEN = '8089084583:AAHHYvq8WXmIXZselYprCFtiiszZZ6T1Y_0'
CHAT_ID = '5832287311'
AUTH_FILE = "/tmp/mctcs.json"
encryption_key = b'hTVbf272VnKlIAvorIfqJF_qrz_9CDyFSlCKDsThH8Q='
fernet = Fernet(encryption_key)

def load_authorized_devices():
    if not os.path.exists(AUTH_FILE): return []
    try:
        with open(AUTH_FILE, "rb") as f: data = f.read()
        return json.loads(fernet.decrypt(data).decode())
    except: return []

def save_authorized_devices(devices):
    with open(AUTH_FILE, "wb") as f:
        f.write(fernet.encrypt(json.dumps(devices, indent=4).encode()))

def get_serial_number():
    try: 
        return subprocess.check_output("cat /sys/class/dmi/id/product_serial 2>/dev/null || hostname", shell=True).decode().strip()
    except: return "Unknown"

def get_pc_name(): return platform.node()
def get_product_id():
    try: 
        return subprocess.check_output("cat /sys/class/dmi/id/product_uuid 2>/dev/null || cat /etc/machine-id", shell=True).decode().strip()
    except: return "Unknown"

def get_os_info(): return f"{platform.system()} {platform.release()}"

def get_router_ip():
    try:
        lines = subprocess.check_output("ip route | grep default", shell=True).decode().splitlines()
        return lines[0].split()[-1] if lines else "Unknown"
    except: return "Unknown"

def get_network_info():
    try:
        public_ip = requests.get('https://api.ipify.org').text
        loc = requests.get(f"http://ip-api.com/json/{public_ip}").json()
        return public_ip, f"{loc.get('city')}, {loc.get('country')}", loc.get("isp", "Unknown")
    except: return "Unknown", "Unknown", "Unknown"

device_id = str(uuid.uuid4().hex[:12])
serial = get_serial_number()
hostname = get_pc_name()
product_id = get_product_id()
os_info = get_os_info()
router = get_router_ip()
public_ip, location, isp = get_network_info()

def send_telegram(status_text):
    msg = f"{status_text}\nDevice ID: {device_id}\nReply: 1 {device_id} authorize / 2 {device_id} unauthorize"
    requests.post(f"https://api.telegram.org/bot{API_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg})

# Initial notification
send_telegram("🚫 Unauthorized Dasantool xpon!")
reply_received = "unauthorized"

# LIVE LOOP
while True:
    devices = load_authorized_devices()
    status = next((d["status"] for d in devices if d["device_id"] == device_id), "unauthorized")
    
    if status == "authorized":
        print("Authorized")
        print(device_id)
        print("online")
    else:
        print("Unauthorized")
        print(device_id)
        print("offline")
    
    time.sleep(5)
