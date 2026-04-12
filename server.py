from flask import Flask, request, jsonify
import uuid
import os
import json

app = Flask(__name__)

LICENSE_FILE = "licenses.json"

# =========================
# LOAD / SAVE
# =========================
def load_licenses():
    if os.path.exists(LICENSE_FILE):
        with open(LICENSE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_licenses(data):
    with open(LICENSE_FILE, "w") as f:
        json.dump(data, f, indent=4)

licenses = load_licenses()

# =========================
# GENERATE KEY
# =========================
def generate_key():
    return uuid.uuid4().hex[:12].upper()

# =========================
# HOME
# =========================
@app.route("/")
def home():
    return "Server OK"

# =========================
# GENERATE LICENSE
# =========================
@app.route("/generate", methods=["GET"])
def generate():
    key = generate_key()

    licenses[key] = {
        "hwid": None,
        "active": True
    }

    save_licenses(licenses)

    print("🆕 NEW KEY GENERATED:", key)

    return jsonify({"key": key})

# =========================
# CHECK LICENSE
# =========================
@app.route("/check", methods=["POST"])
def check():
    data = request.json
    key = data.get("key")
    hwid = data.get("hwid")

    print("---- REQUETE RECUE ----")
    print("KEY :", key)
    print("HWID :", hwid)

    if key not in licenses:
        print("❌ INVALID KEY")
        return jsonify({"valid": False})

    lic = licenses[key]

    # première activation
    if lic["hwid"] is None:
        lic["hwid"] = hwid
        save_licenses(licenses)
        print("🔐 FIRST ACTIVATION")

    if lic["hwid"] != hwid:
        print("❌ HWID DIFFERENT")
        return jsonify({"valid": False})

    if not lic["active"]:
        print("❌ LICENSE DISABLED")
        return jsonify({"valid": False})

    print("✅ VALID LICENSE")
    return jsonify({"valid": True})

# =========================
# START
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
