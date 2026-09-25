import jwt
from functools import wraps
from flask import request, jsonify, g
from backend_flask.config import Config

def verify_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({
                "success": False,
                "message": "Authorization token required"
            }), 401
            
        token = auth_header.split(" ")[1].strip()
        
        try:
            decoded = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
            # Normalize fields to match Node.js req.user
            g.user = {
                "id": decoded.get("id"),
                "email": decoded.get("email"),
                "role": str(decoded.get("role", "")).lower(),
                "canteen_id": decoded.get("canteen_id")
            }
            # Also attach directly to request for compatibility
            request.user = g.user
        except jwt.ExpiredSignatureError:
            return jsonify({
                "success": False,
                "message": "Token expired"
            }), 401
        except jwt.InvalidTokenError:
            return jsonify({
                "success": False,
                "message": "Invalid or expired token"
            }), 401
            
        return f(*args, **kwargs)
    return decorated_function
