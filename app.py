import os
import sqlite3
import bcrypt
from functools import wraps
from flask import Flask, render_template, request, redirect, session, flash

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "DEV_ONLY_troque-isso")
DB_PATH = "data/app.db"


def get_db():
    os.makedirs("data", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with get_db() as con:
        cur = con.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash BLOB NOT NULL
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                codigo TEXT NOT NULL UNIQUE,
                categoria TEXT NOT NULL,
                price REAL NOT NULL DEFAULT 0,
                quantity INTEGER NOT NULL DEFAULT 0,
                stqmin INTEGER NOT NULL DEFAULT 0
            );
        """)

        # migrações seguras
        cur.execute("PRAGMA table_info(products)")
        cols = [r["name"] for r in cur.fetchall()]

        if "price" not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN price REAL NOT NULL DEFAULT 0")
        if "stqmin" not in cols:
            cur.execute("ALTER TABLE products ADD COLUMN stqmin INTEGER NOT NULL DEFAULT 0")


def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            flash("Faça login para continuar.", "warning")
            return redirect("/")
        return fn(*args, **kwargs)
    return wrapper


@app.get("/")
def index():
    return render_template("login.html")


@app.post("/register")
def register():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        flash("Preencha usuário e senha.", "warning")
        return redirect("/")

    pw_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    try:
        with get_db() as con:
            con.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, pw_hash)
            )
        flash("Conta criada! Agora faça login.", "success")
        return redirect("/")
    except sqlite3.IntegrityError:
        flash("Esse usuário já existe. Escolha outro.", "danger")
        return redirect("/")


@app.post("/login")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not username or not password:
        flash("Preencha usuário e senha.", "warning")
        return redirect("/")

    with get_db() as con:
        user = con.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,)
        ).fetchone()

    if not user:
        flash("Usuário ou senha inválidos.", "danger")
        return redirect("/")

    if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"]):
        flash("Usuário ou senha inválidos.", "danger")
        return redirect("/")

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return redirect("/dashboard")


@app.get("/dashboard")
@login_required
def dashboard():
    with get_db() as con:
        products = con.execute("""
            SELECT id, name, codigo, categoria, price, quantity, stqmin
            FROM products
            ORDER BY id DESC
        """).fetchall()

        total_products = con.execute(
            "SELECT COUNT(*) AS total FROM products"
        ).fetchone()["total"]

        total_categories = con.execute(
            "SELECT COUNT(DISTINCT categoria) AS total FROM products"
        ).fetchone()["total"]

        # estoque baixo: quantity <= stqmin (e quantidade > 0, opcional)
        value_estoque = con.execute("""
            SELECT COUNT(*) AS total
            FROM products
            WHERE quantity > 0 AND quantity <= stqmin
        """).fetchone()["total"]

        # gasto total (valor total do estoque)
        gasto_estoque = con.execute(
            "SELECT COALESCE(SUM(price * quantity), 0) AS total FROM products"
        ).fetchone()["total"]

    return render_template(
        "dashboard.html",
        username=session.get("username", ""),
        products=products,
        total_products=total_products,
        total_categories=total_categories,
        value_estoque=value_estoque,
        gasto_estoque=f"R$ {gasto_estoque:.2f}".replace(".", ",")
    )


@app.post("/add")
@login_required
def add_product():
    name = request.form.get("name", "").strip()
    codigo = request.form.get("codigo", "").strip()
    categoria = request.form.get("categoria", "").strip()

    if not all([name, codigo, categoria]):
        flash("Preencha todos os campos do produto.", "warning")
        return redirect("/dashboard")

    # qty
    try:
        qty = int(request.form.get("qty", 0))
    except ValueError:
        qty = 0
    qty = max(0, qty)

    # price
    try:
        price = float(request.form.get("price", 0))
    except ValueError:
        price = 0.0
    price = max(0.0, price)

    # stqmin
    try:
        stqmin = int(request.form.get("stqmin", 0))
    except ValueError:
        stqmin = 0
    stqmin = max(0, stqmin)

    with get_db() as con:
        cur = con.cursor()
        existing = cur.execute(
            "SELECT id, quantity FROM products WHERE codigo = ?",
            (codigo,)
        ).fetchone()

        if existing:
            new_qty = existing["quantity"] + qty
            cur.execute("""
                UPDATE products
                SET name = ?, categoria = ?, price = ?, quantity = ?, stqmin = ?
                WHERE id = ?
            """, (name, categoria, price, new_qty, stqmin, existing["id"]))
            flash("Produto atualizado (quantidade somada).", "success")
        else:
            cur.execute("""
                INSERT INTO products (name, codigo, categoria, price, quantity, stqmin)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, codigo, categoria, price, qty, stqmin))
            flash("Produto adicionado.", "success")

    return redirect("/dashboard")


@app.post("/remove/<int:prod_id>")
@login_required
def remove_product(prod_id):
    with get_db() as con:
        con.execute("DELETE FROM products WHERE id = ?", (prod_id,))
    flash("Produto removido.", "success")
    return redirect("/dashboard")


@app.get("/logout")
def logout():
    session.clear()
    flash("Você saiu da conta.", "success")
    return redirect("/")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)