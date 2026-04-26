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
# 📂 DB INIT
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
# 🏠 HOME
# =========================
@app.route("/")
def home():
    return "TUNESOFT LICENSE SERVER OK"

# =========================
# 🔑 GENERATE LICENSE (ADMIN)
# =========================
def generate_key():
    return hashlib.sha256(os.urandom(64)).hexdigest()[:20].upper()

@app.route("/generate", methods=["POST"])
def generate():
    if request.headers.get("X-API-KEY") != ADMIN_KEY:
        return jsonify({"error": "unauthorized"}), 403

    key = generate_key()
    now = int(time.time())
    expires = now + (30 * 24 * 3600)  # 30 jours

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        INSERT INTO licenses (key, hwid, active, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?)
    """, (key, None, 1, now, expires))

    conn.commit()
    conn.close()

    return jsonify({
        "key": key,
        "expires_at": expires
    })

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

    # -------------------------
    # VALIDATION INPUT
    # -------------------------
    if not key or not hwid or not timestamp or not signature:
        return jsonify({"valid": False, "reason": "missing_data"})

    try:
        timestamp = int(timestamp)
    except:
        return jsonify({"valid": False, "reason": "bad_timestamp"})

    # -------------------------
    # ANTI REPLAY
    # -------------------------
    if abs(time.time() - timestamp) > 30:
        return jsonify({"valid": False, "reason": "replay_detected"})

    # -------------------------
    # SIGNATURE CHECK
    # -------------------------
    payload = hwid + str(timestamp)

    expected_sig = hmac.new(
        SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, signature):
        return jsonify({"valid": False, "reason": "bad_signature"})

    # -------------------------
    # LOAD LICENSE
    # -------------------------
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

    # -------------------------
    # EXPIRED
    # -------------------------
    if time.time() > expires_at:
        return jsonify({"valid": False, "reason": "expired"})

    # -------------------------
    # FIRST ACTIVATION
    # -------------------------
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

    # -------------------------
    # HWID CHECK
    # -------------------------
    if db_hwid != hwid:
        return jsonify({"valid": False, "reason": "hwid_mismatch"})

    # -------------------------
    # STATUS CHECK
    # -------------------------
    if not active:
        return jsonify({"valid": False, "reason": "disabled"})

    return jsonify({"valid": True})

# =========================
# 🚀 RUN
# =========================
if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
