import os
import sqlite3
import uuid
import bcrypt
from flask import Flask, render_template, request, redirect, session, abort

app = Flask(__name__)
DB_PATH = "data/app.db"


def get_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
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
    conn.commit()
    conn.close()

@app.route("/")
def home():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT id, name, codigo, marca, categoria, quantity FROM products ORDER BY id DESC")
    products = cur.fetchall()
    con.close()
    return render_template("dashboard.html", products=products)



@app.post("/add")
def adicionar():
    name = request.form.get("name", "").strip()
    codigo = request.form.get("codigo", "").strip()
    marca = request.form.get("marca", "").strip()
    categoria = request.form.get("categoria", "").strip()

    if not name or not codigo or not marca or not categoria:
        return redirect("/")

    try:
        qty = int(request.form.get("qty", 0))
    except ValueError:
        qty = 0
    qty = max(0, qty)

    con = get_db()
    cur = con.cursor()

    # agora o identificador é o codigo (UNIQUE)
    cur.execute("SELECT id, quantity FROM products WHERE codigo = ?", (codigo,))
    product = cur.fetchone()

    if product:
        new_qty = product["quantity"] + qty
        cur.execute(
            "UPDATE products SET name = ?, marca = ?, categoria = ?, quantity = ? WHERE id = ?",
            (name, marca, categoria, new_qty, product["id"])
        )
    else:
        cur.execute(
            "INSERT INTO products (name, codigo, marca, categoria, quantity) VALUES (?, ?, ?, ?, ?)",
            (name, codigo, marca, categoria, qty)
        )

    con.commit()
    con.close()
    return redirect("/")

@app.post("/remove/<int:id>")
def remover(id):
    con = get_db()
    cur = con.cursor()
    cur.execute("DELETE FROM products WHERE id = ?", (id,))
    con.commit()
    con.close()
    return redirect("/")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
