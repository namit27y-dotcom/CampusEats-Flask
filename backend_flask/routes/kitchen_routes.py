from flask import Blueprint
from backend_flask.controllers import kitchen_controller
from backend_flask.middleware import verify_token, authorize_roles

kitchen_bp = Blueprint("kitchen", __name__)

kitchen_bp.route("/orders", methods=["GET"])(verify_token(authorize_roles("kitchen", "admin")(kitchen_controller.get_kitchen_orders)))
kitchen_bp.route("/orders/<int:id>/status", methods=["PATCH"])(verify_token(authorize_roles("kitchen", "admin")(kitchen_controller.update_order_status)))
