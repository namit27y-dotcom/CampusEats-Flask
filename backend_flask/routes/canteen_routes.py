from flask import Blueprint
from backend_flask.controllers import canteen_controller

canteen_bp = Blueprint("canteen", __name__)

canteen_bp.route("", methods=["GET"], strict_slashes=False)(canteen_controller.get_canteens)
canteen_bp.route("/<int:id>", methods=["GET"])(canteen_controller.get_canteen_by_id)
