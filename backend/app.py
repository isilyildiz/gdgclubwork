from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, redirect, session
import sqlite3
import os
import random

app = Flask(__name__)
app.secret_key = "super-secret-key"

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT NOT NULL,
        password TEXT NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        image_path TEXT NOT NULL,
        category TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()


def get_db_connection():
    conn = sqlite3.connect("database.db")
    conn.row_factory = sqlite3.Row
    return conn


# LOGIN PAGE
@app.route("/")
def login_page():
    return render_template("index.html")


# LOGIN ACTION
@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    password = request.form["password"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE username = ? AND password = ?",
        (username, password)
    )
    user = cursor.fetchone()
    conn.close()

    if user:
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        return redirect("/welcome")
    else:
        return "Kullanıcı adı veya şifre yanlış."


# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register_page():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, password)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "Bu kullanıcı adı zaten kayıtlı."

        conn.close()
        return redirect("/")

    return render_template("register.html")


# WELCOME (PROTECTED)
@app.route("/welcome")
def welcome_page():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM items WHERE user_id = ?",
        (session["user_id"],)
    )
    items = cursor.fetchall()
    conn.close()

    return render_template(
        "welcome.html",
        username=session["username"],
        items=items
    )


# ADD ITEM
@app.route("/add-item", methods=["POST"])
def add_item():
    if "user_id" not in session:
        return redirect("/")

    file = request.files["image"]
    category = request.form["category"]

    if file.filename == "":
        return "Dosya seçilmedi."

    # uploads klasörü yoksa oluştur
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)

    file.save(filepath)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO items (user_id, image_path, category) VALUES (?, ?, ?)",
        (session["user_id"], filepath, category)
    )
    conn.commit()
    conn.close()

    return redirect("/welcome")


#delete item
@app.route("/delete-item/<int:item_id>", methods=["POST"])
def delete_item(item_id):
    if "user_id" not in session:
        return redirect("/")

    conn = get_db_connection()
    cursor = conn.cursor()

    #item kullanıcıya ait mi kontrolü
    cursor.execute(
        "SELECT * FROM items WHERE id = ? AND user_id = ?",
        (item_id, session["user_id"])
    )
    item = cursor.fetchone()

    if item:
        # Dosyayı sil
        if os.path.exists(item["image_path"]):
            os.remove(item["image_path"])

        # dbden sil
        cursor.execute(
            "DELETE FROM items WHERE id = ?",
            (item_id,)
        )
        conn.commit()

    conn.close()
    return redirect("/welcome")

#random kombin
@app.route("/random-combination")
def random_combination():
    if "user_id" not in session:
        return redirect("/")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Üst
    cursor.execute(
        "SELECT * FROM items WHERE user_id = ? AND category = 'ust'",
        (session["user_id"],)
    )
    ustler = cursor.fetchall()

    # Alt
    cursor.execute(
        "SELECT * FROM items WHERE user_id = ? AND category = 'alt'",
        (session["user_id"],)
    )
    altlar = cursor.fetchall()

    # Ayakkabı
    cursor.execute(
        "SELECT * FROM items WHERE user_id = ? AND category = 'ayakkabi'",
        (session["user_id"],)
    )
    ayakkabilar = cursor.fetchall()

    conn.close()

    # Eğer herhangi biri boşsa kombin oluşturamayız
    if not ustler or not altlar or not ayakkabilar:
        return "Kombin oluşturmak için her kategoriden en az 1 ürün eklemelisin."

    kombin = {
        "ust": random.choice(ustler),
        "alt": random.choice(altlar),
        "ayakkabi": random.choice(ayakkabilar)
    }

    return render_template(
        "kombin.html",
        kombin=kombin
    )


# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
