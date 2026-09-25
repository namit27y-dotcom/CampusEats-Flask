import re
import datetime
import bcrypt
import jwt
from flask import request, jsonify, g
from backend_flask.config import Config
from backend_flask.services.db_service import query_db, execute_db

EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SPECIAL_CHAR_REGEX = re.compile(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?~`]")

def register():
    try:
        data = request.get_json() or {}
        name = data.get("name")
        email = data.get("email")
        password = data.get("password")

        if not name or not email or not password:
            return jsonify({
                "success": False,
                "message": "Name, email and password are required"
            }), 400

        name = str(name).strip()
        email = str(email).strip().lower()

        if not EMAIL_REGEX.match(email):
            return jsonify({
                "success": False,
                "message": "Invalid email format"
            }), 400

        # Password strength validation matching existing Node backend
        if len(password) < 8:
            return jsonify({
                "success": False,
                "message": "Password must be at least 8 characters long"
            }), 400

        if not any(char.isdigit() for char in password):
            return jsonify({
                "success": False,
                "message": "Password must contain at least one numeric digit"
            }), 400

        if not SPECIAL_CHAR_REGEX.search(password):
            return jsonify({
                "success": False,
                "message": "Password must contain at least one special character (e.g. !@#$%^&*)"
            }), 400

        # Public registration is strictly 'student'
        assigned_role = "student"

        existing = query_db("SELECT id FROM users WHERE email = %s", [email], one=True)
        if existing:
            return jsonify({
                "success": False,
                "message": "Email already registered"
            }), 409

        # Hash password with bcrypt
        salt = bcrypt.gensalt(10)
        hashed_password = bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

        last_id, _ = execute_db(
            "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s)",
            [name, email, hashed_password, assigned_role]
        )

        return jsonify({
            "success": True,
            "message": "User registered successfully",
            "userId": last_id,
            "role": assigned_role
        }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Registration failed"
        }), 500

def login():
    try:
        data = request.get_json() or {}
        email = data.get("email")
        password = data.get("password")

        if not email or not password:
            return jsonify({
                "success": False,
                "message": "Email and password are required"
            }), 400

        user = query_db("SELECT * FROM users WHERE email = %s", [str(email).strip().lower()], one=True)
        if not user:
            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401

        # Check password hash safely with legacy seed compatibility
        user_pw_hash = user["password"]
        if isinstance(user_pw_hash, str):
            user_pw_hash = user_pw_hash.encode("utf-8")

        is_match = False
        try:
            is_match = bcrypt.checkpw(password.encode("utf-8"), user_pw_hash)
        except Exception:
            if isinstance(user_pw_hash, bytes):
                is_match = password == user_pw_hash.decode("utf-8")
            else:
                is_match = password == str(user_pw_hash)

        if not is_match:
            return jsonify({
                "success": False,
                "message": "Invalid email or password"
            }), 401

        # Generate JWT
        payload = {
            "id": user["id"],
            "email": user["email"],
            "role": user["role"],
            "canteen_id": user.get("canteen_id"),
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=Config.JWT_EXPIRES_DAYS)
        }
        token = jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")

        return jsonify({
            "success": True,
            "message": "Login successful",
            "token": token,
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"],
                "canteen_id": user.get("canteen_id"),
                "wallet_balance": float(user.get("wallet_balance", 0.0))
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Login failed"
        }), 500

def get_me():
    try:
        user_id = g.user["id"]
        user = query_db(
            "SELECT id, name, email, role, wallet_balance FROM users WHERE id = %s",
            [user_id],
            one=True
        )

        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404

        if "wallet_balance" in user and user["wallet_balance"] is not None:
            user["wallet_balance"] = float(user["wallet_balance"])

        return jsonify({
            "success": True,
            "message": "Authenticated user",
            "user": user
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch user profile"
        }), 500
