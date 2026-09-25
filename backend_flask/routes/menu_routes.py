from flask import Blueprint
from backend_flask.controllers import menu_controller
from backend_flask.middleware import verify_token, authorize_roles

menu_bp = Blueprint("menu", __name__)

menu_bp.route("/<int:canteen_id>", methods=["GET"])(menu_controller.get_menu_items)
menu_bp.route("", methods=["POST"], strict_slashes=False)(verify_token(authorize_roles("admin")(menu_controller.add_menu_item)))
menu_bp.route("/<int:id>", methods=["PUT"])(verify_token(authorize_roles("admin")(menu_controller.update_menu_item)))
menu_bp.route("/<int:id>/availability", methods=["PATCH"])(verify_token(authorize_roles("admin", "kitchen")(menu_controller.toggle_availability)))
menu_bp.route("/<int:id>/stock", methods=["PATCH"])(verify_token(authorize_roles("admin", "kitchen")(menu_controller.update_stock)))
