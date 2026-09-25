import datetime
from flask import Flask, jsonify, request
from flask_socketio import join_room, leave_room
from backend_flask.config import Config
from backend_flask.extensions import socketio, cors, limiter
from backend_flask.routes import (
    auth_bp,
    canteen_bp,
    menu_bp,
    order_bp,
    payment_bp,
    wallet_bp,
    kitchen_bp,
    counter_bp,
    rating_bp,
    admin_bp,
    ai_bp
)

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Enable CORS
    cors.init_app(app, resources={r"/api/*": {"origins": Config.CORS_ORIGINS + ["*"]}})
    
    # Initialize SocketIO
    socketio.init_app(app, cors_allowed_origins="*")

    # Global Health Routes
    @app.route("/", methods=["GET"])
    def root_status():
        return jsonify({
            "success": True,
            "message": "CampusEats Flask API is running",
            "version": "1.0.0"
        }), 200

    @app.route("/api/health", methods=["GET"])
    def health_check():
        from backend_flask.services.db_service import query_db
        db_status = "Disconnected"
        try:
            res = query_db("SELECT 1 AS ping", one=True)
            if res and res.get("ping") == 1:
                db_status = "Connected"
        except Exception as e:
            db_status = f"Error: {type(e).__name__}"

        return jsonify({
            "success": True,
            "status": "ok",
            "database": db_status,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "service": "CampusEats Flask Backend"
        }), 200

    # Register API Blueprints
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(canteen_bp, url_prefix="/api/canteens")
    app.register_blueprint(menu_bp, url_prefix="/api/menu")
    app.register_blueprint(order_bp, url_prefix="/api/orders")
    app.register_blueprint(payment_bp, url_prefix="/api/payment")
    app.register_blueprint(wallet_bp, url_prefix="/api/wallet")
    app.register_blueprint(kitchen_bp, url_prefix="/api/kitchen")
    app.register_blueprint(counter_bp, url_prefix="/api/counter")
    app.register_blueprint(rating_bp, url_prefix="/api/ratings")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(ai_bp, url_prefix="/api/ai")

    # Global 404 Handler
    @app.errorhandler(404)
    def handle_404(e):
        return jsonify({
            "success": False,
            "message": "API endpoint not found"
        }), 404

    # Global 500 Handler
    @app.errorhandler(500)
    def handle_500(e):
        return jsonify({
            "success": False,
            "message": "Internal server error"
        }), 500

    return app

# Socket.IO Event Handlers
@socketio.on("connect")
def handle_connect(auth):
    # Support connection handshake
    pass

@socketio.on("joinOrder")
def handle_join_order(order_id):
    if order_id:
        room_name = f"order_{order_id}"
        join_room(room_name)

@socketio.on("joinCanteen")
def handle_join_canteen(canteen_id):
    if canteen_id:
        room_name = f"canteen_{canteen_id}"
        join_room(room_name)

@socketio.on("disconnect")
def handle_disconnect():
    pass

app = create_app()

if __name__ == "__main__":
    port = Config.PORT
    print(f"🚀 CampusEats Flask server starting on port {port}...")
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
