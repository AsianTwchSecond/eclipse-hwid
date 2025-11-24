from flask import Flask, render_template, request, redirect, session, jsonify
import os, json, time

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Admin login
ADMIN_USER = "EclipseOwner"
ADMIN_PASS = "Secret123"

# Database folder
if not os.path.exists("database"):
    os.makedirs("database")

DB_KEYS = "database/keys.json"
DB_BLACKLIST = "database/blacklist.json"
DB_LOGS = "database/logs.txt"

for f in [DB_KEYS, DB_BLACKLIST]:
    if not os.path.exists(f):
        with open(f, "w") as x:
            x.write("{}")

if not os.path.exists(DB_LOGS):
    open(DB_LOGS, "w").close()


def load_json(p):
    with open(p, "r") as f:
        return json.load(f)


def save_json(p, d):
    with open(p, "w") as f:
        json.dump(d, f, indent=4)


def log_event(txt):
    with open(DB_LOGS, "a") as f:
        f.write(f"[{time.ctime()}] {txt}\n")


# -------------------- LOGIN -------------------- #

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username")
        pw = request.form.get("password")

        if user == ADMIN_USER and pw == ADMIN_PASS:
            session["auth"] = True
            return redirect("/dashboard")

        return render_template("login.html", error="Invalid login!")

    return render_template("login.html")


def require_auth():
    return session.get("auth", False)


# -------------------- DASHBOARD -------------------- #

@app.route("/dashboard")
def dashboard():
    if not require_auth():
        return redirect("/")
    return render_template("dashboard.html")


# -------------------- KEY SYSTEM -------------------- #

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
        keys[key] = {
            "expires": expire,
            "hwid": None,
            "used": False
        }
        new_keys.append(key)

    save_json(DB_KEYS, keys)
    log_event(f"Generated {len(new_keys)} keys")
    return render_template("keys.html", keys=keys, new_keys=new_keys)


@app.route("/deletekey/<key>")
def delete_key(key):
    if not require_auth():
        return redirect("/")

    keys = load_json(DB_KEYS)
    if key in keys:
        del keys[key]
        save_json(DB_KEYS, keys)
        log_event(f"Deleted key {key}")

    return redirect("/keys")


# -------------------- BLACKLIST -------------------- #

@app.route("/blacklist")
def blacklist_page():
    if not require_auth():
        return redirect("/")

    black = load_json("database/blacklist.json")
    return render_template("blacklist.html", black=black)


@app.route("/addblacklist", methods=["POST"])
def add_black():
    if not require_auth():
        return redirect("/")

    hwid = request.form.get("hwid")
    black = load_json(DB_BLACKLIST)
    black[hwid] = True
    save_json(DB_BLACKLIST, black)
    log_event(f"Blacklisted HWID {hwid}")
    return redirect("/blacklist")


@app.route("/removeblacklist/<hwid>")
def remove_black(hwid):
    if not require_auth():
        return redirect("/")

    black = load_json(DB_BLACKLIST)
    black.pop(hwid, None)
    save_json(DB_BLACKLIST, black)
    log_event(f"Removed HWID {hwid}")
    return redirect("/blacklist")


# -------------------- LOGS -------------------- #

@app.route("/logs")
def logs_page():
    if not require_auth():
        return redirect("/")

    with open(DB_LOGS, "r") as f:
        logs = f.read()

    return render_template("logs.html", logs=logs)


# -------------------- ROBLOX API -------------------- #

@app.route("/check", methods=["GET"])
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
        entry["used"] = True
        keys[key] = entry
        save_json(DB_KEYS, keys)
        log_event(f"Key {key} bound to HWID {hwid}")

    if entry["hwid"] != hwid:
        return jsonify({"success": False, "reason": "HWID mismatch"})

    return jsonify({
        "success": True,
        "loadstring": "https://raw.githubusercontent.com/AsianTwchSecond/Loveu/refs/heads/main/stay.txt"
    })


# -------------------- SERVER -------------------- #

@app.route("/ping")
def ping():
    return "alive", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
