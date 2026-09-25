from flask import Blueprint
from backend_flask.controllers import order_controller
from backend_flask.middleware import verify_token

order_bp = Blueprint("order", __name__)

order_bp.route("", methods=["POST"], strict_slashes=False)(verify_token(order_controller.create_order))
order_bp.route("/my", methods=["GET"])(verify_token(order_controller.get_my_orders))
order_bp.route("/my-orders", methods=["GET"], endpoint="get_my_orders_alias")(verify_token(order_controller.get_my_orders))
order_bp.route("/<int:id>/cancel", methods=["PATCH", "POST"])(verify_token(order_controller.cancel_order))
order_bp.route("/<int:id>/invoice", methods=["GET"])(verify_token(order_controller.get_order_invoice))
