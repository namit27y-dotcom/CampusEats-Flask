from flask import Blueprint
from backend_flask.controllers import rating_controller
from backend_flask.middleware import verify_token

rating_bp = Blueprint("rating", __name__)

rating_bp.route("", methods=["POST"], strict_slashes=False)(verify_token(rating_controller.add_rating))
rating_bp.route("", methods=["GET"], strict_slashes=False)(rating_controller.get_ratings)
