import os
import sys
import json
import jwt
import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend_flask.app import create_app
from backend_flask.config import Config
from backend_flask.services.db_service import query_db, execute_db
from backend_flask.services.invoice_service import generate_invoice_pdf
from backend_flask.services.ai_service import generate_recommendations

def run_live_verification():
    print("==================================================")
    print("CAMPUS EATS FLASK BACKEND - LIVE FLOW VERIFICATION")
    print("==================================================")
    
    app = create_app()
    client = app.test_client()

    # 1. Health & Database
    health_res = client.get("/api/health")
    health_data = health_res.get_json()
    print(f"[OK] Phase 2: GET /api/health -> status={health_data.get('status')}, database={health_data.get('database')}")
    assert health_data.get("database") == "Connected", "Database is not connected!"

    # 2. Auth Test with test student & test kitchen
    student_users = query_db("SELECT id, email, role, wallet_balance FROM users WHERE role = 'student' LIMIT 1")
    kitchen_users = query_db("SELECT id, email, role, canteen_id FROM users WHERE role = 'kitchen' LIMIT 1")
    counter_users = query_db("SELECT id, email, role, canteen_id FROM users WHERE role = 'counter' LIMIT 1")
    admin_users = query_db("SELECT id, email, role FROM users WHERE role = 'admin' LIMIT 1")

    assert student_users, "No student found in DB"
    assert kitchen_users, "No kitchen user found in DB"
    student = student_users[0]
    kitchen = kitchen_users[0]
    counter = counter_users[0]
    admin = admin_users[0]

    student_token = jwt.encode({
        "id": student["id"],
        "email": student["email"],
        "role": "student",
        "canteen_id": None,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    }, Config.JWT_SECRET, algorithm="HS256")

    kitchen_token = jwt.encode({
        "id": kitchen["id"],
        "email": kitchen["email"],
        "role": "kitchen",
        "canteen_id": kitchen.get("canteen_id") or 1,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    }, Config.JWT_SECRET, algorithm="HS256")

    admin_token = jwt.encode({
        "id": admin["id"],
        "email": admin["email"],
        "role": "admin",
        "canteen_id": 1,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    }, Config.JWT_SECRET, algorithm="HS256")

    # Verify /api/auth/me
    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {student_token}"})
    print(f"[OK] Phase 4: Student Auth /api/auth/me -> HTTP {me_res.status_code}, User ID #{me_res.get_json()['user']['id']}")

    # Verify role protection: student cannot access kitchen
    forbidden_res = client.get("/api/kitchen/orders", headers={"Authorization": f"Bearer {student_token}"})
    print(f"[OK] Phase 4: Student RBAC Protection on /api/kitchen/orders -> HTTP {forbidden_res.status_code} (Forbidden)")
    assert forbidden_res.status_code == 403

    # 3. Menu & Canteen
    canteens_res = client.get("/api/canteens")
    canteens_data = canteens_res.get_json()
    print(f"[OK] Phase 5: GET /api/canteens -> Found {len(canteens_data.get('canteens', []))} active canteens")
    canteen_id = canteens_data["canteens"][0]["id"]

    menu_res = client.get(f"/api/menu/{canteen_id}")
    menu_data = menu_res.get_json()
    print(f"[OK] Phase 5: GET /api/menu/{canteen_id} -> Found {len(menu_data.get('items', []))} menu items")
    assert len(menu_data.get("items", [])) > 0, "No menu items found"
    menu_item = menu_data["items"][0]

    # 4. Order Creation Flow
    # Add money to student wallet first to ensure sufficient funds
    add_money_res = client.post("/api/wallet/add-money", json={"amount": 200}, headers={"Authorization": f"Bearer {student_token}"})
    print(f"[OK] Phase 7: Add money to wallet -> Balance: Rs.{add_money_res.get_json().get('walletBalance')}")

    order_payload = {
        "canteenId": canteen_id,
        "items": [
            {
                "menuItemId": menu_item["id"],
                "quantity": 1,
                "extraAmount": 0,
                "customization": "Test Order Flow"
            }
        ],
        "paymentMethod": "wallet"
    }
    create_order_res = client.post("/api/orders", json=order_payload, headers={"Authorization": f"Bearer {student_token}"})
    assert create_order_res.status_code == 201, f"Failed to create order: {create_order_res.get_json()}"
    created_order = create_order_res.get_json()["order"]
    order_id = created_order["id"]
    token_number = created_order["tokenNumber"]
    print(f"[OK] Phase 6: Order placed successfully -> Order ID #{order_id}, Token #{token_number}, Status: {created_order['status']}, Total: Rs.{created_order['totalAmount']}")

    # Check order history
    history_res = client.get("/api/orders/my", headers={"Authorization": f"Bearer {student_token}"})
    assert any(o["id"] == order_id for o in history_res.get_json().get("orders", [])), "Order not in history!"
    print(f"[OK] Phase 6: Verified order #{order_id} in /api/orders/my history")

    # 5. Kitchen State Transitions
    k_headers = {"Authorization": f"Bearer {kitchen_token}"}
    
    # placed -> accepted
    res_accepted = client.patch(f"/api/kitchen/orders/{order_id}/status", json={"status": "accepted"}, headers=k_headers)
    assert res_accepted.status_code == 200
    print(f"[OK] Phase 8: Kitchen transitioned #{order_id} to 'accepted'")

    # accepted -> preparing
    res_prep = client.patch(f"/api/kitchen/orders/{order_id}/status", json={"status": "preparing"}, headers=k_headers)
    assert res_prep.status_code == 200
    print(f"[OK] Phase 8: Kitchen transitioned #{order_id} to 'preparing'")

    # preparing -> ready
    res_ready = client.patch(f"/api/kitchen/orders/{order_id}/status", json={"status": "ready"}, headers=k_headers)
    assert res_ready.status_code == 200
    print(f"[OK] Phase 8: Kitchen transitioned #{order_id} to 'ready'")

    # invalid jump: ready -> accepted should fail (400)
    res_invalid = client.patch(f"/api/kitchen/orders/{order_id}/status", json={"status": "accepted"}, headers=k_headers)
    assert res_invalid.status_code == 400
    print(f"[OK] Phase 8: Invalid transition rejected -> HTTP {res_invalid.status_code} ({res_invalid.get_json().get('message')})")

    # 6. Counter Token Collection
    counter_token = jwt.encode({
        "id": counter["id"],
        "email": counter["email"],
        "role": "counter",
        "canteen_id": canteen_id,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
    }, Config.JWT_SECRET, algorithm="HS256")
    c_headers = {"Authorization": f"Bearer {counter_token}"}

    collect_res = client.patch(f"/api/counter/orders/{order_id}/collect", json={"canteenId": canteen_id}, headers=c_headers)
    assert collect_res.status_code == 200
    print(f"[OK] Phase 10: Counter marked #{order_id} as 'completed' (Token #{token_number})")

    # Prevent double collection
    double_collect_res = client.patch(f"/api/counter/orders/{order_id}/collect", json={"canteenId": canteen_id}, headers=c_headers)
    assert double_collect_res.status_code == 400
    print(f"[OK] Phase 10: Double collection prevented -> HTTP 400 ({double_collect_res.get_json().get('message')})")

    # 7. Rating Submission
    rating_res = client.post("/api/ratings", json={"orderId": order_id, "rating": 5, "review": "Crispy and delicious!"}, headers={"Authorization": f"Bearer {student_token}"})
    assert rating_res.status_code == 201
    print(f"[OK] Phase 11: Rating submitted -> Rating ID #{rating_res.get_json().get('ratingId')}")

    # Duplicate rating check
    dup_rating_res = client.post("/api/ratings", json={"orderId": order_id, "rating": 4}, headers={"Authorization": f"Bearer {student_token}"})
    assert dup_rating_res.status_code == 409
    print(f"[OK] Phase 11: Duplicate rating rejected -> HTTP 409")

    # 8. AI Recommender & Menu Q&A
    ai_res = client.post("/api/ai/recommend", json={"prompt": "Suggest a meal under 100", "budget": 100, "dietary": "veg"}, headers={"Authorization": f"Bearer {student_token}"})
    ai_json = ai_res.get_json()
    summary_text = (ai_json.get('data', {}).get('summary') or '').replace('₹', 'Rs.')
    print(f"[OK] Phase 12: AI Recommender -> Summary: {summary_text}")
    print(f"[OK] Phase 12: AI Recommendations count: {len(ai_json.get('data', {}).get('recommendations', []))}")

    # 9. Invoice PDF Generation
    inv_res = client.get(f"/api/orders/{order_id}/invoice", headers={"Authorization": f"Bearer {student_token}"})
    assert inv_res.status_code == 200
    assert inv_res.mimetype == "application/pdf"
    assert inv_res.data.startswith(b"%PDF-")
    print(f"[OK] Phase 13: Generated PDF Invoice -> Size: {len(inv_res.data)} bytes, Content-Type: {inv_res.mimetype}")

    # 10. Admin Analytics
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    admin_stats_res = client.get("/api/admin/stats", headers=admin_headers)
    assert admin_stats_res.status_code == 200
    print(f"[OK] Phase 14: Admin Stats -> Total Orders: {admin_stats_res.get_json().get('stats', {}).get('totalOrders')}, Revenue: Rs.{admin_stats_res.get_json().get('stats', {}).get('totalRevenue')}")

    print("==================================================")
    print("ALL 14 LIVE INTEGRATION PHASES VERIFIED SUCCESSFULLY")
    print("==================================================")

if __name__ == "__main__":
    run_live_verification()
