from .extensions import mysql, login_manager
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user_data = cur.fetchone()
    cur.close()

    if user_data:
        return User(
            id=user_data['id'],
            username=user_data['username'],
            email=user_data['email'],
            role=user_data['role']
        )
    return None


class User(UserMixin):
    def __init__(self, id, username, email, role):
        self.id = id
        self.username = username
        self.email = email
        self.role = role


class Product:
    def __init__(self, id, name, manufacturer, price):
        self.id = id
        self.name = name
        self.manufacturer = manufacturer
        self.price = price


class Shop:
    def __init__(self, id, name, address):
        self.id = id
        self.name = name
        self.address = address