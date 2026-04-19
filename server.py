from flask import Flask, request, jsonify
import json
import os
import uuid
import hashlib
from time import time

# =========================
# 🔐 CONFIG
# =========================
ADMIN_KEY = "TUNESOFT_SUPER_SECRET_8472"  # ✅ clé admin directe
LICENSE_FILE = "licenses.json"

app = Flask(__name__)

# =========================
# 🛡️ ANTI-SPAM
# =========================
last_requests = {}

@app.before_request
def limit_requests():
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    now = time()

    if ip in last_requests and now - last_requests[ip] < 0.3:
        return "Too many requests", 429

    last_requests[ip] = now

# =========================
# 📂 LOAD / SAVE
# =========================
def load_licenses():
    if os.path.exists(LICENSE_FILE):
        try:
            with open(LICENSE_FILE, "r") as f:
                data = f.read().strip()
                if not data:
                    return {}
                return json.loads(data)
        except:
            return {}
    return {}

def save_licenses(data):
    with open(LICENSE_FILE, "w") as f:
        json.dump(data, f, indent=4)

licenses = load_licenses()

# =========================
# 🔑 GENERATE KEY
# =========================
def generate_key():
    return uuid.uuid4().hex[:16].upper()

# =========================
# 🏠 HOME
# =========================
@app.route("/")
def home():
    return "Server OK"

# =========================
# 🔐 GENERATE LICENSE
# =========================
@app.route("/generate")
def generate():
    if request.args.get("admin") != ADMIN_KEY:
        return jsonify({"error": "Unauthorized"}), 403

    key = generate_key()

    licenses[key] = {
        "hwid": None,
        "active": True,
        "created_at": int(time())
    }

    save_licenses(licenses)

    return jsonify({"key": key})

# =========================
# 🔁 RESET LICENSE
# =========================
@app.route("/reset")
def reset():
    if request.args.get("admin") != ADMIN_KEY:
        return jsonify({"error": "Unauthorized"}), 403

    key = request.args.get("key")

    if key not in licenses or not isinstance(licenses[key], dict):
        return jsonify({"error": "Key not found"}), 404

    licenses[key]["hwid"] = None
    save_licenses(licenses)

    return jsonify({"status": "reset OK"})

# =========================
# ❌ DISABLE LICENSE
# =========================
@app.route("/disable")
def disable():
    if request.args.get("admin") != ADMIN_KEY:
        return jsonify({"error": "Unauthorized"}), 403

    key = request.args.get("key")

    if key not in licenses or not isinstance(licenses[key], dict):
        return jsonify({"error": "Key not found"}), 404

    licenses[key]["active"] = False
    save_licenses(licenses)

    return jsonify({"status": "disabled"})

# =========================
# 📋 LIST LICENSES
# =========================
@app.route("/licenses")
def list_licenses():
    if request.args.get("admin") != ADMIN_KEY:
        return jsonify({"error": "Unauthorized"}), 403

    return jsonify(licenses)

# =========================
# 🔍 CHECK LICENSE
# =========================
@app.route("/check", methods=["POST"])
def check():
    data = request.json

    if not data:
        return jsonify({"valid": False})

    key = data.get("key")
    hwid = data.get("hwid")

    if not key or not hwid:
        return jsonify({"valid": False})

    if key not in licenses or not isinstance(licenses[key], dict):
        return jsonify({"valid": False})

    lic = licenses[key]
    hwid_hash = hashlib.sha256(hwid.encode()).hexdigest()

    # 🔐 première activation
    if lic["hwid"] is None:
        lic["hwid"] = hwid_hash
        save_licenses(licenses)

    # 🔒 mauvais PC
    if lic["hwid"] != hwid_hash:
        return jsonify({"valid": False})

    # 🔒 licence désactivée
    if not lic.get("active", False):
        return jsonify({"valid": False})

    return jsonify({"valid": True})

# =========================
# 🚀 START
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
