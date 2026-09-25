from flask import Blueprint
from backend_flask.controllers import counter_controller
from backend_flask.middleware import verify_token, authorize_roles

counter_bp = Blueprint("counter", __name__)

counter_bp.route("/orders", methods=["GET"])(verify_token(authorize_roles("counter", "admin")(counter_controller.get_counter_orders)))
counter_bp.route("/orders/<int:id>/collect", methods=["PATCH"])(verify_token(authorize_roles("counter", "admin")(counter_controller.mark_order_collected)))
