import time
from flask import request, jsonify, g, send_file, Response
from backend_flask.services.db_service import DBTransaction, query_db
from backend_flask.services.invoice_service import generate_invoice_pdf
from backend_flask.extensions import socketio

def create_order():
    try:
        user_id = g.user["id"]
        data = request.get_json() or {}
        canteen_id = data.get("canteenId")
        items = data.get("items")
        payment_method = data.get("paymentMethod", "wallet")

        if not canteen_id or not items or not isinstance(items, list) or len(items) == 0:
            return jsonify({
                "success": False,
                "message": "Canteen and items are required"
            }), 400

        if payment_method not in ["upi", "wallet", "card", "cash"]:
            return jsonify({
                "success": False,
                "message": "Invalid payment method"
            }), 400

        with DBTransaction() as tx:
            subtotal = 0.0
            order_items = []

            for item in items:
                menu_item_id = item.get("menuItemId")
                quantity = item.get("quantity")

                if not menu_item_id or not quantity or int(quantity) <= 0:
                    return jsonify({
                        "success": False,
                        "message": "Invalid order item"
                    }), 400

                quantity = int(quantity)

                menu_rows, _, _ = tx.query(
                    """SELECT id, name, price, is_available,
                              COALESCE(stock_quantity, 100) AS stock_quantity,
                              COALESCE(is_tracked, 0) AS is_tracked
                       FROM menu_items
                       WHERE id = %s AND canteen_id = %s
                       FOR UPDATE""",
                    [menu_item_id, canteen_id]
                )

                if not menu_rows or not menu_rows[0]["is_available"]:
                    return jsonify({
                        "success": False,
                        "message": f"Menu item '{menu_item_id}' is not available"
                    }), 400

                menu_item = menu_rows[0]

                if menu_item["is_tracked"] and menu_item["stock_quantity"] < quantity:
                    return jsonify({
                        "success": False,
                        "message": f"Insufficient stock for '{menu_item['name']}'. Requested: {quantity}, Available: {menu_item['stock_quantity']}",
                        "availableStock": menu_item["stock_quantity"]
                    }), 400

                if menu_item["is_tracked"]:
                    _, _, affected = tx.query(
                        """UPDATE menu_items
                           SET stock_quantity = stock_quantity - %s,
                               is_available = CASE WHEN stock_quantity - %s <= 0 THEN 0 ELSE is_available END
                           WHERE id = %s AND stock_quantity >= %s""",
                        [quantity, quantity, menu_item_id, quantity]
                    )

                    if affected == 0:
                        return jsonify({
                            "success": False,
                            "message": f"Stock for '{menu_item['name']}' was depleted concurrently. Please try again."
                        }), 400

                base_price = float(menu_item["price"])
                extra_amount = max(0.0, float(item.get("extraAmount") or 0))

                if extra_amount > 100:
                    return jsonify({
                        "success": False,
                        "message": "Invalid customization amount"
                    }), 400

                unit_price = base_price + extra_amount
                subtotal += unit_price * quantity

                order_items.append({
                    "menuItemId": menu_item_id,
                    "name": menu_item["name"],
                    "quantity": quantity,
                    "price": unit_price,
                    "extraAmount": extra_amount,
                    "customization": item.get("customization") or None
                })

            discount = 15.0 if subtotal >= 100 else 0.0
            taxes = 0.0
            total_amount = max(0.0, subtotal - discount + taxes)
            token_number = f"T{str(int(time.time() * 1000))[-6:]}"

            payment_status = "pending"
            payment_txn_id = None
            wallet_balance = None

            if payment_method == "wallet":
                user_rows, _, _ = tx.query(
                    "SELECT wallet_balance FROM users WHERE id = %s FOR UPDATE",
                    [user_id]
                )

                if not user_rows:
                    return jsonify({
                        "success": False,
                        "message": "User not found"
                    }), 404

                wallet_balance = float(user_rows[0].get("wallet_balance") or 0.0)

                if wallet_balance < total_amount:
                    return jsonify({
                        "success": False,
                        "message": "Insufficient wallet balance",
                        "walletBalance": wallet_balance,
                        "requiredAmount": total_amount
                    }), 400

                tx.query(
                    "UPDATE users SET wallet_balance = wallet_balance - %s WHERE id = %s",
                    [total_amount, user_id]
                )

                wallet_balance -= total_amount
                payment_status = "paid"
                payment_txn_id = f"CW-WALLET-{int(time.time() * 1000)}"

                tx.query(
                    """INSERT INTO wallet_transactions
                       (user_id, amount, type, description)
                       VALUES (%s, %s, 'debit', %s)""",
                    [user_id, total_amount, "Payment for order"]
                )

            elif payment_method == "upi":
                payment_status = "paid"
                payment_txn_id = f"DEMO-UPI-{int(time.time() * 1000)}"

            elif payment_method == "card":
                payment_status = "paid"
                payment_txn_id = f"DEMO-CARD-{int(time.time() * 1000)}"

            elif payment_method == "cash":
                payment_status = "pending"
                payment_txn_id = None

            _, order_id, _ = tx.query(
                """INSERT INTO orders
                   (user_id, canteen_id, total_amount, token_number, status, payment_method, payment_status, payment_transaction_id)
                   VALUES (%s, %s, %s, %s, 'placed', %s, %s, %s)""",
                [
                    user_id,
                    canteen_id,
                    total_amount,
                    token_number,
                    payment_method,
                    payment_status,
                    payment_txn_id
                ]
            )

            for item in order_items:
                tx.query(
                    """INSERT INTO order_items
                       (order_id, menu_item_id, quantity, price, customization, extra_amount)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    [
                        order_id,
                        item["menuItemId"],
                        item["quantity"],
                        item["price"],
                        item["customization"],
                        item["extraAmount"]
                    ]
                )

        # Broadcast Socket.IO event
        try:
            created_order = query_db(
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
                 WHERE o.id = %s""",
                [order_id],
                one=True
            )

            if created_order:
                socketio.emit(
                    "newOrderCreated",
                    {**created_order, "items": order_items},
                    to=f"canteen_{canteen_id}"
                )
        except Exception as e:
            pass

        return jsonify({
            "success": True,
            "message": "Order placed successfully",
            "order": {
                "id": order_id,
                "tokenNumber": token_number,
                "subtotal": subtotal,
                "discount": discount,
                "taxes": taxes,
                "totalAmount": total_amount,
                "status": "placed",
                "paymentMethod": payment_method,
                "paymentStatus": payment_status,
                "paymentTransactionId": payment_txn_id
            },
            "walletBalance": wallet_balance
        }), 201

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"Failed to place order: {str(e)}"
        }), 500

