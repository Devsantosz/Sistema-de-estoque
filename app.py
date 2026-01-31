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
            quantity INTEGER NOT NULL DEFAULT 0
        );
    """)
    conn.commit()
    conn.close()

@app.route("/")
def home():
    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT id, name, quantity FROM products ORDER BY id DESC")
    products = cur.fetchall()
    con.close()
    return render_template("dashboard.html", products=products)



@app.post("/add")
def adicionar():
    name = request.form["name"].strip()
    if not name:
        return redirect("/")

    qty = max(0, int(request.form["qty"]))

    con = get_db()
    cur = con.cursor()
    cur.execute("INSERT INTO products (name, quantity) VALUES (?, ?)", (name, qty))
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
