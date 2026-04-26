from flask import Flask, request, jsonify, render_template_string, redirect
import os
import sqlite3
import hashlib
import hmac
import time

# =========================
# 🔐 CONFIG
# =========================
ADMIN_KEY = os.environ.get("ADMIN_KEY", "CHANGE_ME")
SECRET_KEY = os.environ.get("SECRET_KEY", "SUPER_SECRET")
DB_FILE = "licenses.db"

app = Flask(__name__)

# =========================
# 📂 DB
# =========================
def get_db():
    conn = sqlite3.connect(DB_FILE)
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
# 🔑 UTIL
# =========================
def generate_key():
    return hashlib.sha256(os.urandom(64)).hexdigest()[:20].upper()

# =========================
# 🏠 HOME
# =========================
@app.route("/")
def home():
    return "TUNESOFT LICENSE SERVER OK"

# =========================
# 🔑 GENERATE (API ADMIN)
# =========================
@app.route("/generate", methods=["POST"])
def generate():
    if request.headers.get("X-API-KEY") != ADMIN_KEY:
        return jsonify({"error": "unauthorized"}), 403

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

    return jsonify({"key": key, "expires_at": expires})

# =========================
# 🔍 CHECK LICENSE
# =========================
@app.route("/check", methods=["POST"])
def check():
    data = request.json or {}

    key = data.get("key")
    hwid = data.get("hwid")
    timestamp = data.get("timestamp")
    signature = data.get("signature")

    if not key or not hwid or not timestamp or not signature:
        return jsonify({"valid": False, "reason": "missing_data"})

    try:
        timestamp = int(timestamp)
    except:
        return jsonify({"valid": False, "reason": "bad_timestamp"})

    # anti replay
    if abs(time.time() - timestamp) > 30:
        return jsonify({"valid": False, "reason": "replay"})

    # signature check
    payload = hwid + str(timestamp)

    expected = hmac.new(
        SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        return jsonify({"valid": False, "reason": "bad_signature"})

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

    if time.time() > expires_at:
        return jsonify({"valid": False, "reason": "expired"})

    # first bind
    if db_hwid is None:
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE licenses SET hwid=? WHERE key=?", (hwid, key))
        conn.commit()
        conn.close()
        return jsonify({"valid": True, "first_activation": True})

    if db_hwid != hwid:
        return jsonify({"valid": False, "reason": "hwid_mismatch"})

    if not active:
        return jsonify({"valid": False, "reason": "disabled"})

    return jsonify({"valid": True})

# =========================
# 🔥 ADMIN DASHBOARD WEB
# =========================
ADMIN_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>TUNESOFT ADMIN</title>
    <style>
        body { background:#111; color:white; font-family:Arial; }
        table { width:100%; margin-top:20px; border-collapse: collapse; }
        th, td { border:1px solid #333; padding:10px; text-align:center; }
        button { padding:6px; background:#007acc; color:white; border:none; cursor:pointer; }
    </style>
</head>
<body>

<h1>🔥 TUNESOFT ADMIN PANEL</h1>

<form method="POST" action="/admin/generate">
    <button>➕ Générer clé</button>
</form>

<table>
<tr>
<th>KEY</th><th>HWID</th><th>ACTIVE</th><th>EXPIRES</th><th>ACTION</th>
</tr>

{% for l in licenses %}
<tr>
<td>{{l['key']}}</td>
<td>{{l['hwid']}}</td>
<td>{{l['active']}}</td>
<td>{{l['expires_at']}}</td>
<td>
    <a href="/admin/ban/{{l['key']}}">
        <button style="background:red;">BAN</button>
    </a>
</td>
</tr>
{% endfor %}

</table>

</body>
</html>
"""

# =========================
# ADMIN SECURITY
# =========================
def auth():
    return request.headers.get("X-ADMIN-KEY") == ADMIN_KEY

# =========================
# ADMIN PAGE
# =========================
@app.route("/admin")
def admin():
    if not auth():
        return "Unauthorized", 403

    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM licenses")
    licenses = c.fetchall()
    conn.close()

    return render_template_string(ADMIN_HTML, licenses=licenses)

# =========================
# ADMIN GENERATE
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

    return redirect("/admin")

# =========================
# BAN LICENSE
# =========================
@app.route("/admin/ban/<key>")
def ban(key):
    if not auth():
        return "Unauthorized", 403

    conn = get_db()
    c = conn.cursor()
    c.execute("UPDATE licenses SET active=0 WHERE key=?", (key,))
    conn.commit()
    conn.close()

    return redirect("/admin")

# =========================
# 🚀 RUN
# =========================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