def get_my_orders():
    try:
        user_id = g.user["id"]
        orders = query_db(
            """SELECT
                o.id,
                o.canteen_id,
                c.name AS canteen_name,
                o.total_amount,
                o.token_number,
                o.status,
                o.payment_method,
                o.payment_status,
                o.payment_transaction_id,
                o.created_at,
                r.rating AS user_rating,
                r.review AS user_review
             FROM orders o
             JOIN canteens c ON o.canteen_id = c.id
             LEFT JOIN ratings r ON o.id = r.order_id AND r.user_id = o.user_id
             WHERE o.user_id = %s
             ORDER BY o.created_at DESC""",
            [user_id]
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

        orders_with_details = []
        for o in orders:
            orders_with_details.append({
                **o,
                "total_amount": float(o["total_amount"]),
                "created_at": o["created_at"].isoformat() if hasattr(o["created_at"], "isoformat") else str(o["created_at"]),
                "items": items_by_order_id.get(o["id"], [])
            })

        return jsonify({
            "success": True,
            "orders": orders_with_details
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch orders"
        }), 500

def cancel_order(id):
    try:
        user_id = g.user["id"]
        user_role = g.user["role"]

        with DBTransaction() as tx:
            orders, _, _ = tx.query(
                "SELECT * FROM orders WHERE id = %s FOR UPDATE",
                [id]
            )

            if not orders:
                return jsonify({
                    "success": False,
                    "message": "Order not found"
                }), 404

            order = orders[0]

            # Ownership check
            if user_role == "student" and int(order["user_id"]) != int(user_id):
                return jsonify({
                    "success": False,
                    "message": "Access denied. You cannot cancel another student's order."
                }), 403

            if order["status"] == "cancelled":
                return jsonify({
                    "success": False,
                    "message": "Order is already cancelled"
                }), 400

            if order["status"] in ["preparing", "ready", "completed"]:
                return jsonify({
                    "success": False,
                    "message": f"Cannot cancel order in '{order['status']}' status. Food is already in preparation or completed."
                }), 400

            refund_processed = False
            new_wallet_balance = None

            # Schema-compatible wallet credit transaction for refund
            if order["payment_method"] == "wallet" and order["payment_status"] == "paid":
                refund_desc = f"Refund for cancelled order #{order['id']} (Token {order['token_number']})"
                existing_refund, _, _ = tx.query(
                    "SELECT id FROM wallet_transactions WHERE user_id = %s AND description LIKE %s",
                    [order["user_id"], f"%#{order['id']}%"]
                )

                if not existing_refund:
                    user_rows, _, _ = tx.query(
                        "SELECT wallet_balance FROM users WHERE id = %s FOR UPDATE",
                        [order["user_id"]]
                    )

                    if user_rows:
                        refund_amount = float(order["total_amount"])
                        tx.query(
                            "UPDATE users SET wallet_balance = wallet_balance + %s WHERE id = %s",
                            [refund_amount, order["user_id"]]
                        )
                        tx.query(
                            """INSERT INTO wallet_transactions
                               (user_id, amount, type, description)
                               VALUES (%s, %s, 'credit', %s)""",
                            [order["user_id"], refund_amount, refund_desc]
                        )
                        new_wallet_balance = float(user_rows[0].get("wallet_balance") or 0.0) + refund_amount
                        refund_processed = True

            # Update order status to cancelled
            tx.query("UPDATE orders SET status = 'cancelled' WHERE id = %s", [id])

        # Socket emissions
        try:
            socketio.emit(
                "orderStatusUpdated",
                {"orderId": int(id), "status": "cancelled"},
                to=f"order_{id}"
            )
            socketio.emit(
                "orderStatusUpdated",
                {"orderId": int(id), "status": "cancelled"},
                to=f"canteen_{order['canteen_id']}"
            )
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": "Order cancelled successfully",
            "orderId": int(id),
            "status": "cancelled",
            "refundProcessed": refund_processed,
            "walletBalance": new_wallet_balance
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to cancel order"
        }), 500

