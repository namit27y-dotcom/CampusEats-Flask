from .auth_routes import auth_bp
from .canteen_routes import canteen_bp
from .menu_routes import menu_bp
from .order_routes import order_bp
from .payment_routes import payment_bp
from .wallet_routes import wallet_bp
from .kitchen_routes import kitchen_bp
from .counter_routes import counter_bp
from .rating_routes import rating_bp
from .admin_routes import admin_bp
from .ai_routes import ai_bp

__all__ = [
    "auth_bp",
    "canteen_bp",
    "menu_bp",
    "order_bp",
    "payment_bp",
    "wallet_bp",
    "kitchen_bp",
    "counter_bp",
    "rating_bp",
    "admin_bp",
    "ai_bp"
]
