from flask import request, jsonify, g
from backend_flask.services.db_service import query_db, execute_db

def add_rating():
    try:
        user_id = g.user["id"]
        data = request.get_json() or {}
        order_id = data.get("orderId")
        rating = data.get("rating")
        review = data.get("review")

        if not order_id or not rating:
            return jsonify({
                "success": False,
                "message": "Order ID and rating are required"
            }), 400

        try:
            rating_num = int(rating)
            if rating_num < 1 or rating_num > 5:
                return jsonify({
                    "success": False,
                    "message": "Rating must be between 1 and 5"
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                "success": False,
                "message": "Rating must be between 1 and 5"
            }), 400

        order = query_db(
            "SELECT id, status FROM orders WHERE id = %s AND user_id = %s",
            [order_id, user_id],
            one=True
        )

        if not order:
            return jsonify({
                "success": False,
                "message": "Order not found"
            }), 404

        if order["status"] != "completed":
            return jsonify({
                "success": False,
                "message": "You can rate only completed orders"
            }), 400

        existing = query_db(
            "SELECT id FROM ratings WHERE order_id = %s AND user_id = %s",
            [order_id, user_id],
            one=True
        )

        if existing:
            return jsonify({
                "success": False,
                "message": "You have already rated this order"
            }), 409

        last_id, _ = execute_db(
            """INSERT INTO ratings (user_id, order_id, rating, review)
               VALUES (%s, %s, %s, %s)""",
            [user_id, order_id, rating_num, review or None]
        )

        return jsonify({
            "success": True,
            "message": "Rating added successfully",
            "ratingId": last_id
        }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to add rating"
        }), 500

def get_ratings():
    try:
        ratings = query_db(
            """SELECT
                r.id,
                r.user_id,
                u.name AS user_name,
                r.order_id,
                r.rating,
                r.review,
                r.created_at
             FROM ratings r
             JOIN users u ON r.user_id = u.id
             ORDER BY r.created_at DESC"""
        )

        formatted_ratings = []
        for r in ratings:
            formatted_ratings.append({
                **r,
                "rating": int(r["rating"]),
                "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"])
            })

        return jsonify({
            "success": True,
            "ratings": formatted_ratings
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch ratings"
        }), 500
