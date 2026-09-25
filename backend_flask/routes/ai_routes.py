from flask import Blueprint
from backend_flask.controllers import ai_controller
from backend_flask.middleware import verify_token

ai_bp = Blueprint("ai", __name__)

ai_bp.route("/recommend", methods=["POST"])(verify_token(ai_controller.get_ai_recommendations))
