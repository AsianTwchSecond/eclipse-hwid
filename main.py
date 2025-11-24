from flask import Flask, render_template, request, redirect, session, jsonify
import os, json, time, random, string

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ADMIN
ADMIN_USER = "EclipseOwner"
ADMIN_PASS = "Secret123"

# DB FOLDER
if not os.path.exists("database"):
    os.makedirs("database")

DB_KEYS = "database/keys.json"
DB_BLACKLIST = "database/blacklist.json"
DB_LOGS = "database/logs.txt"

# CREATE FILES IF MISSING
if not os.path.exists(DB_KEYS):
    open(DB_KEYS, "w").write("{}")
if not os.path.exists(DB_BLACKLIST):
    open(DB_BLACKLIST, "w").write("{}")
if not os.path.exists(DB_LOGS):
    open(DB_LOGS, "w").write("")


def load_json(path):
    return json.load(open(path, "r"))

def save_json(path, data):
    json.dump(data, open(path, "w"), indent=4)

def log_event(text):
    open(DB_LOGS, "a").write(f"[{time.ctime()}] {text}\n")


# ---------------- LOGIN ---------------- #

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")

        if u == ADMIN_USER and p == ADMIN_PASS:
            session["auth"] = True
            return redirect("/dashboard")

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


def authed():
    return session.get("auth") == True


# ---------------- DASHBOARD ---------------- #

@app.route("/dashboard")
def dashboard():
    if not authed(): return redirect("/")
    return render_template("dashboard.html")


# ---------------- KEY MANAGER ---------------- #

@app.route("/keys")
def keys():
    if not authed(): return redirect("/")
    return render_template("keys.html", keys=load_json(DB_KEYS))


@app.route("/generate", methods=["POST"])
def generate():
    if not authed(): return redirect("/")

    days = int(request.form.get("days"))
    amount = int(request.form.get("amount"))

    expire = int(time.time()) + (days * 86400)
    db = load_json(DB_KEYS)

    new_keys = []

    for _ in range(amount):
        k = ''.join(random.choices(string.ascii_uppercase + string.digits, k=25))
        db[k] = {"expires": expire, "hwid": None}
        new_keys.append(k)

    save_json(DB_KEYS, db)
    log_event(f"Generated {len(new_keys)} keys")

    return render_template("keys.html", keys=db, new_keys=new_keys)


@app.route("/deletekey/<key>")
def deletekey(key):
    if not authed(): return redirect("/")
    db = load_json(DB_KEYS)
    db.pop(key, None)
    save_json(DB_KEYS, db)
    log_event(f"Deleted key {key}")
    return redirect("/keys")


# ---------------- BLACKLIST ---------------- #

@app.route("/blacklist")
def blacklist():
    if not authed(): return redirect("/")
    return render_template("blacklist.html", black=load_json(DB_BLACKLIST))


@app.route("/addblacklist", methods=["POST"])
def add_blacklist():
    if not authed(): return redirect("/")
    hwid = request.form.get("hwid")
    db = load_json(DB_BLACKLIST)
    db[hwid] = True
    save_json(DB_BLACKLIST, db)
    log_event(f"Blacklisted {hwid}")
    return redirect("/blacklist")


@app.route("/removeblacklist/<hwid>")
def remove_black(hwid):
    if not authed(): return redirect("/")
    db = load_json(DB_BLACKLIST)
    db.pop(hwid, None)
    save_json(DB_BLACKLIST, db)
    log_event(f"Removed blacklist {hwid}")
    return redirect("/blacklist")


# ---------------- LOGS ---------------- #

@app.route("/logs")
def logs():
    if not authed(): return redirect("/")
    logs = open(DB_LOGS).read()
    return render_template("logs.html", logs=logs)


# ---------------- ROBLOX API ---------------- #

@app.route("/check")
def check():
    key = request.args.get("key")
    hwid = request.args.get("hwid")

    keys = load_json(DB_KEYS)
    black = load_json(DB_BLACKLIST)

    if hwid in black:
        return jsonify({"success": False, "reason": "Blacklisted"})

    if key not in keys:
        return jsonify({"success": False, "reason": "Invalid Key"})

    data = keys[key]

    if data["expires"] < time.time():
        return jsonify({"success": False, "reason": "Key expired"})

    if data["hwid"] is None:
        data["hwid"] = hwid  
        keys[key] = data
        save_json(DB_KEYS, keys)
        log_event(f"Auto-bound key {key} → HWID {hwid}")

    if data["hwid"] != hwid:
        return jsonify({"success": False, "reason": "HWID mismatch"})

    return jsonify({
        "success": True,
        "script": f'_G.Key = "{key}"\nloadstring(game:HttpGet("https://raw.githubusercontent.com/FwtysLuas/EclipseMeteor/refs/heads/main/Protected_4548462735082467.lua.txt"))()'
    })


@app.route("/ping")
def ping():
    return "alive", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
