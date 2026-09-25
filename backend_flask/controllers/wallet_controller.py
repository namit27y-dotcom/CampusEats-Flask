from flask import request, jsonify, g
from backend_flask.services.db_service import DBTransaction, query_db

def get_wallet_balance():
    try:
        user_id = g.user["id"]
        user = query_db(
            "SELECT wallet_balance FROM users WHERE id = %s",
            [user_id],
            one=True
        )

        if not user:
            return jsonify({
                "success": False,
                "message": "User not found"
            }), 404

        balance = float(user.get("wallet_balance") or 0.0)
        return jsonify({
            "success": True,
            "walletBalance": balance
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch wallet balance"
        }), 500

def add_money():
    try:
        user_id = g.user["id"]
        data = request.get_json() or {}
        amount = data.get("amount")

        if not amount or float(amount) <= 0:
            return jsonify({
                "success": False,
                "message": "Enter a valid amount"
            }), 400

        money = float(amount)

        with DBTransaction() as tx:
            tx.query(
                "UPDATE users SET wallet_balance = wallet_balance + %s WHERE id = %s",
                [money, user_id]
            )

            tx.query(
                """INSERT INTO wallet_transactions
                   (user_id, amount, type, description)
                   VALUES (%s, %s, 'credit', %s)""",
                [user_id, money, "Money added to wallet"]
            )

            user_rows, _, _ = tx.query(
                "SELECT wallet_balance FROM users WHERE id = %s",
                [user_id]
            )

        new_balance = float(user_rows[0].get("wallet_balance") or 0.0) if user_rows else 0.0

        return jsonify({
            "success": True,
            "message": "Money added successfully",
            "walletBalance": new_balance
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to add money"
        }), 500

def get_transactions():
    try:
        user_id = g.user["id"]
        transactions = query_db(
            """SELECT id, user_id, amount, type, description, created_at
               FROM wallet_transactions
               WHERE user_id = %s
               ORDER BY created_at DESC""",
            [user_id]
        )

        formatted_transactions = []
        for t in transactions:
            formatted_transactions.append({
                **t,
                "amount": float(t["amount"]),
                "created_at": t["created_at"].isoformat() if hasattr(t["created_at"], "isoformat") else str(t["created_at"])
            })

        return jsonify({
            "success": True,
            "transactions": formatted_transactions
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to fetch wallet transactions"
        }), 500
