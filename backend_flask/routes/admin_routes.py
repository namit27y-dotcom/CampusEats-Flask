from flask import Blueprint
from backend_flask.controllers import admin_controller
from backend_flask.middleware import verify_token, authorize_roles

admin_bp = Blueprint("admin", __name__)

admin_bp.route("/stats", methods=["GET"])(verify_token(authorize_roles("admin")(admin_controller.get_admin_stats)))
admin_bp.route("/analytics/daily-sales", methods=["GET"])(verify_token(authorize_roles("admin")(admin_controller.get_daily_sales_analytics)))
admin_bp.route("/analytics/peak-hours", methods=["GET"])(verify_token(authorize_roles("admin")(admin_controller.get_peak_hours_analytics)))
admin_bp.route("/analytics/top-dishes", methods=["GET"])(verify_token(authorize_roles("admin")(admin_controller.get_top_dishes_analytics)))
admin_bp.route("/analytics/canteens", methods=["GET"])(verify_token(authorize_roles("admin")(admin_controller.get_canteens_analytics)))
admin_bp.route("/analytics/fulfillment", methods=["GET"])(verify_token(authorize_roles("admin")(admin_controller.get_fulfillment_analytics)))
admin_bp.route("/users", methods=["GET"])(verify_token(authorize_roles("admin")(admin_controller.get_admin_users)))
admin_bp.route("/orders", methods=["GET"])(verify_token(authorize_roles("admin")(admin_controller.get_admin_orders)))
