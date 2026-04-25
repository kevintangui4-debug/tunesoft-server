from flask import Flask, request, jsonify
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
# 📂 INIT DB
# =========================
def init_db():
    conn = sqlite3.connect(DB_FILE)
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
# 🏠 HOME
# =========================
@app.route("/")
def home():
    return "Server OK"

# =========================
# 🔑 GENERATE LICENSE
# =========================
def generate_key():
    return hashlib.sha256(os.urandom(32)).hexdigest()[:20].upper()

@app.route("/generate", methods=["POST"])
def generate():
    if request.headers.get("X-API-KEY") != ADMIN_KEY:
        return jsonify({"error": "Unauthorized"}), 403

    key = generate_key()

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    expires_at = int(time.time()) + 30 * 24 * 3600

    c.execute("""
        INSERT INTO licenses (key, hwid, active, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?)
    """, (key, None, 1, int(time.time()), expires_at))

    conn.commit()
    conn.close()

    return jsonify({"key": key})

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
        return jsonify({"valid": False})

    try:
        timestamp = int(timestamp)
    except:
        return jsonify({"valid": False})

    # ⏱ anti replay
    if abs(time.time() - timestamp) > 30:
        return jsonify({"valid": False})

    # 🔐 signature check
    payload = hwid + str(timestamp)

    expected_sig = hmac.new(
        SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, signature):
        return jsonify({"valid": False})

    hwid_hash = hashlib.sha256(hwid.strip().encode()).hexdigest()

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT hwid, active, expires_at FROM licenses WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({"valid": False})

    db_hwid, active, expires_at = row

    # 🔐 first bind
    if db_hwid is None:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("UPDATE licenses SET hwid=? WHERE key=?", (hwid_hash, key))
        conn.commit()
        conn.close()
        db_hwid = hwid_hash

    if db_hwid != hwid_hash:
        return jsonify({"valid": False})

    if not active:
        return jsonify({"valid": False})

    if time.time() > expires_at:
        return jsonify({"valid": False})

    return jsonify({"valid": True})

# =========================
# 🚀 RUN
# =========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
