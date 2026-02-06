import os
import sqlite3
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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
    """)
    con.commit()
    con.close()

@app.get("/")
def index():
    return render_template("login.html")

@app.post("/register")
def register():
    username = request.form["username"].strip()
    password = request.form["password"].strip()

    if not username or not password:
        return redirect("/")

    con = get_db()
    cur = con.cursor()
    try:
        cur.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        con.commit()
    except sqlite3.IntegrityError:
        # username já existe
        con.close()
        return "Usuário já existe. Volte e escolha outro.", 400

    con.close()
    return "Conta criada! Agora faça login.", 200

@app.post("/login")
def login():
    username = request.form["username"].strip()
    password = request.form["password"].strip()

    con = get_db()
    cur = con.cursor()
    cur.execute("SELECT id, username FROM users WHERE username = ? AND password = ?", (username, password))
    user = cur.fetchone()
    con.close()

    if not user:
        return "Login inválido.", 401

    session["user_id"] = user["id"]
    session["username"] = user["username"]
    return redirect("/dashboard")

@app.get("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")
    render_template("dashboard.html")
    return f"Logado como: {session['username']} ✅"

@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
