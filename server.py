from flask import Flask, request, jsonify
import uuid
import os
import json

# =========================
# 🔐 CONFIG
# =========================
ADMIN_KEY = "TUNESOFT_9xA$#2026_SECURE"
LICENSE_FILE = "licenses.json"

app = Flask(__name__)

# =========================
# 📂 LOAD / SAVE LICENSES
# =========================
def load_licenses():
    if os.path.exists(LICENSE_FILE):
        with open(LICENSE_FILE, "r") as f:
            return json.load(f)

    # 🔁 fallback si fichier absent
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
# 🔐 GENERATE LICENSE (ADMIN ONLY)
# =========================
@app.route("/generate", methods=["GET"])
def generate():
    admin = request.args.get("admin")

    # 🔒 protection admin
    if admin != ADMIN_KEY:
        print("❌ UNAUTHORIZED ACCESS")
        return jsonify({"error": "Unauthorized"}), 403

    key = generate_key()

    licenses[key] = {
        "hwid": None,
        "active": True
    }

    save_licenses(licenses)

    print("🆕 NEW KEY GENERATED:", key)

    return jsonify({"key": key})

# =========================
# 🔍 CHECK LICENSE
# =========================
@app.route("/check", methods=["POST"])
def check():
    data = request.json
    key = data.get("key")
    hwid = data.get("hwid")

    print("---- REQUETE RECUE ----")
    print("KEY :", key)
    print("HWID :", hwid)

    # ❌ clé inexistante
    if key not in licenses:
        print("❌ INVALID KEY")
        return jsonify({"valid": False})

    lic = licenses[key]

    # 🔐 première activation
    if lic["hwid"] is None:
        lic["hwid"] = hwid
        save_licenses(licenses)
        print("🔐 FIRST ACTIVATION")

    # ❌ mauvais PC
    if lic["hwid"] != hwid:
        print("❌ HWID DIFFERENT")
        return jsonify({"valid": False})

    # ❌ licence désactivée
    if not lic["active"]:
        print("❌ LICENSE DISABLED")
        return jsonify({"valid": False})

    print("✅ VALID LICENSE")
    return jsonify({"valid": True})

# =========================
# 🚀 START SERVER
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
