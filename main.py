from flask import Flask, render_template, request, redirect, session, jsonify
import os, json, time

app = Flask(__name__)
app.secret_key = "supersecretkey"

ADMIN_USER = "EclipseOwner"
ADMIN_PASS = "Secret123"

# Database paths
DB_KEYS = "database/keys.json"
DB_BLACKLIST = "database/blacklist.json"
DB_LOGS = "database/logs.txt"

# Ensure DB exists
os.makedirs("database", exist_ok=True)
for f in [DB_KEYS, DB_BLACKLIST]:
    if not os.path.exists(f):
        with open(f, "w") as x:
            x.write("{}")

if not os.path.exists(DB_LOGS):
    open(DB_LOGS, "w").close()

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def log_event(text):
    with open(DB_LOGS, "a") as f:
        f.write(f"[{time.ctime()}] {text}\n")


# ---------------- LOGIN ---------------- #

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")

        if u == ADMIN_USER and p == ADMIN_PASS:
            session["auth"] = True
            return redirect("/dashboard")
        return render_template("login.html", error="Invalid Credentials")

    return render_template("login.html")

def require_auth():
    return session.get("auth", False)


# ---------------- DASHBOARD ---------------- #

@app.route("/dashboard")
def dashboard():
    if not require_auth():
        return redirect("/")
    return render_template("dashboard.html")


# ---------------- KEY SYSTEM ---------------- #

@app.route("/keys")
def keys():
    if not require_auth():
        return redirect("/")

    data = load_json(DB_KEYS)
    return render_template("keys.html", keys=data)


@app.route("/generate", methods=["POST"])
def generate_key():
    if not require_auth():
        return redirect("/")

    days = int(request.form.get("days"))
    amount = int(request.form.get("amount"))

    keys = load_json(DB_KEYS)
    expire = int(time.time()) + (days * 86400)

    import random, string

    new_keys = []
    for i in range(amount):
        k = ''.join(random.choices(string.ascii_uppercase + string.digits, k=25))
        keys[k] = {"expires": expire, "hwid": None}
        new_keys.append(k)

    save_json(DB_KEYS, keys)
    log_event(f"Generated {amount} keys")

    return render_template("keys.html", keys=keys, new_keys=new_keys)


@app.route("/deletekey/<key>")
def delete_key(key):
    if not require_auth():
        return redirect("/")

    keys = load_json(DB_KEYS)
    keys.pop(key, None)
    save_json(DB_KEYS, keys)
    log_event(f"Deleted key {key}")

    return redirect("/keys")


# ---------------- BLACKLIST ---------------- #

@app.route("/blacklist")
def blacklist():
    if not require_auth():
        return redirect("/")

    bl = load_json(DB_BLACKLIST)
    return render_template("blacklist.html", black=bl)


@app.route("/addblacklist", methods=["POST"])
def add_black():
    if not require_auth():
        return redirect("/")

    hwid = request.form.get("hwid")
    bl = load_json(DB_BLACKLIST)

    bl[hwid] = True
    save_json(DB_BLACKLIST, bl)
    log_event(f"Blacklisted HWID {hwid}")

    return redirect("/blacklist")


@app.route("/removeblacklist/<hwid>")
def remove_black(hwid):
    if not require_auth():
        return redirect("/")

    bl = load_json(DB_BLACKLIST)
    bl.pop(hwid, None)
    save_json(DB_BLACKLIST, bl)
    log_event(f"Removed HWID {hwid}")

    return redirect("/blacklist")


# ---------------- LOGS ---------------- #

@app.route("/logs")
def logs():
    if not require_auth():
        return redirect("/")

    with open(DB_LOGS, "r") as f:
        content = f.read()

    return render_template("logs.html", logs=content)


# ---------------- ROBLOX API ---------------- #

@app.route("/check")
def check():
    key = request.args.get("key")
    hwid = request.args.get("hwid")

    keys = load_json(DB_KEYS)
    black = load_json(DB_BLACKLIST)

    # blacklisted
    if hwid in black:
        return jsonify({"success": False, "reason": "Blacklisted"})

    # invalid
    if key not in keys:
        return jsonify({"success": False, "reason": "Invalid key"})

    entry = keys[key]
    if entry["expires"] < time.time():
        return jsonify({"success": False, "reason": "Key expired"})

    # auto whitelist
    if entry["hwid"] is None:
        entry["hwid"] = hwid
        save_json(DB_KEYS, keys)
        log_event(f"Key {key} HWID-Bound to {hwid}")

    # wrong hwid
    if entry["hwid"] != hwid:
        return jsonify({"success": False, "reason": "HWID mismatch"})

    # SUCCESS → updated script URL
    return jsonify({
        "success": True,
        "loadstring": "https://raw.githubusercontent.com/FwtysLuas/EclipseMeteor/refs/heads/main/Protected_8387035221277894.lua.txt"
    })


# ---------------- KEEP ALIVE ---------------- #

@app.route("/ping")
def ping():
    return "alive", 200


# ---------------- RUN ---------------- #

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
