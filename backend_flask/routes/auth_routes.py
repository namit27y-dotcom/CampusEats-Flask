from flask import Blueprint
from backend_flask.controllers import auth_controller
from backend_flask.middleware import verify_token

auth_bp = Blueprint("auth", __name__)

auth_bp.route("/register", methods=["POST"])(auth_controller.register)
auth_bp.route("/login", methods=["POST"])(auth_controller.login)
auth_bp.route("/me", methods=["GET"])(verify_token(auth_controller.get_me))
