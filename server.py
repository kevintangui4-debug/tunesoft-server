from flask import Flask, request, jsonify
import uuid
import os
import json

# =========================
# 🔐 CONFIG
# =========================
ADMIN_KEY = "TUNESOFT_SECURE_2026"
LICENSE_FILE = "licenses.json"

app = Flask(__name__)

# =========================
# 📂 LOAD / SAVE LICENSES
# =========================
def load_licenses():
    if os.path.exists(LICENSE_FILE):
        with open(LICENSE_FILE, "r") as f:
            return json.load(f)

    return {
        "ABC123456789": {"hwid": None, "active": True}
    }

def save_licenses(data):
    with open(LICENSE_FILE, "w") as f:
        json.dump(data, f, indent=4)

licenses = load_licenses()

# =========================
# 🔑 GENERATE KEY
# =========================
def generate_key():
    return uuid.uuid4().hex[:12].upper()

# =========================
# 🏠 HOME
# =========================
@app.route("/")
def home():
    return "Server OK"

# =========================
# 🔐 GENERATE LICENSE
# =========================
@app.route("/generate", methods=["GET"])
def generate():
    admin = request.args.get("admin")

    if admin != ADMIN_KEY:
        return jsonify({"error": "Unauthorized"}), 403

    key = generate_key()

    licenses[key] = {
        "hwid": None,
        "active": True
    }

    save_licenses(licenses)

    print("🆕 NEW KEY:", key)

    return jsonify({"key": key})

# =========================
# 🔄 RESET LICENSE (TRÈS IMPORTANT)
# =========================
@app.route("/reset", methods=["GET"])
def reset():
    admin = request.args.get("admin")
    key = request.args.get("key")

    if admin != ADMIN_KEY:
        return jsonify({"error": "Unauthorized"}), 403

    if key not in licenses:
        return jsonify({"error": "Key not found"}), 404

    licenses[key]["hwid"] = None
    save_licenses(licenses)

    print("♻️ RESET:", key)

    return jsonify({"status": "reset OK"})

# =========================
# 🔍 CHECK LICENSE
# =========================
@app.route("/check", methods=["POST"])
def check():
    data = request.json
    key = data.get("key")
    hwid = data.get("hwid")

    print("KEY:", key, "| HWID:", hwid)

    if key not in licenses:
        return jsonify({"valid": False})

    lic = licenses[key]

    if lic["hwid"] is None:
        lic["hwid"] = hwid
        save_licenses(licenses)

    if lic["hwid"] != hwid:
        return jsonify({"valid": False})

    if not lic["active"]:
        return jsonify({"valid": False})

    return jsonify({"valid": True})

# =========================
# 🚀 START
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
