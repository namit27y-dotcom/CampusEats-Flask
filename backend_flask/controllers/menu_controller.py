from flask import request, jsonify
from backend_flask.services.db_service import query_db, execute_db

def get_menu_items(canteen_id):
    try:
        items = query_db(
            """SELECT * FROM menu_items
               WHERE canteen_id = %s AND is_available = TRUE
               ORDER BY category, id""",
            [canteen_id]
        )
        return jsonify({
            "success": True,
            "items": items
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch menu items"
        }), 500

def add_menu_item():
    try:
        data = request.get_json() or {}
        canteen_id = data.get("canteenId")
        name = data.get("name")
        description = data.get("description")
        price = data.get("price")
        category = data.get("category", "snacks")
        image_url = data.get("imageUrl")
        is_available = data.get("isAvailable", True)

        if not canteen_id or not name or price is None:
            return jsonify({
                "success": False,
                "message": "Canteen ID, name, and price are required"
            }), 400

        last_id, _ = execute_db(
            """INSERT INTO menu_items
               (canteen_id, name, description, price, category, image_url, is_available)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            [
                canteen_id,
                name,
                description or None,
                price,
                category,
                image_url or None,
                bool(is_available)
            ]
        )

        return jsonify({
            "success": True,
            "message": "Menu item added successfully",
            "itemId": last_id
        }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to add menu item"
        }), 500

def update_menu_item(id):
    try:
        data = request.get_json() or {}
        name = data.get("name")
        description = data.get("description")
        price = data.get("price")
        category = data.get("category")
        image_url = data.get("imageUrl")
        is_available = data.get("isAvailable")

        _, affected = execute_db(
            """UPDATE menu_items
               SET name = COALESCE(%s, name),
                   description = COALESCE(%s, description),
                   price = COALESCE(%s, price),
                   category = COALESCE(%s, category),
                   image_url = COALESCE(%s, image_url),
                   is_available = COALESCE(%s, is_available)
               WHERE id = %s""",
            [name, description, price, category, image_url, is_available, id]
        )

        if affected == 0:
            # Check if item exists
            existing = query_db("SELECT id FROM menu_items WHERE id = %s", [id], one=True)
            if not existing:
                return jsonify({
                    "success": False,
                    "message": "Menu item not found"
                }), 404

        return jsonify({
            "success": True,
            "message": "Menu item updated successfully"
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to update menu item"
        }), 500

def toggle_availability(id):
    try:
        data = request.get_json() or {}
        is_available = bool(data.get("isAvailable"))

        _, affected = execute_db(
            "UPDATE menu_items SET is_available = %s WHERE id = %s",
            [is_available, id]
        )

        if affected == 0:
            existing = query_db("SELECT id FROM menu_items WHERE id = %s", [id], one=True)
            if not existing:
                return jsonify({
                    "success": False,
                    "message": "Menu item not found"
                }), 404

        return jsonify({
            "success": True,
            "message": "Menu item availability updated",
            "isAvailable": is_available
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to update availability"
        }), 500

def update_stock(id):
    try:
        data = request.get_json() or {}
        stock_quantity = data.get("stockQuantity")
        is_tracked = data.get("isTracked")
        is_available = data.get("isAvailable")

        if stock_quantity is not None and (float(stock_quantity) < 0):
            return jsonify({
                "success": False,
                "message": "Stock quantity must be a non-negative number"
            }), 400

        item = query_db(
            "SELECT id, name, is_available, stock_quantity, is_tracked FROM menu_items WHERE id = %s",
            [id],
            one=True
        )

        if not item:
            return jsonify({
                "success": False,
                "message": "Menu item not found"
            }), 404

        new_stock = int(stock_quantity) if stock_quantity is not None else int(item.get("stock_quantity") or 100)
        new_tracked = 1 if is_tracked is True or is_tracked == 1 else (0 if is_tracked is False or is_tracked == 0 else int(item.get("is_tracked") or 0))
        
        current_avail = int(item.get("is_available", 1))
        if is_available is not None:
            new_available = 1 if is_available else 0
        else:
            new_available = current_avail

        if new_tracked == 1 and new_stock == 0:
            new_available = 0
        elif new_stock > 0 and is_available is None and current_avail == 0:
            new_available = 1

        execute_db(
            """UPDATE menu_items
               SET stock_quantity = %s,
                   is_tracked = %s,
                   is_available = %s
               WHERE id = %s""",
            [new_stock, new_tracked, new_available, id]
        )

        return jsonify({
            "success": True,
            "message": f"Stock updated for '{item['name']}'",
            "data": {
                "id": int(id),
                "stockQuantity": new_stock,
                "isTracked": bool(new_tracked),
                "isAvailable": bool(new_available)
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to update stock"
        }), 500
