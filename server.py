from flask import Flask, request, jsonify
import sqlite3
import time
import os
import hashlib

app = Flask(__name__)

# =========================
# CONFIG
# =========================
ADMIN_KEY = os.environ.get("ADMIN_KEY", "CHANGE_ME")

# =========================
# DATABASE
# =========================
def get_db():
    conn = sqlite3.connect("licenses.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS licenses (
            key TEXT PRIMARY KEY,
            hwid TEXT,
            active INTEGER,
            created_at INTEGER,
            expires_at INTEGER
        )
    """)

    conn.commit()
    conn.close()

init_db()

# =========================
# KEY GENERATOR
# =========================
def generate_key():
    return hashlib.sha256(os.urandom(64)).hexdigest()[:20].upper()

# =========================
# AUTH ADMIN
# =========================
def auth():
    return request.headers.get("X-ADMIN-KEY") == ADMIN_KEY

# =========================
# HOME
# =========================
@app.route("/")
def home():
    return "TUNESOFT SERVER OK"

# =========================
# CHECK LICENSE (CLIENT)
# =========================
@app.route("/check", methods=["POST"])
def check():
    data = request.json or {}

    key = data.get("key")
    hwid = data.get("hwid")

    if not key or not hwid:
        return jsonify({"valid": False, "reason": "missing_data"})

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT hwid, active, expires_at FROM licenses WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({"valid": False, "reason": "invalid_key"})

    db_hwid = row["hwid"]
    active = row["active"]
    expires_at = row["expires_at"]

    now = time.time()

    # expiration
    if now > expires_at:
        return jsonify({"valid": False, "reason": "expired"})

    # disabled
    if active == 0:
        return jsonify({"valid": False, "reason": "disabled"})

    # first activation (bind HWID)
    if db_hwid is None:
        conn = get_db()
        c = conn.cursor()
        c.execute(
            "UPDATE licenses SET hwid=? WHERE key=?",
            (hwid, key)
        )
        conn.commit()
        conn.close()

        return jsonify({"valid": True, "first_activation": True})

    # HWID mismatch
    if db_hwid != hwid:
        return jsonify({"valid": False, "reason": "hwid_mismatch"})

    return jsonify({"valid": True})

# =========================
# ADMIN PANEL
# =========================
@app.route("/admin")
def admin():
    if not auth():
        return "Unauthorized", 403

    return """
    <html>
    <body style="background:#111;color:white;font-family:Arial;text-align:center;padding-top:60px;">

        <h1>🔥 ADMIN PANEL</h1>

        <form method="POST" action="/admin/generate">
            <button style="padding:15px;background:#007acc;color:white;border:none;cursor:pointer;">
                ⚡ GENERER UNE CLE
            </button>
        </form>

    </body>
    </html>
    """

# =========================
# GENERATE KEY
# =========================
@app.route("/admin/generate", methods=["POST"])
def admin_generate():
    if not auth():
        return "Unauthorized", 403

    key = generate_key()
    now = int(time.time())
    expires = now + (30 * 24 * 3600)

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        INSERT INTO licenses (key, hwid, active, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?)
    """, (key, None, 1, now, expires))

    conn.commit()
    conn.close()

    return f"""
    <html>
    <body style="background:#111;color:white;font-family:Arial;text-align:center;padding-top:60px;">

        <h2>🔑 LICENCE GÉNÉRÉE</h2>

        <input id="key" value="{key}" readonly
            style="padding:10px;width:350px;text-align:center;" />

        <br><br>

        <button onclick="copyKey()"
            style="padding:10px 20px;background:#00c853;color:white;border:none;cursor:pointer;">
            📋 COPIER + RETOUR
        </button>

        <script>
        function copyKey() {{
            let k = document.getElementById("key");
            k.select();
            document.execCommand("copy");

            setTimeout(() => {{
                window.location.href = "/admin";
            }}, 800);
        }}
        </script>

    </body>
    </html>
    """

# =========================
# RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
