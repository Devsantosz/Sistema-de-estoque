import os
import sqlite3
import bcrypt
from flask import Flask, render_template, request, redirect, session

app = Flask(__name__)
app.secret_key = "troque-por-uma-chave-forte"
DB_PATH = "data/app.db"


def get_db():
    os.makedirs("data", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = get_db()
    cur = con.cursor()

    # USERS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash BLOB NOT NULL
        );
    """)

    # PRODUCTS
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            codigo TEXT NOT NULL UNIQUE,
            marca TEXT NOT NULL,
            categoria TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 0
        );
    """)

    con.commit()
    con.close()


def require_login():
    return "user_id" in session


@app.get("/")
def index():
    # tela de login
    return render_template("login.html")


@app.post("/register")
def register():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        return redirect("/")

    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    con = get_db()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, pw_hash))
        con.commit()
    except sqlite3.IntegrityError:
        con.close()
        return "Usuário já existe. Volte e escolha outro.", 400

    con.close()
    return "Conta criada! Agora faça login.", 200


@app.post("/login")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT id, username, password_hash FROM users WHERE username = ?", (username,))
    user = cur.fetchone()
    con.close()

    if not user:
        return "Login inválido.", 401

    ok = bcrypt.checkpw(password.encode("utf-8"), user["password_hash"])
    if not ok:
        return "Login inválido.", 401

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return redirect("/dashboard")


@app.get("/dashboard")
def dashboard():
    if not require_login():
        return redirect("/")

    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT id, name, codigo, marca, categoria, quantity FROM products ORDER BY id DESC")
    products = cur.fetchall()
    con.close()

    return render_template("dashboard.html", username=session["username"], products=products)


@app.post("/add")
def add_product():
    if not require_login():
        return redirect("/")

    name = request.form.get("name", "").strip()
    codigo = request.form.get("codigo", "").strip()
    marca = request.form.get("marca", "").strip()
    categoria = request.form.get("categoria", "").strip()

    if not name or not codigo or not marca or not categoria:
        return redirect("/dashboard")

    try:
        qty = int(request.form.get("qty", 0))
    except ValueError:
        qty = 0
    qty = max(0, qty)

    con = get_db()
    cur = con.cursor()

    # se o código já existir, atualiza (evita conflito do UNIQUE)
    cur.execute("SELECT id, quantity FROM products WHERE codigo = ?", (codigo,))
    p = cur.fetchone()

    if p:
        new_qty = p["quantity"] + qty
        cur.execute("""
            UPDATE products
            SET name = ?, marca = ?, categoria = ?, quantity = ?
            WHERE id = ?
        """, (name, marca, categoria, new_qty, p["id"]))
    else:
        cur.execute("""
            INSERT INTO products (name, codigo, marca, categoria, quantity)
            VALUES (?, ?, ?, ?, ?)
        """, (name, codigo, marca, categoria, qty))

    con.commit()
    con.close()

    return redirect("/dashboard")


@app.post("/remove/<int:prod_id>")
def remove_product(prod_id):
    if not require_login():
        return redirect("/")

    con = get_db()
    cur = con.cursor()
    cur.execute("DELETE FROM products WHERE id = ?", (prod_id,))
    con.commit()
    con.close()

    return redirect("/dashboard")


@app.get("/logout")
def logout():
    session.clear()
    return render_template("login.html")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
