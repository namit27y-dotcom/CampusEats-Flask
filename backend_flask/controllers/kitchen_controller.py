from flask import request, jsonify, g
from backend_flask.services.db_service import query_db, execute_db
from backend_flask.extensions import socketio

def get_kitchen_orders():
    try:
        user = g.user
        user_role = str(user.get("role", "")).lower()
        canteen_id = None

        if user_role == "kitchen":
            user_row = query_db(
                "SELECT canteen_id FROM users WHERE id = %s",
                [user["id"]],
                one=True
            )
            canteen_id = user_row.get("canteen_id") if user_row else user.get("canteen_id")

            if not canteen_id:
                return jsonify({
                    "success": False,
                    "message": "Kitchen staff is not assigned to any canteen"
                }), 403

        elif user_role == "admin":
            req_canteen = request.args.get("canteen_id")
            if req_canteen:
                canteen_id = int(req_canteen)

        query = """
            SELECT
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
             WHERE o.status IN ('placed', 'accepted', 'preparing', 'ready')
        """
        params = []

        if canteen_id:
            query += " AND o.canteen_id = %s"
            params.append(canteen_id)

        query += " ORDER BY o.created_at ASC"

        orders = query_db(query, params)

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
            "message": "Failed to fetch kitchen orders"
        }), 500

def update_order_status(id):
    try:
        data = request.get_json() or {}
        status = data.get("status")

        allowed_statuses = ["accepted", "preparing", "ready", "completed", "cancelled"]
        if status not in allowed_statuses:
            return jsonify({
                "success": False,
                "message": f"Invalid order status '{status}'"
            }), 400

        order = query_db(
            "SELECT id, status, canteen_id, user_id FROM orders WHERE id = %s",
            [id],
            one=True
        )

        if not order:
            return jsonify({
                "success": False,
                "message": "Order not found"
            }), 404

        user_role = str(g.user.get("role", "")).lower()
        if user_role == "kitchen":
            user_row = query_db(
                "SELECT canteen_id FROM users WHERE id = %s",
                [g.user["id"]],
                one=True
            )
            staff_canteen_id = user_row.get("canteen_id") if user_row else g.user.get("canteen_id")

            if not staff_canteen_id or str(order["canteen_id"]) != str(staff_canteen_id):
                return jsonify({
                    "success": False,
                    "message": "Unauthorized: Kitchen staff cannot update orders belonging to another canteen"
                }), 403

        current_status = order["status"]

        # Idempotency
        if current_status == status:
            return jsonify({
                "success": True,
                "message": f"Order #{id} is already in status '{status}'",
                "orderId": int(id),
                "status": status
            }), 200

        # State transitions
        valid_transitions = {
            "placed": ["accepted", "cancelled"],
            "accepted": ["preparing", "cancelled"],
            "preparing": ["ready"],
            "ready": ["completed"],
            "completed": [],
            "cancelled": []
        }

        allowed_next = valid_transitions.get(current_status, [])
        if status not in allowed_next:
            return jsonify({
                "success": False,
                "message": f"Invalid status transition: Cannot change order from '{current_status}' to '{status}'",
                "currentStatus": current_status,
                "allowedTransitions": allowed_next,
                "orderId": int(id)
            }), 400

        execute_db("UPDATE orders SET status = %s WHERE id = %s", [status, id])

        try:
            socketio.emit(
                "orderStatusUpdated",
                {"orderId": int(id), "status": status},
                to=f"order_{id}"
            )
            socketio.emit(
                "orderStatusUpdated",
                {"orderId": int(id), "status": status},
                to=f"canteen_{order['canteen_id']}"
            )
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": f"Order status updated to '{status}' successfully",
            "orderId": int(id),
            "status": status
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Failed to update order status: {str(e)}"
        }), 500
