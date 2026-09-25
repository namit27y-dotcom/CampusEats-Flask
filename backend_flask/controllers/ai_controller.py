from flask import request, jsonify, g
from backend_flask.services.db_service import query_db
from backend_flask.services.ai_service import (
    generate_recommendations,
    infer_is_veg,
    infer_prep_time
)

def get_ai_recommendations():
    try:
        user_id = g.user["id"]
        data = request.get_json() or {}
        prompt = data.get("prompt")
        budget = data.get("budget")
        dietary = data.get("dietary")
        canteen_id = data.get("canteenId")

        if not prompt or not isinstance(prompt, str) or len(prompt.strip()) == 0:
            return jsonify({
                "success": False,
                "message": "A prompt is required for AI recommendations"
            }), 400

        trimmed_prompt = prompt.strip()
        if len(trimmed_prompt) > 500:
            return jsonify({
                "success": False,
                "message": "Prompt is too long. Maximum allowed length is 500 characters."
            }), 400

        # Fetch menu items from DB
        menu_query = """
            SELECT 
                id, 
                canteen_id,
                name, 
                description, 
                price, 
                category, 
                COALESCE(stock_quantity, 100) AS stock_quantity
            FROM menu_items 
            WHERE is_available = 1"""
        params = []

        if canteen_id:
            menu_query += " AND canteen_id = %s"
            params.append(int(canteen_id))

        available_menu_items = query_db(menu_query, params)

        if not available_menu_items:
            return jsonify({
                "success": True,
                "data": {
                    "recommendations": [],
                    "summary": "No active menu items are currently available in the cafeteria."
                }
            }), 200

        # Student order history
        history_names = ""
        try:
            recent_history = query_db(
                """SELECT m.name, oi.quantity
                   FROM orders o
                   JOIN order_items oi ON o.id = oi.order_id
                   JOIN menu_items m ON oi.menu_item_id = m.id
                   WHERE o.user_id = %s AND o.status = 'completed'
                   ORDER BY o.created_at DESC
                   LIMIT 5""",
                [user_id]
            )
            if recent_history:
                history_names = ", ".join([h["name"] for h in recent_history if h.get("name")])
        except Exception:
            history_names = ""

        catalog_for_llm = [
            {
                "id": m["id"],
                "name": m["name"],
                "description": m.get("description") or "",
                "price": float(m["price"]),
                "category": m.get("category") or "general",
                "isVeg": infer_is_veg(m),
                "prepTimeMinutes": infer_prep_time(m)
            }
            for m in available_menu_items
        ]

        ai_result = generate_recommendations(
            trimmed_prompt,
            catalog_for_llm,
            budget=budget,
            dietary=dietary,
            history_names=history_names
        )

        valid_item_map = {m["id"]: m for m in available_menu_items}
        validated_recs = []

        for rec in (ai_result.get("recommendations") or []):
            menu_item_id = rec.get("menuItemId")
            if menu_item_id in valid_item_map:
                matched_item = valid_item_map[menu_item_id]
                validated_recs.append({
                    "menuItemId": matched_item["id"],
                    "name": matched_item["name"],
                    "price": float(matched_item["price"]),
                    "isVeg": infer_is_veg(matched_item),
                    "reason": str(rec.get("reason") or f"Fits your preferences at ₹{matched_item['price']}"),
                    "estimatedWaitMinutes": int(rec.get("estimatedWaitMinutes") or infer_prep_time(matched_item))
                })

        summary = ai_result.get("summary")
        if validated_recs:
            final_summary = summary or f"Found {len(validated_recs)} matching meal options."
        else:
            final_summary = summary or "No matching menu items found for your specific criteria."

        return jsonify({
            "success": True,
            "data": {
                "recommendations": validated_recs,
                "summary": final_summary
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "message": "Failed to generate AI recommendations"
        }), 500
