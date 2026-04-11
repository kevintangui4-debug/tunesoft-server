from flask import Flask, request, jsonify

app = Flask(__name__)

licenses = {
    "ABC123456789": {"hwid": None, "active": True},
    "TESTKEY999999": {"hwid": None, "active": True}
}

# 👇 AJOUTE ÇA ICI
@app.route("/")
def home():
    return "Server OK"

@app.route("/check", methods=["POST"])
def check():
    data = request.json
    key = data.get("key")
    hwid = data.get("hwid")

    if key not in licenses:
        return jsonify({"valid": False})

    lic = licenses[key]

    if lic["hwid"] is None:
        lic["hwid"] = hwid

    if lic["hwid"] != hwid:
        return jsonify({"valid": False})

    if not lic["active"]:
        return jsonify({"valid": False})

    return jsonify({"valid": True})

if __name__ == "__main__":
    import os
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
