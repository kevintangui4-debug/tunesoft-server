from flask import Flask, request, jsonify
import sqlite3
import hashlib
import time
import secrets

app = Flask(__name__)
DB = "licenses.db"

# ---------- INIT DB ----------
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

# ---------- GENERER UNE LICENCE ----------
def generate_key():
    return "LIC-" + secrets.token_hex(8).upper()

@app.route("/create_license", methods=["POST"])
def create_license():
    data = request.json
    expires_days = data.get("days", 30)

    key = generate_key()
    expires = int(time.time()) + expires_days * 86400

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO licenses VALUES (?, ?, ?)", (key, None, expires))
    conn.commit()
    conn.close()

    return jsonify({"license": key, "expires": expires})

# ---------- ACTIVER LICENCE (lier HWID) ----------
@app.route("/activate", methods=["POST"])
def activate():
    data = request.json
    key = data.get("license")
    hwid = data.get("hwid")

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT hwid FROM licenses WHERE key=?", (key,))
    row = c.fetchone()

    if not row:
        return jsonify({"status": "invalid"}), 403

    stored_hwid = row[0]

    # première activation
    if stored_hwid is None:
        c.execute("UPDATE licenses SET hwid=? WHERE key=?", (hwid, key))
        conn.commit()
        return jsonify({"status": "activated"})

    # vérification HWID
    if stored_hwid != hwid:
        return jsonify({"status": "hwid_mismatch"}), 403

    return jsonify({"status": "valid"})

# ---------- CHECK LICENCE ----------
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

    if time.time() > expires:
        return jsonify({"status": "expired"}), 403

    if stored_hwid != hwid:
        return jsonify({"status": "hwid_mismatch"}), 403

    return jsonify({"status": "valid"})


app.run(host="0.0.0.0", port=5000)
