from flask import Flask, request, jsonify
import sqlite3
import time
import secrets

app = Flask(__name__)
DB = "licenses.db"

# =========================
# 🧱 INIT DATABASE
# =========================
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS licenses (
        key TEXT PRIMARY KEY,
        hwid TEXT,
        expires INTEGER
    )
    """)
    conn.commit()
    conn.close()

init_db()

# =========================
# 🔑 GENERATE LICENSE
# =========================
def generate_key():
    return "LIC-" + secrets.token_hex(8).upper()

@app.route("/create_license", methods=["POST"])
def create_license():
    data = request.json
    days = data.get("days", 30)

    key = generate_key()
    expires = int(time.time()) + days * 86400

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO licenses VALUES (?, ?, ?)", (key, None, expires))
    conn.commit()
    conn.close()

    return jsonify({
        "license": key,
        "expires": expires
    })

# =========================
# 🔐 CHECK + AUTO BIND HWID
# =========================
@app.route("/check", methods=["POST"])
def check():
    data = request.json
    key = data.get("license")
    hwid = data.get("hwid")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT hwid, expires FROM licenses WHERE key=?", (key,))
    row = c.fetchone()

    if not row:
        return jsonify({"status": "invalid"}), 403

    stored_hwid, expires = row

    # ❌ expired
    if time.time() > expires:
        return jsonify({"status": "expired"}), 403

    # 🧠 FIRST TIME → AUTO BIND HWID
    if stored_hwid is None:
        c.execute("UPDATE licenses SET hwid=? WHERE key=?", (hwid, key))
        conn.commit()
        conn.close()
        return jsonify({"status": "valid"})

    # ❌ wrong machine
    if stored_hwid != hwid:
        conn.close()
        return jsonify({"status": "hwid_mismatch"}), 403

    conn.close()
    return jsonify({"status": "valid"})

# =========================
# 🚀 START SERVER
# =========================
app.run(host="0.0.0.0", port=5000)
