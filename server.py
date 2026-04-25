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

    if abs(time.time() - timestamp) > 30:
        return jsonify({"valid": False})

    payload = hwid + str(timestamp)
    expected_sig = hmac.new(
        SECRET_KEY.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected_sig, signature):
        return jsonify({"valid": False})

    hwid_hash = hashlib.sha256(hwid.encode()).hexdigest()

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    c.execute("SELECT hwid, active, expires_at FROM licenses WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()

    if not row:
        return jsonify({"valid": False})

    db_hwid, active, expires_at = row

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
        return jsonify({"valid": False, "error": "expired"})

    return jsonify({"valid": True})
