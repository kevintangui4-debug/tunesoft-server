from flask import Flask, request, jsonify
import json
import os
import uuid

# =========================
# 🔐 CONFIG
# =========================
ADMIN_KEY = "TUNESOFT_SECURE_2026"
LICENSE_FILE = "licenses.json"

app = Flask(__name__)

# =========================
# 📂 LOAD / SAVE
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
# 🔐 GENERATE LICENSE (ADMIN)
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

    return jsonify({"key": key})

# =========================
# 🔁 RESET LICENSE (ADMIN)
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
# 🔍 CHECK LICENSE
# =========================
@app.route("/check", methods=["POST"])
def check():
    data = request.json
    key = data.get("key")
    hwid = data.get("hwid")

    if key not in licenses:
        return jsonify({"valid": False})

    lic = licenses[key]

    # 🔐 première activation
    if lic["hwid"] is None:
        lic["hwid"] = hwid
        save_licenses(licenses)

    # ❌ mauvais PC
    if lic["hwid"] != hwid:
        return jsonify({"valid": False})

    # ❌ désactivée
    if not lic["active"]:
        return jsonify({"valid": False})

    return jsonify({"valid": True})

# =========================
# 🧠 ADMIN PANEL (WEB UI)
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
                border: none;
                border-radius: 5px;
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
            <input id="resetkey" placeholder="Entrer clé">
            <button onclick="reset()">RESET</button>
            <p id="resetresult"></p>
        </div>

        <script>
        function generate() {{
            fetch('/generate?admin={ADMIN_KEY}')
            .then(res => res.json())
            .then(data => {{
                document.getElementById('newkey').innerText = data.key;
            }});
        }}

        function reset() {{
            let key = document.getElementById('resetkey').value;

            fetch(`/reset?key=${{key}}&admin={ADMIN_KEY}`)
            .then(res => res.json())
            .then(data => {{
                document.getElementById('resetresult').innerText = JSON.stringify(data);
            }});
        }}
        </script>

    </body>
    </html>
    """

# =========================
# 🚀 START
# =========================
if __name__ == "__main__":
    app.run(port=5000)
