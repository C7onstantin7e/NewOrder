from .auth import auth_bp
from .main import main_bp
from .products import products_bp
from .shops import shops_bp
from .orders import orders_bp
from .admin import admin_bp

__all__ = ['auth_bp', 'products_bp', 'shops_bp', 'orders_bp', 'admin_bp', 'main_bp']