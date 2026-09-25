from flask import Blueprint
from backend_flask.controllers import payment_controller
from backend_flask.middleware import verify_token

payment_bp = Blueprint("payment", __name__)

payment_bp.route("/create-order", methods=["POST"])(verify_token(payment_controller.create_razorpay_order))
payment_bp.route("/verify-signature", methods=["POST"])(verify_token(payment_controller.verify_razorpay_signature))
