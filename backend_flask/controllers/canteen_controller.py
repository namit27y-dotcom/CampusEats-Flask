from flask import jsonify
from backend_flask.services.db_service import query_db

def get_canteens():
    try:
        canteens = query_db(
            "SELECT * FROM canteens WHERE is_active = TRUE ORDER BY id DESC"
        )
        return jsonify({
            "success": True,
            "canteens": canteens
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch canteens"
        }), 500

def get_canteen_by_id(id):
    try:
        canteen = query_db(
            "SELECT * FROM canteens WHERE id = %s AND is_active = TRUE",
            [id],
            one=True
        )
        if not canteen:
            return jsonify({
                "success": False,
                "message": "Canteen not found"
            }), 404

        return jsonify({
            "success": True,
            "canteen": canteen
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch canteen"
        }), 500
