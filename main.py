from flask import Flask, render_template, request, redirect, session, jsonify
import os, json, time

app = Flask(__name__)
app.secret_key = "supersecretkey"

ADMIN_USER = "EclipseOwner"
ADMIN_PASS = "Secret123"

# Ensure folders exist
if not os.path.exists("database"):
    os.makedirs("database")

DB_KEYS = "database/keys.json"
DB_HWIDS = "database/hwids.json"
DB_BLACKLIST = "database/blacklist.json"
DB_LOGS = "database/logs.txt"

# Create missing files
for f in [DB_KEYS, DB_HWIDS, DB_BLACKLIST]:
    if not os.path.exists(f):
        with open(f, "w") as x:
            x.write("{}")

if not os.path.exists(DB_LOGS):
    open(DB_LOGS, "w").close()

# Load/save json
def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def log_event(msg):
    with open(DB_LOGS, "a") as f:
        f.write(f"[{time.ctime()}] {msg}\n")


# ---------------- LOGIN ----------------

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == ADMIN_USER and request.form["password"] == ADMIN_PASS:
            session["auth"] = True
            return redirect("/dashboard")
        return render_template("login.html", error="Invalid login")
    return render_template("login.html")


def require_auth():
    return session.get("auth", False)


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():
    if not require_auth():
        return redirect("/")
    return render_template("dashboard.html")


# ---------------- KEY MANAGER ----------------

@app.route("/keys")
def keys():
    if not require_auth():
        return redirect("/")
    return render_template("keys.html", keys=load_json(DB_KEYS))

@app.route("/generate", methods=["POST"])
def generate():
    if not require_auth():
        return redirect("/")

    days = int(request.form["days"])
    amount = int(request.form["amount"])

    keys = load_json(DB_KEYS)
    expire = int(time.time()) + days * 86400

    import random, string
    new_keys = []

    for _ in range(amount):
        k = "".join(random.choices(string.ascii_uppercase + string.digits, k=25))
        keys[k] = {"expires": expire, "hwid": None}
        new_keys.append(k)

    save_json(DB_KEYS, keys)
    log_event(f"Generated {amount} keys")
    return render_template("keys.html", keys=keys, new_keys=new_keys)


@app.route("/deletekey/<key>")
def delkey(key):
    if not require_auth():
        return redirect("/")
    keys = load_json(DB_KEYS)
    keys.pop(key, None)
    save_json(DB_KEYS, keys)
    log_event(f"Deleted key {key}")
    return redirect("/keys")


# ---------------- BLACKLIST ----------------

@app.route("/blacklist")
def blacklist():
    if not require_auth():
        return redirect("/")
    return render_template("blacklist.html", black=load_json(DB_BLACKLIST))

@app.route("/addblacklist", methods=["POST"])
def add_blacklist():
    if not require_auth():
        return redirect("/")
    hwid = request.form["hwid"]
    black = load_json(DB_BLACKLIST)
    black[hwid] = True
    save_json(DB_BLACKLIST, black)
    log_event(f"Blacklisted HWID {hwid}")
    return redirect("/blacklist")


@app.route("/removeblacklist/<hwid>")
def rm_blacklist(hwid):
    if not require_auth():
        return redirect("/")
    black = load_json(DB_BLACKLIST)
    black.pop(hwid, None)
    save_json(DB_BLACKLIST, black)
    log_event(f"Removed HWID {hwid}")
    return redirect("/blacklist")


# ---------------- LOGS PAGE ----------------

@app.route("/logs")
def logs_page():
    if not require_auth():
        return redirect("/")
    with open(DB_LOGS, "r") as f:
        logs = f.read()
    return render_template("logs.html", logs=logs)


# ---------------- ROBLOX API ----------------

@app.route("/check")
def check():
    key = request.args.get("key")
    hwid = request.args.get("hwid")

    keys = load_json(DB_KEYS)
    black = load_json(DB_BLACKLIST)

    if hwid in black:
        return jsonify({"success": False, "reason": "Blacklisted"})

    if key not in keys:
        return jsonify({"success": False, "reason": "Invalid key"})

    entry = keys[key]

    if entry["expires"] < time.time():
        return jsonify({"success": False, "reason": "Key expired"})

    if entry["hwid"] is None:
        entry["hwid"] = hwid
        save_json(DB_KEYS, keys)
        log_event(f"Auto-whitelisted HWID {hwid} for key {key}")

    if entry["hwid"] != hwid:
        return jsonify({"success": False, "reason": "HWID mismatch"})

    return jsonify({
        "success": True,
        "loadstring": "https://raw.githubusercontent.com/AsianTwchSecond/Loveu/refs/heads/main/stay.txt"
    })


# ---------------- START ----------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
