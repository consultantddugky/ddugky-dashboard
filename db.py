# db.py
from flask import Flask, render_template, request, redirect, session
from db import get_db
from flask_mysqldb import MySQL
app = Flask(__name__)
app.secret_key = 'secretkey'

# MySQL config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = '1234567890'
app.config['MYSQL_DB'] = 'kaushal_dashboard'

mysql = MySQL(app)

def check_login(username, password):
    cur = mysql.connection.cursor()
    cursor = cur.cursor(dictionary=True)

    query = "SELECT * FROM users WHERE username=%s AND password=%s"
    cursor.execute(query, (username, password))

    user = cursor.fetchone()
    cur.close()

    return user