from functools import wraps
from flask import jsonify, g

def authorize_roles(*allowed_roles):
    """
    Middleware decorator to restrict route access by user role.
    allowed_roles: string args e.g. "admin", "kitchen", "counter"
    """
    normalized_allowed = [str(r).lower() for r in allowed_roles]

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = getattr(g, "user", None)
            if not user or not user.get("role"):
                return jsonify({
                    "success": False,
                    "message": "Access denied. Role not identified."
                }), 403

            user_role = str(user["role"]).lower()
            if user_role not in normalized_allowed:
                return jsonify({
                    "success": False,
                    "message": f"Access denied. Required role: {', '.join(allowed_roles)}"
                }), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator
