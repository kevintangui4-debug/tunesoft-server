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

    # expiration
    if time.time() > expires_at:
        return jsonify({"valid": False, "reason": "expired"})

    # first activation
    if db_hwid is None:
        conn = get_db()
        c = conn.cursor()
        c.execute("UPDATE licenses SET hwid=? WHERE key=?", (hwid, key))
        conn.commit()
        conn.close()
        return jsonify({"valid": True, "first_activation": True})

    # HWID mismatch
    if db_hwid != hwid:
        return jsonify({"valid": False, "reason": "hwid_mismatch"})

    # désactivé
    if not active:
        return jsonify({"valid": False, "reason": "disabled"})

    return jsonify({"valid": True})
