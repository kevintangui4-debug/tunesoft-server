from flask import Flask, request, jsonify

app = Flask(__name__)

# 🔐 Base de données simple (tu peux remplacer par SQL plus tard)
licenses = {
    "ABC123456789": {"hwid": None, "active": True},
    "TESTKEY999999": {"hwid": None, "active": True}
}

@app.route("/check", methods=["POST"])
def check():
    data = request.json
    key = data.get("key")
    hwid = data.get("hwid")

    if key not in licenses:
        return jsonify({"valid": False})

    lic = licenses[key]

    # 🔒 Première activation
    if lic["hwid"] is None:
        lic["hwid"] = hwid

    # 🔒 Vérification HWID
    if lic["hwid"] != hwid:
        return jsonify({"valid": False})

    # 🔒 Vérification active
    if not lic["active"]:
        return jsonify({"valid": False})

    return jsonify({"valid": True})

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
