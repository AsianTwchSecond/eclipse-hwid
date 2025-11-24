from flask import Flask, render_template, request, redirect, session, jsonify
import os, json, time

app = Flask(__name__)
app.secret_key = "supersecretkey"   # change later

# Admin login
ADMIN_USER = "EclipseOwner"
ADMIN_PASS = "Secret123"

# Database folder
if not os.path.exists("database"):
    os.makedirs("database")

# Database files
DB_KEYS = "database/keys.json"
DB_HWIDS = "database/hwids.json"
DB_BLACKLIST = "database/blacklist.json"
DB_LOGS = "database/logs.txt"

# Ensure JSON files exist
for path in [DB_KEYS, DB_HWIDS, DB_BLACKLIST]:
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write("{}")

# Ensure logs exist
if not os.path.exists(DB_LOGS):
    open(DB_LOGS, "w").close()


# ------------------ JSON LOAD/SAVE ------------------ #

def load_json(path):
    with open(path, "r") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def log_event(text):
    with open(DB_LOGS, "a") as f:
        f.write(f"[{time.ctime()}] {text}\n")


# ------------------ LOGIN PAGE ------------------ #

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        pw = request.form.get("password")

        if user == ADMIN_USER and pw == ADMIN_PASS:
            session["auth"] = True
            return redirect("/dashboard")

        return render_template("login.html", error="Invalid login")

    return render_template("login.html")


def require_auth():
    return session.get("auth", False)


# ------------------ DASHBOARD ------------------ #

@app.route("/dashboard")
def dashboard():
    if not require_auth():
        return redirect("/")
    return render_template("dashboard.html")


# ------------------ KEY PAGE ------------------ #

@app.route("/keys")
def keys_page():
    if not require_auth():
        return redirect("/")

    keys = load_json(DB_KEYS)
    return render_template("keys.html", keys=keys)


@app.route("/generate", methods=["POST"])
def generate():
    if not require_auth():
        return redirect("/")

    days = int(request.form.get("days"))
    amount = int(request.form.get("amount"))

    keys = load_json(DB_KEYS)
    expire = int(time.time()) + days * 86400

    import random, string

    new_keys = []
    for _ in range(amount):
        key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=25))
        keys[key] = {"expires": expire, "hwid": None, "used": False}
        new_keys.append(key)

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


# ------------------ BLACKLIST ------------------ #

@app.route("/blacklist")
def blacklist_page():
    if not require_auth():
        return redirect("/")

    black = load_json(DB_BLACKLIST)
    return render_template("blacklist.html", black=black)


@app.route("/addblacklist", methods=["POST"])
def add_blacklist():
    if not require_auth():
        return redirect("/")

    hwid = request.form.get("hwid")
    black = load_json(DB_BLACKLIST)
    black[hwid] = True
    save_json(DB_BLACKLIST, black)

    log_event(f"Blacklisted HWID {hwid}")
    return redirect("/blacklist")


@app.route("/removeblacklist/<hwid>")
def remove_blacklist(hwid):
    if not require_auth():
        return redirect("/")

    black = load_json(DB_BLACKLIST)
    black.pop(hwid, None)
    save_json(DB_BLACKLIST, black)

    log_event(f"Removed HWID {hwid} from blacklist")
    return redirect("/blacklist")


# ------------------ LOG PAGE ------------------ #

@app.route("/logs")
def log_page():
    if not require_auth():
        return redirect("/")

    with open(DB_LOGS, "r") as f:
        logs = f.read()

    return render_template("logs.html", logs=logs)


# ------------------ ROBLOX API (/check) ------------------ #

@app.route("/check", methods=["GET"])
def check():
    key = request.args.get("key")
    hwid = request.args.get("hwid")

    keys = load_json(DB_KEYS)
    black = load_json(DB_BLACKLIST)

    # Blacklisted
    if hwid in black:
        return jsonify({"success": False, "reason": "Blacklisted"})

    # Invalid key
    if key not in keys:
        return jsonify({"success": False, "reason": "Invalid key"})

    entry = keys[key]

    # Expired key
    if entry["expires"] < time.time():
        return jsonify({"success": False, "reason": "Key expired"})

    # Auto whitelist (first use)
    if entry["hwid"] is None:
        entry["hwid"] = hwid
        entry["used"] = True
        keys[key] = entry
        save_json(DB_KEYS, keys)
        log_event(f"Key {key} auto-bound to HWID {hwid}")

    # Wrong HWID
    if entry["hwid"] != hwid:
        return jsonify({"success": False, "reason": "HWID mismatch"})

    # SUCCESS → LOAD stay.txt
    return jsonify({
        "success": True,
        "loadstring": "https://raw.githubusercontent.com/AsianTwchSecond/Loveu/refs/heads/main/stay.txt"
    })


# ------------------ UPTIMEROBOT SAFE PING ------------------ #

@app.route("/ping")
def ping():
    return "alive", 200


# ------------------ START SERVER ------------------ #

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
