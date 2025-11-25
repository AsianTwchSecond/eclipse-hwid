from flask import Flask, render_template, request, redirect, session, jsonify
import psycopg2
import psycopg2.extras
import time

app = Flask(__name__)
app.secret_key = "supersecretkey"

ADMIN_USER = "EclipseOwner"
ADMIN_PASS = "Secret123"

# ----------------------------
# POSTGRESQL CONNECTION
# ----------------------------
DB_URL = "postgresql://eclipse_user:YDLnK5wvBT4j8UygKJ5qIs9e8LNj3Uap@dpg-d4imgafgi27c739n09q0-a/eclipse_db_l322"   # <- replace this

def db():
    return psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.DictCursor)


# ----------------------------
# INIT DATABASE TABLES
# ----------------------------
def init_db():
    conn = db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            key TEXT PRIMARY KEY,
            expires BIGINT,
            hwid TEXT,
            used BOOLEAN
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            hwid TEXT PRIMARY KEY
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id SERIAL PRIMARY KEY,
            text TEXT,
            time BIGINT
        );
    """)

    conn.commit()
    conn.close()


init_db()


# ----------------------------
# HELPERS
# ----------------------------

def log_event(text):
    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO logs (text, time) VALUES (%s, %s)", (text, int(time.time())))
    conn.commit()
    conn.close()


# ----------------------------
# LOGIN PAGE
# ----------------------------
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


# ----------------------------
# DASHBOARD
# ----------------------------
@app.route("/dashboard")
def dashboard():
    if not require_auth():
        return redirect("/")
    return render_template("dashboard.html")


# ----------------------------
# KEY SYSTEM
# ----------------------------
@app.route("/keys")
def keys_page():
    if not require_auth():
        return redirect("/")

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM keys ORDER BY expires DESC")
    keys = cur.fetchall()
    conn.close()

    return render_template("keys.html", keys=keys)


@app.route("/generate", methods=["POST"])
def generate():
    if not require_auth():
        return redirect("/")

    days = int(request.form.get("days"))
    amount = int(request.form.get("amount"))

    expire = int(time.time()) + days * 86400

    import random, string

    conn = db()
    cur = conn.cursor()

    new_keys = []
    for _ in range(amount):
        k = ''.join(random.choices(string.ascii_uppercase + string.digits, k=25))
        cur.execute(
            "INSERT INTO keys (key, expires, hwid, used) VALUES (%s, %s, %s, %s)",
            (k, expire, None, False)
        )
        new_keys.append(k)

    conn.commit()
    conn.close()

    log_event(f"Generated {amount} keys")

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM keys")
    keys = cur.fetchall()
    conn.close()

    return render_template("keys.html", keys=keys, new_keys=new_keys)


@app.route("/deletekey/<key>")
def delete_key(key):
    if not require_auth():
        return redirect("/")

    conn = db()
    cur = conn.cursor()
    cur.execute("DELETE FROM keys WHERE key=%s", (key,))
    conn.commit()
    conn.close()

    log_event(f"Deleted key {key}")
    return redirect("/keys")


# ----------------------------
# BLACKLIST PAGE
# ----------------------------
@app.route("/blacklist")
def blacklist_page():
    if not require_auth():
        return redirect("/")

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM blacklist")
    data = cur.fetchall()
    conn.close()

    return render_template("blacklist.html", black=data)


@app.route("/addblacklist", methods=["POST"])
def add_blacklist():
    if not require_auth():
        return redirect("/")

    hwid = request.form.get("hwid")

    conn = db()
    cur = conn.cursor()
    cur.execute("INSERT INTO blacklist (hwid) VALUES (%s) ON CONFLICT DO NOTHING", (hwid,))
    conn.commit()
    conn.close()

    log_event(f"HWID blacklisted: {hwid}")
    return redirect("/blacklist")


@app.route("/removeblacklist/<hwid>")
def removebl(hwid):
    if not require_auth():
        return redirect("/")

    conn = db()
    cur = conn.cursor()
    cur.execute("DELETE FROM blacklist WHERE hwid=%s", (hwid,))
    conn.commit()
    conn.close()

    log_event(f"HWID removed from blacklist: {hwid}")
    return redirect("/blacklist")


# ----------------------------
# LOGS
# ----------------------------
@app.route("/logs")
def logs_page():
    if not require_auth():
        return redirect("/")

    conn = db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM logs ORDER BY id DESC LIMIT 200")
    logs = cur.fetchall()
    conn.close()

    return render_template("logs.html", logs=logs)


# ----------------------------
# ROBLOX /check API
# ----------------------------
@app.route("/check")
def check():
    key = request.args.get("key")
    hwid = request.args.get("hwid")

    conn = db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM blacklist WHERE hwid=%s", (hwid,))
    if cur.fetchone():
        return jsonify({"success": False, "reason": "Blacklisted"})

    cur.execute("SELECT * FROM keys WHERE key=%s", (key,))
    row = cur.fetchone()

    if not row:
        return jsonify({"success": False, "reason": "Invalid key"})

    expires = row["expires"]
    saved_hwid = row["hwid"]

    if expires < time.time():
        return jsonify({"success": False, "reason": "Key expired"})

    # Auto-whitelist
    if saved_hwid is None:
        cur.execute("UPDATE keys SET hwid=%s, used=true WHERE key=%s", (hwid, key))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "loadstring": "https://raw.githubusercontent.com/AsianTwchSecond/Loveu/refs/heads/main/stay.txt"})

    # Wrong HWID
    if saved_hwid != hwid:
        conn.close()
        return jsonify({"success": False, "reason": "HWID mismatch"})

    conn.close()
    return jsonify({"success": True, "loadstring": "https://raw.githubusercontent.com/AsianTwchSecond/Loveu/refs/heads/main/stay.txt"})


# ----------------------------
# RUN SERVER
# ----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