def get_order_invoice(id):
    try:
        user = g.user
        orders = query_db(
            """SELECT 
                o.id,
                o.user_id,
                u.name AS student_name,
                u.email AS student_email,
                o.canteen_id,
                c.name AS canteen_name,
                c.location AS canteen_location,
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
             WHERE o.id = %s""",
            [id]
        )

        if not orders:
            return jsonify({
                "success": False,
                "message": "Order not found"
            }), 404

        order = orders[0]
        is_owner = int(order["user_id"]) == int(user["id"])
        is_staff_or_admin = str(user.get("role", "")).lower() in ["admin", "kitchen", "counter"]

        if not is_owner and not is_staff_or_admin:
            return jsonify({
                "success": False,
                "message": "Access denied. You are not authorized to view this invoice."
            }), 403

        items = query_db(
            """SELECT 
                oi.id,
                oi.menu_item_id,
                m.name,
                oi.quantity,
                oi.price,
                oi.customization,
                oi.extra_amount
             FROM order_items oi
             JOIN menu_items m ON oi.menu_item_id = m.id
             WHERE oi.order_id = %s""",
            [id]
        )

        pdf_stream = generate_invoice_pdf(order, items)
        filename = f"CampusEats_Invoice_{order.get('token_number') or order.get('id')}.pdf"

        return Response(
            pdf_stream.getvalue(),
            mimetype="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename=\"{filename}\""
            }
        )

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to generate invoice receipt"
        }), 500
