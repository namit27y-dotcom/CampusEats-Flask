from flask import request, jsonify, g
from backend_flask.services.db_service import query_db, execute_db
from backend_flask.extensions import socketio

def get_counter_orders():
    try:
        orders = query_db(
            """SELECT
                o.id,
                o.user_id,
                u.name AS student_name,
                o.canteen_id,
                c.name AS canteen_name,
                o.total_amount,
                o.token_number,
                o.status,
                o.payment_method,
                o.payment_status,
                o.payment_transaction_id,
                o.created_at
             FROM orders o
             JOIN users u ON o.user_id = u.id
             JOIN canteens c ON o.canteen_id = c.id
             WHERE o.status IN ('ready', 'completed')
             ORDER BY o.created_at DESC"""
        )

        if not orders:
            return jsonify({
                "success": True,
                "orders": []
            }), 200

        order_ids = [o["id"] for o in orders]
        order_items = query_db(
            """SELECT
                oi.id,
                oi.order_id,
                oi.menu_item_id,
                oi.quantity,
                oi.price,
                oi.customization,
                oi.extra_amount,
                m.name,
                m.is_available
             FROM order_items oi
             JOIN menu_items m ON oi.menu_item_id = m.id
             WHERE oi.order_id IN (%s)""",
            [order_ids]
        )

        items_by_order_id = {}
        for item in order_items:
            oid = item["order_id"]
            if oid not in items_by_order_id:
                items_by_order_id[oid] = []
            items_by_order_id[oid].append({
                "id": item["id"],
                "menu_item_id": item["menu_item_id"],
                "name": item["name"],
                "quantity": int(item["quantity"]),
                "price": float(item["price"]),
                "customization": item["customization"],
                "extra_amount": float(item.get("extra_amount") or 0.0)
            })

        orders_with_items = []
        for o in orders:
            orders_with_items.append({
                **o,
                "total_amount": float(o["total_amount"]),
                "created_at": o["created_at"].isoformat() if hasattr(o["created_at"], "isoformat") else str(o["created_at"]),
                "items": items_by_order_id.get(o["id"], [])
            })

        return jsonify({
            "success": True,
            "orders": orders_with_items
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch counter orders"
        }), 500

def mark_order_collected(id):
    try:
        data = request.get_json() or {}
        canteen_id = data.get("canteenId")

        order = query_db(
            "SELECT id, token_number, canteen_id, user_id, status FROM orders WHERE id = %s",
            [id],
            one=True
        )

        if not order:
            return jsonify({
                "success": False,
                "message": "Order not found"
            }), 404

        user = g.user
        staff_canteen_id = user.get("canteen_id") or request.headers.get("x-canteen-id") or canteen_id

        if user.get("role") == "counter" and staff_canteen_id:
            if int(order["canteen_id"]) != int(staff_canteen_id):
                return jsonify({
                    "success": False,
                    "message": f"Unauthorized: Counter staff is not authorized to collect orders for Canteen #{order['canteen_id']} (Assigned: Canteen #{staff_canteen_id})"
                }), 403

        if order["status"] == "completed":
            return jsonify({
                "success": False,
                "message": f"Token #{order['token_number']} has already been collected and completed."
            }), 400

        if order["status"] != "ready":
            return jsonify({
                "success": False,
                "message": f"Cannot collect order #{order['id']} with status '{order['status']}'. Food must be marked 'ready' by kitchen first."
            }), 400

        _, affected = execute_db(
            """UPDATE orders
               SET status = 'completed'
               WHERE id = %s AND status = 'ready'""",
            [id]
        )

        if affected == 0:
            return jsonify({
                "success": False,
                "message": "Order could not be collected. It may have already been collected concurrently or is no longer ready."
            }), 409

        try:
            socketio.emit(
                "orderStatusUpdated",
                {"orderId": int(id), "status": "completed"},
                to=f"order_{id}"
            )
            socketio.emit(
                "orderStatusUpdated",
                {"orderId": int(id), "status": "completed"},
                to=f"canteen_{order['canteen_id']}"
            )
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": f"Token #{order['token_number']} verified and marked as collected/completed",
            "orderId": int(id),
            "tokenNumber": order["token_number"],
            "status": "completed"
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to mark order collected"
        }), 500
