from flask import jsonify
from backend_flask.services.db_service import query_db

def get_admin_stats():
    try:
        orders_count = query_db("SELECT COUNT(*) AS totalOrders FROM orders", one=True) or {}
        revenue_count = query_db(
            "SELECT COALESCE(SUM(total_amount), 0) AS totalRevenue FROM orders WHERE status != 'cancelled'",
            one=True
        ) or {}
        active_count = query_db(
            "SELECT COUNT(*) AS activeOrders FROM orders WHERE status IN ('placed', 'accepted', 'preparing', 'ready')",
            one=True
        ) or {}
        completed_count = query_db(
            "SELECT COUNT(*) AS completedOrders FROM orders WHERE status = 'completed'",
            one=True
        ) or {}
        cancelled_count = query_db(
            "SELECT COUNT(*) AS cancelledOrders FROM orders WHERE status = 'cancelled'",
            one=True
        ) or {}
        today_count = query_db(
            "SELECT COUNT(*) AS todayOrders, COALESCE(SUM(CASE WHEN status != 'cancelled' THEN total_amount ELSE 0 END), 0) AS todayRevenue FROM orders WHERE DATE(created_at) = CURRENT_DATE()",
            one=True
        ) or {}
        users_count = query_db("SELECT COUNT(*) AS totalUsers FROM users", one=True) or {}

        return jsonify({
            "success": True,
            "stats": {
                "totalOrders": int(orders_count.get("totalOrders") or 0),
                "totalRevenue": float(revenue_count.get("totalRevenue") or 0.0),
                "activeOrders": int(active_count.get("activeOrders") or 0),
                "completedOrders": int(completed_count.get("completedOrders") or 0),
                "cancelledOrders": int(cancelled_count.get("cancelledOrders") or 0),
                "todayOrders": int(today_count.get("todayOrders") or 0),
                "todayRevenue": float(today_count.get("todayRevenue") or 0.0),
                "totalUsers": int(users_count.get("totalUsers") or 0)
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch admin stats"
        }), 500

def get_daily_sales_analytics():
    try:
        rows = query_db(
            """SELECT 
                DATE_FORMAT(created_at, '%%Y-%%m-%%d') AS date,
                COUNT(*) AS total_orders,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) AS completed_orders,
                COALESCE(SUM(CASE WHEN status != 'cancelled' THEN total_amount ELSE 0 END), 0) AS revenue
             FROM orders
             WHERE created_at >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
             GROUP BY DATE_FORMAT(created_at, '%%Y-%%m-%%d')
             ORDER BY date ASC"""
        )

        return jsonify({
            "success": True,
            "data": [
                {
                    "date": r["date"],
                    "orders": int(r["total_orders"]),
                    "completedOrders": int(r["completed_orders"]),
                    "revenue": float(r["revenue"])
                }
                for r in rows
            ]
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch daily sales analytics"
        }), 500

def get_peak_hours_analytics():
    try:
        rows = query_db(
            """SELECT 
                HOUR(created_at) AS hour,
                COUNT(*) AS order_count,
                COALESCE(SUM(CASE WHEN status != 'cancelled' THEN total_amount ELSE 0 END), 0) AS revenue
             FROM orders
             GROUP BY HOUR(created_at)
             ORDER BY hour ASC"""
        )

        return jsonify({
            "success": True,
            "data": [
                {
                    "hour": int(r["hour"]),
                    "orderCount": int(r["order_count"]),
                    "revenue": float(r["revenue"])
                }
                for r in rows
            ]
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch peak hours analytics"
        }), 500

def get_top_dishes_analytics():
    try:
        rows = query_db(
            """SELECT 
                m.id,
                m.name,
                COALESCE(m.category, 'General') AS category,
                SUM(oi.quantity) AS total_sold,
                COALESCE(SUM(oi.quantity * oi.price), 0) AS total_revenue
             FROM order_items oi
             JOIN menu_items m ON oi.menu_item_id = m.id
             JOIN orders o ON oi.order_id = o.id
             WHERE o.status != 'cancelled'
             GROUP BY m.id, m.name, m.category
             ORDER BY total_sold DESC
             LIMIT 10"""
        )

        return jsonify({
            "success": True,
            "data": [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "category": r["category"],
                    "totalSold": int(r["total_sold"]),
                    "totalRevenue": float(r["total_revenue"])
                }
                for r in rows
            ]
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch top dishes analytics"
        }), 500

def get_canteens_analytics():
    try:
        rows = query_db(
            """SELECT 
                c.id,
                c.name,
                c.location,
                COUNT(o.id) AS total_orders,
                COUNT(CASE WHEN o.status IN ('placed', 'accepted', 'preparing', 'ready') THEN 1 END) AS active_orders,
                COUNT(CASE WHEN o.status = 'completed' THEN 1 END) AS completed_orders,
                COALESCE(SUM(CASE WHEN o.status != 'cancelled' THEN o.total_amount ELSE 0 END), 0) AS total_revenue
             FROM canteens c
             LEFT JOIN orders o ON c.id = o.canteen_id
             GROUP BY c.id, c.name, c.location
             ORDER BY total_revenue DESC"""
        )

        return jsonify({
            "success": True,
            "data": [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "location": r["location"],
                    "totalOrders": int(r["total_orders"]),
                    "activeOrders": int(r["active_orders"]),
                    "completedOrders": int(r["completed_orders"]),
                    "totalRevenue": float(r["total_revenue"])
                }
                for r in rows
            ]
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch canteens analytics"
        }), 500

def get_fulfillment_analytics():
    try:
        orders_data = query_db(
            """SELECT 
                COUNT(CASE WHEN status = 'completed' THEN 1 END) AS total_completed,
                COUNT(CASE WHEN status = 'cancelled' THEN 1 END) AS total_cancelled,
                COUNT(*) AS total_processed
             FROM orders""",
            one=True
        ) or {}

        # Safely query average prep time if column exists, else default to 8
        try:
            prep_data = query_db(
                """SELECT AVG(m.prep_time) AS avg_estimated_prep_time
                   FROM order_items oi
                   JOIN menu_items m ON oi.menu_item_id = m.id
                   JOIN orders o ON oi.order_id = o.id
                   WHERE o.status = 'completed'""",
                one=True
            )
            avg_prep = float(prep_data.get("avg_estimated_prep_time") or 8.0) if prep_data else 8.0
        except Exception:
            avg_prep = 8.0

        total_proc = int(orders_data.get("total_processed") or 0)
        total_comp = int(orders_data.get("total_completed") or 0)
        completion_rate = round((total_comp / total_proc) * 100, 1) if total_proc > 0 else 0.0

        return jsonify({
            "success": True,
            "data": {
                "totalCompleted": total_comp,
                "totalCancelled": int(orders_data.get("total_cancelled") or 0),
                "totalProcessed": total_proc,
                "completionRate": completion_rate,
                "avgPrepTimeMinutes": avg_prep
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch fulfillment analytics"
        }), 500

def get_admin_users():
    try:
        users = query_db(
            "SELECT id, name, email, role, wallet_balance, created_at FROM users ORDER BY id DESC"
        )

        formatted_users = []
        for u in users:
            formatted_users.append({
                **u,
                "wallet_balance": float(u["wallet_balance"]) if u["wallet_balance"] is not None else 0.0,
                "created_at": u["created_at"].isoformat() if hasattr(u["created_at"], "isoformat") else str(u["created_at"])
            })

        return jsonify({
            "success": True,
            "users": formatted_users
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch admin users"
        }), 500

def get_admin_orders():
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
                m.name
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
            "message": "Failed to fetch admin orders"
        }), 500
