from flask import Flask, request, jsonify
import time
import sqlite3

app = Flask(__name__)  # ✅ OBLIGATOIRE EN PREMIER

def get_db():
    conn = sqlite3.connect("licenses.db")
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def home():
    return "OK"

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

    if row is None:
        return jsonify({"valid": False, "reason": "invalid_key"})

    db_hwid = row["hwid"]
    active = row["active"]
    expires_at = row["expires_at"]

    if time.time() > expires_at:
        return jsonify({"valid": False, "reason": "expired"})

    if active == 0:
        return jsonify({"valid": False, "reason": "disabled"})

    if db_hwid is None:
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE licenses SET hwid=? WHERE key=?", (hwid, key))
        conn.commit()
        conn.close()
        return jsonify({"valid": True, "first_activation": True})

    if db_hwid != hwid:
        return jsonify({"valid": False, "reason": "hwid_mismatch"})

    return jsonify({"valid": True})
