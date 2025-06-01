from flask import Flask
from .extensions import mysql, login_manager
from .routes import main_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object('config.Config')

    # Инициализация расширений
    mysql.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # Регистрация blueprint'ов
    from .routes.auth import auth_bp
    from .routes.products import products_bp
    from .routes.shops import shops_bp
    from .routes.orders import orders_bp
    from .routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(shops_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(main_bp)

    return app