from flask import Flask, request, render_template, redirect, session
import psycopg2
import psycopg2.extras
import os
import datetime

app = Flask(__name__)
app.secret_key = "ECLIPSE_SECRET_KEY"

# ────────────────────────────────────────────────
# CONNECT TO POSTGRES (Render → Environment → DATABASE_URL)
# ────────────────────────────────────────────────

DATABASE_URL = os.getenv("DATABASE_URL")

conn = psycopg2.connect(DATABASE_URL, sslmode="require")
cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# ────────────────────────────────────────────────
# CREATE TABLES IF NOT EXISTS
# ────────────────────────────────────────────────

cursor.execute("""
CREATE TABLE IF NOT EXISTS keys (
    key TEXT PRIMARY KEY,
    expires DATE,
    hwid TEXT
);
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS blacklist (
    hwid TEXT PRIMARY KEY
);
""")

conn.commit()

# ────────────────────────────────────────────────
# LOGIN SYSTEM
# ────────────────────────────────────────────────

ADMIN_USER = "EclipseOwner"
ADMIN_PASS = "Secret123"

@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")

        if u == ADMIN_USER and p == ADMIN_PASS:
            session["logged"] = True
            return redirect("/dashboard")
        else:
            return render_template("login.html", error="Invalid Login")

    return render_template("login.html")


# ────────────────────────────────────────────────
# DASHBOARD
# ────────────────────────────────────────────────

@app.route("/dashboard")
def dashboard():
    if "logged" not in session:
        return redirect("/")
    return render_template("dashboard.html")


# ────────────────────────────────────────────────
# KEYS PAGE (LIST + GENERATE + DELETE)
# ────────────────────────────────────────────────

@app.route("/keys", methods=["GET", "POST"])
def keys_page():
    if "logged" not in session:
        return redirect("/")

    new_keys = []

    if request.method == "POST":
        days = int(request.form.get("days"))
        amount = int(request.form.get("amount"))

        for _ in range(amount):
            import secrets
            k = secrets.token_hex(16).upper()

            expire_date = datetime.date.today() + datetime.timedelta(days=days)

            cursor.execute(
                "INSERT INTO keys (key, expires, hwid) VALUES (%s, %s, %s)",
                (k, expire_date, None)
            )
            conn.commit()

            new_keys.append(k)

    cursor.execute("SELECT * FROM keys")
    all_keys = cursor.fetchall()

    return render_template("keys.html", keys=all_keys, new_keys=new_keys)


# DELETE KEY
@app.route("/deletekey/<key>")
def delete_key(key):
    if "logged" not in session:
        return redirect("/")

    cursor.execute("DELETE FROM keys WHERE key = %s", (key,))
    conn.commit()
    return redirect("/keys")


# ────────────────────────────────────────────────
# API FOR LUA CHECK
# ────────────────────────────────────────────────

@app.route("/check")
def check():
    key = request.args.get("key")
    hwid = request.args.get("hwid")

    cursor.execute("SELECT * FROM blacklist WHERE hwid = %s", (hwid,))
    if cursor.fetchone():
        return {"success": False, "reason": "Blacklisted"}

    cursor.execute("SELECT * FROM keys WHERE key = %s", (key,))
    result = cursor.fetchone()

    if not result:
        return {"success": False, "reason": "Invalid Key"}

    expire = result["expires"]

    if expire < datetime.date.today():
        return {"success": False, "reason": "Expired"}

    # Bind HWID if first time
    if result["hwid"] is None:
        cursor.execute("UPDATE keys SET hwid = %s WHERE key = %s", (hwid, key))
        conn.commit()

    elif result["hwid"] != hwid:
        return {"success": False, "reason": "HWID Mismatch"}

    return {"success": True}


# ────────────────────────────────────────────────
# START SERVER
# ────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
