from flask import Blueprint
from backend_flask.controllers import wallet_controller
from backend_flask.middleware import verify_token

wallet_bp = Blueprint("wallet", __name__)

wallet_bp.route("/balance", methods=["GET"])(verify_token(wallet_controller.get_wallet_balance))
wallet_bp.route("/add-money", methods=["POST"])(verify_token(wallet_controller.add_money))
wallet_bp.route("/transactions", methods=["GET"])(verify_token(wallet_controller.get_transactions))
