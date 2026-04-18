from flask import Flask, request, jsonify
import json
import os
import uuid
import hashlib
from time import time

# =========================
# 🔐 CONFIG
# =========================
ADMIN_KEY = os.environ.get("ADMIN_KEY", "CHANGE_ME")  # ⚠️ à changer sur Render
LICENSE_FILE = "licenses.json"

app = Flask(__name__)

# =========================
# 🛡️ ANTI-SPAM SIMPLE
# =========================
last_requests = {}

@app.before_request
def limit_requests():
    ip = request.remote_addr
    now = time()

    if ip in last_requests and now - last_requests[ip] < 0.5:
        return "Too many requests", 429

    last_requests[ip] = now

# =========================
# 📂 LOAD / SAVE
# =========================
def load_licenses():
    if os.path.exists(LICENSE_FILE):
        try:
            with open(LICENSE_FILE, "r") as f:
                return json.load(f)
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
    raw = uuid.uuid4().hex[:16].upper()
    return raw

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
        "active": True,
        "created_at": int(time())
    }

    save_licenses(licenses)

    return jsonify({"key": key})

# =========================
# 🔁 RESET LICENSE
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

    return jsonify({"status": "reset OK"})

# =========================
# ❌ DISABLE LICENSE
# =========================
@app.route("/disable", methods=["GET"])
def disable():
    admin = request.args.get("admin")
    key = request.args.get("key")

    if admin != ADMIN_KEY:
        return jsonify({"error": "Unauthorized"}), 403

    if key not in licenses:
        return jsonify({"error": "Key not found"}), 404

    licenses[key]["active"] = False
    save_licenses(licenses)

    return jsonify({"status": "disabled"})

# =========================
# 📋 LIST LICENSES
# =========================
@app.route("/licenses", methods=["GET"])
def list_licenses():
    admin = request.args.get("admin")

    if admin != ADMIN_KEY:
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

    if key not in licenses:
        return jsonify({"valid": False})

    lic = licenses[key]

    # 🔐 première activation
    if lic["hwid"] is None:
        lic["hwid"] = hashlib.sha256(hwid.encode()).hexdigest()
        save_licenses(licenses)

    # 🔒 vérification HWID
    if lic["hwid"] != hashlib.sha256(hwid.encode()).hexdigest():
        return jsonify({"valid": False})

    # 🔒 licence désactivée
    if not lic["active"]:
        return jsonify({"valid": False})

    return jsonify({"valid": True})

# =========================
# 🧠 ADMIN PANEL
# =========================
@app.route("/admin")
def admin_panel():
    admin = request.args.get("admin")

    if admin != ADMIN_KEY:
        return "Accès refusé", 403

    return f"""
    <html>
    <head>
        <title>TUNESOFT ADMIN</title>
        <style>
            body {{
                font-family: Arial;
                background: #111;
                color: white;
                text-align: center;
                padding: 40px;
            }}
            input, button {{
                padding: 10px;
                margin: 5px;
                border-radius: 5px;
                border: none;
            }}
            button {{
                background: orange;
                cursor: pointer;
            }}
            .box {{
                background: #222;
                padding: 20px;
                margin: 20px;
                border-radius: 10px;
            }}
            pre {{
                background: black;
                padding: 10px;
                text-align: left;
                overflow-x: auto;
            }}
        </style>
    </head>
    <body>

        <h1>🔥 TUNESOFT ADMIN PANEL</h1>

        <div class="box">
            <h2>Générer une clé</h2>
            <button onclick="generate()">GÉNÉRER</button>
            <p id="newkey"></p>
        </div>

        <div class="box">
            <h2>Reset licence</h2>
            <input id="resetkey" placeholder="clé">
            <button onclick="reset()">RESET</button>
            <p id="resetresult"></p>
        </div>

        <div class="box">
            <h2>Désactiver licence</h2>
            <input id="disablekey" placeholder="clé">
            <button onclick="disableKey()">DISABLE</button>
            <p id="disableresult"></p>
        </div>

        <div class="box">
            <h2>Voir licences</h2>
            <button onclick="loadLicenses()">AFFICHER</button>
            <pre id="list"></pre>
        </div>

        <script>
        function generate() {{
            fetch('/generate?admin={ADMIN_KEY}')
            .then(r=>r.json())
            .then(d=>document.getElementById('newkey').innerText=d.key)
        }}

        function reset() {{
            let k=document.getElementById('resetkey').value;
            fetch(`/reset?key=${{k}}&admin={ADMIN_KEY}`)
            .then(r=>r.json())
            .then(d=>document.getElementById('resetresult').innerText=JSON.stringify(d))
        }}

        function disableKey() {{
            let k=document.getElementById('disablekey').value;
            fetch(`/disable?key=${{k}}&admin={ADMIN_KEY}`)
            .then(r=>r.json())
            .then(d=>document.getElementById('disableresult').innerText=JSON.stringify(d))
        }}

        function loadLicenses() {{
            fetch('/licenses?admin={ADMIN_KEY}')
            .then(r=>r.json())
            .then(d=>document.getElementById('list').innerText=JSON.stringify(d,null,2))
        }}
        </script>

    </body>
    </html>
    """

# =========================
# 🚀 START
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
