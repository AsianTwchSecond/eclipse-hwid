from flask import Flask, render_template, request, redirect, session, jsonify
import os, json, time

app = Flask(__name__)
app.secret_key = "supersecretkey"

# Admin info
ADMIN_USER = "EclipseOwner"
ADMIN_PASS = "Secret123"

# Database folder
if not os.path.exists("database"):
    os.makedirs("database")

DB_KEYS = "database/keys.json"
DB_BLACKLIST = "database/blacklist.json"
DB_LOGS = "database/logs.txt"

# Create json files
for path in [DB_KEYS, DB_BLACKLIST]:
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write("{}")

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

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")

        if u == ADMIN_USER and p == ADMIN_PASS:
            session["auth"] = True
            return redirect("/dashboard")

        return render_template("login.html", error="Invalid Login")

    return render_template("login.html")


def authed():
    return session.get("auth", False)

@app.route("/dashboard")
def dashboard():
    if not authed():
        return redirect("/")
    return render_template("dashboard.html")


@app.route("/keys")
def keys():
    if not authed():
        return redirect("/")
    return render_template("keys.html", keys=load_json(DB_KEYS))


@app.route("/generate", methods=["POST"])
def generate():
    if not authed():
        return redirect("/")

    days = int(request.form.get("days"))
    amount = int(request.form.get("amount"))
    expire = int(time.time()) + days * 86400

    keys = load_json(DB_KEYS)

    import random, string
    new_keys = []

    for _ in range(amount):
        key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=25))
        keys[key] = {"expires": expire, "hwid": None, "used": False}
        new_keys.append(key)

    save_json(DB_KEYS, keys)
    log_event(f"Generated {amount} keys")

    return render_template("keys.html", keys=keys, new_keys=new_keys)


@app.route("/delete/<k>")
def delete(k):
    if not authed():
        return redirect("/")
    keys = load_json(DB_KEYS)
    if k in keys:
        del keys[k]
        save_json(DB_KEYS, keys)
    log_event(f"Removed key {k}")
    return redirect("/keys")


@app.route("/blacklist")
def blacklist():
    if not authed():
        return redirect("/")
    return render_template("blacklist.html", black=load_json(DB_BLACKLIST))


@app.route("/blackadd", methods=["POST"])
def blackadd():
    if not authed():
        return redirect("/")
    hwid = request.form.get("hwid")
    b = load_json(DB_BLACKLIST)
    b[hwid] = True
    save_json(DB_BLACKLIST, b)
    log_event(f"Blacklisted {hwid}")
    return redirect("/blacklist")


@app.route("/blackremove/<h>")
def blackremove(h):
    if not authed():
        return redirect("/")
    b = load_json(DB_BLACKLIST)
    if h in b:
        del b[h]
    save_json(DB_BLACKLIST, b)
    log_event(f"Removed blacklist {h}")
    return redirect("/blacklist")


@app.route("/logs")
def logs():
    if not authed():
        return redirect("/")
    with open(DB_LOGS, "r") as f:
        data = f.read()
    return render_template("logs.html", logs=data)


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
        return jsonify({"success": False, "reason": "Invalid key"})

    entry = keys[key]

    if entry["expires"] < time.time():
        return jsonify({"success": False, "reason": "Expired key"})

    if entry["hwid"] is None:
        entry["hwid"] = hwid
        entry["used"] = True
        keys[key] = entry
        save_json(DB_KEYS, keys)
        log_event(f"HWID auto-bound: {hwid}")

    if entry["hwid"] != hwid:
        return jsonify({"success": False, "reason": "HWID mismatch"})

    return jsonify({
        "success": True,
        "loadstring": "https://raw.githubusercontent.com/AsianTwchSecond/Loveu/refs/heads/main/stay.txt"
    })


@app.route("/ping")
def ping():
    return "alive", 200


app.run(host="0.0.0.0", port=8080)
