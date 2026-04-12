from flask import Flask, request, jsonify
import uuid
import os

app = Flask(__name__)

# 🔐 Base de licences
licenses = {
    "ABC123456789": {"hwid": None, "active": True},
    "TESTKEY999999": {"hwid": None, "active": True}
}

# =========================
# 🔑 GENERATE KEY
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
# 🔥 GENERATE LICENSE
# =========================
@app.route("/generate", methods=["GET"])
def generate():
    key = generate_key()

    licenses[key] = {
        "hwid": None,
        "active": True
    }

    print("🆕 NEW KEY GENERATED:", key)

    return jsonify({"key": key})

# =========================
# 🔐 CHECK LICENSE
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

    # 🔐 première activation
    if lic["hwid"] is None:
        lic["hwid"] = hwid
        print("🔐 FIRST ACTIVATION")

    # 🔒 mauvais PC
    if lic["hwid"] != hwid:
        print("❌ HWID DIFFERENT")
        return jsonify({"valid": False})

    # 🔒 licence désactivée
    if not lic["active"]:
        print("❌ LICENSE DISABLED")
        return jsonify({"valid": False})

    print("✅ VALID LICENSE")
    return jsonify({"valid": True})

# =========================
# START SERVER
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
