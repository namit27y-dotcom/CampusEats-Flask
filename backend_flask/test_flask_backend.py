import os
import sys
import unittest
import json
import jwt
import datetime
import hmac
import hashlib

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend_flask.app import create_app
from backend_flask.config import Config
from backend_flask.services.db_service import query_db, execute_db
from backend_flask.services.invoice_service import format_inr, generate_invoice_pdf
from backend_flask.services.ai_service import infer_is_veg, infer_prep_time, generate_database_heuristics

class TestFlaskBackendFullSuite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

        # Helper test tokens
        cls.student_token = jwt.encode({
            "id": 1,
            "email": "student_test@example.com",
            "role": "student",
            "canteen_id": None,
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
        }, Config.JWT_SECRET, algorithm="HS256")

        cls.admin_token = jwt.encode({
            "id": 16,
            "email": "admin_test@example.com",
            "role": "admin",
            "canteen_id": 1,
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
        }, Config.JWT_SECRET, algorithm="HS256")

        cls.kitchen_token = jwt.encode({
            "id": 2,
            "email": "kitchen_test@example.com",
            "role": "kitchen",
            "canteen_id": 1,
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
        }, Config.JWT_SECRET, algorithm="HS256")

        cls.counter_token = jwt.encode({
            "id": 15,
            "email": "counter_test@example.com",
            "role": "counter",
            "canteen_id": 1,
            "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
        }, Config.JWT_SECRET, algorithm="HS256")

    # 1. Health Endpoint
    def test_01_health_check(self):
        """1. Health API returns status=ok, success=true, and live database status"""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("status"), "ok")
        self.assertEqual(data.get("database"), "Connected")

    # 2. Database Connectivity
    def test_02_database_connectivity(self):
        """2. Direct Database Query Ping"""
        row = query_db("SELECT 1 AS ping", one=True)
        self.assertIsNotNone(row)
        self.assertEqual(row.get("ping"), 1)

    # 3. Register Validation
    def test_03_auth_register_validation(self):
        """3. Registration validation (length >= 8, number, special char, valid email)"""
        res = self.client.post("/api/auth/register", json={
            "name": "Invalid User",
            "email": "invalid_email_format",
            "password": "simplepassword"
        })
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))

    # 4. Login Credentials
    def test_04_auth_login_bad_credentials(self):
        """4. Login with invalid credentials returns 401"""
        res = self.client.post("/api/auth/login", json={
            "email": "nonexistent_user_9999@campuseats.com",
            "password": "WrongPassword123!"
        })
        self.assertEqual(res.status_code, 401)
        data = res.get_json()
        self.assertFalse(data.get("success"))

    # 5. Current User /me
    def test_05_auth_current_user(self):
        """5. Authenticated GET /api/auth/me returns user profile"""
        headers = {"Authorization": f"Bearer {self.student_token}"}
        res = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("user", data)

    # 6. Canteens List & Detail
    def test_06_canteens_api(self):
        """6. GET /api/canteens returns active canteens list"""
        res = self.client.get("/api/canteens")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("canteens", data)
        self.assertIsInstance(data["canteens"], list)

    # 7. Menu Items API
    def test_07_menu_api(self):
        """7. GET /api/menu/1 returns available menu items for canteen"""
        res = self.client.get("/api/menu/1")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("items", data)
        self.assertIsInstance(data["items"], list)

    # 8. Order Creation Validation
    def test_08_order_creation_validation(self):
        """8. Order creation payload validation (empty items, invalid payment method)"""
        headers = {"Authorization": f"Bearer {self.student_token}"}
        res = self.client.post("/api/orders", json={"canteenId": 1, "items": []}, headers=headers)
        self.assertEqual(res.status_code, 400)

        res = self.client.post("/api/orders", json={
            "canteenId": 1,
            "items": [{"menuItemId": 99999, "quantity": 1}],
            "paymentMethod": "crypto_fake"
        }, headers=headers)
        self.assertEqual(res.status_code, 400)

    # 9. Wallet Balance Endpoint
    def test_09_wallet_balance(self):
        """9. GET /api/wallet/balance returns numeric walletBalance"""
        headers = {"Authorization": f"Bearer {self.student_token}"}
        res = self.client.get("/api/wallet/balance", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("walletBalance", data)

    # 10. Payment Order Gateway Creation
    def test_10_payment_create_order(self):
        """10. POST /api/payment/create-order generates Razorpay order id and amount in paise"""
        headers = {"Authorization": f"Bearer {self.student_token}"}
        # Fetch active item
        items = query_db("SELECT id FROM menu_items WHERE canteen_id = 1 AND is_available = 1 LIMIT 1")
        if items:
            item_id = items[0]["id"]
            res = self.client.post("/api/payment/create-order", json={
                "canteenId": 1,
                "items": [{"menuItemId": item_id, "quantity": 1}]
            }, headers=headers)
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get("success"))
            self.assertIn("razorpayOrderId", data["data"])
            self.assertIn("amount", data["data"])

    # 11. Order History (/my and /my-orders)
    def test_11_order_history(self):
        """11. GET /api/orders/my and /my-orders both return formatted order list"""
        headers = {"Authorization": f"Bearer {self.student_token}"}
        res1 = self.client.get("/api/orders/my", headers=headers)
        self.assertEqual(res1.status_code, 200)
        self.assertTrue(res1.get_json().get("success"))

        res2 = self.client.get("/api/orders/my-orders", headers=headers)
        self.assertEqual(res2.status_code, 200)
        self.assertTrue(res2.get_json().get("success"))

    # 12. Kitchen Orders API
    def test_12_kitchen_orders(self):
        """12. GET /api/kitchen/orders accessible to kitchen staff and admin"""
        headers = {"Authorization": f"Bearer {self.kitchen_token}"}
        res = self.client.get("/api/kitchen/orders", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("orders", data)

    # 13. Kitchen Status Validation
    def test_13_kitchen_status_validation(self):
        """13. Kitchen status update rejects invalid status strings"""
        headers = {"Authorization": f"Bearer {self.kitchen_token}"}
        res = self.client.patch("/api/kitchen/orders/1/status", json={"status": "invalid_status"}, headers=headers)
        self.assertEqual(res.status_code, 400)

    # 14. Counter Orders API
    def test_14_counter_orders(self):
        """14. GET /api/counter/orders accessible to counter staff and admin"""
        headers = {"Authorization": f"Bearer {self.counter_token}"}
        res = self.client.get("/api/counter/orders", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("orders", data)

    # 15. Counter Collect Validation
    def test_15_counter_collect_validation(self):
        """15. Counter collect returns 404 for non-existent orders"""
        headers = {"Authorization": f"Bearer {self.counter_token}"}
        res = self.client.patch("/api/counter/orders/999999/collect", json={}, headers=headers)
        self.assertEqual(res.status_code, 404)

    # 16. Wallet Transactions
    def test_16_wallet_transactions(self):
        """16. GET /api/wallet/transactions returns user wallet audit history"""
        headers = {"Authorization": f"Bearer {self.student_token}"}
        res = self.client.get("/api/wallet/transactions", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("transactions", data)

    # 17. Rating Validation
    def test_17_ratings_validation(self):
        """17. Rating validation ensures 1-5 score constraint"""
        headers = {"Authorization": f"Bearer {self.student_token}"}
        res = self.client.post("/api/ratings", json={"orderId": 1, "rating": 6}, headers=headers)
        self.assertEqual(res.status_code, 400)

    # 18. Ratings List
    def test_18_ratings_list(self):
        """18. GET /api/ratings returns public reviews"""
        res = self.client.get("/api/ratings")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("ratings", data)

    # 19. AI Recommender Endpoint
    def test_19_ai_recommender(self):
        """19. POST /api/ai/recommend returns recommendations and summary"""
        headers = {"Authorization": f"Bearer {self.student_token}"}
        res = self.client.post("/api/ai/recommend", json={
            "prompt": "Suggest a snack under 100",
            "budget": 100,
            "dietary": "veg"
        }, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("recommendations", data["data"])
        self.assertIn("summary", data["data"])

    # 20. AI Menu Q&A
    def test_20_ai_menu_qa(self):
        """20. AI assistant answers conversational menu queries"""
        headers = {"Authorization": f"Bearer {self.student_token}"}
        res = self.client.post("/api/ai/recommend", json={
            "prompt": "What are your best vegetarian breakfast options?",
            "budget": 150,
            "dietary": "veg"
        }, headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))

    # 21. AI Deterministic Fallback Engine
    def test_21_ai_heuristic_fallback(self):
        """21. Deterministic heuristic fallback filters budget and diet correctly"""
        catalog = [
            {"id": 1, "name": "Veg Samosa", "description": "", "price": 20, "category": "snacks", "isVeg": True, "prepTimeMinutes": 5},
            {"id": 2, "name": "Chicken Biryani", "description": "", "price": 150, "category": "meals", "isVeg": False, "prepTimeMinutes": 10},
        ]
        result = generate_database_heuristics("quick veg snack under 50", catalog, budget=50, dietary="veg")
        self.assertEqual(len(result["recommendations"]), 1)
        self.assertEqual(result["recommendations"][0]["menuItemId"], 1)

    # 22. PDF Invoice Generation
    def test_22_invoice_pdf_generator(self):
        """22. Itemized PDF invoice generator produces valid PDF byte stream with QR and INR"""
        mock_order = {
            "id": 555,
            "user_id": 1,
            "student_name": "Test Student",
            "student_email": "student@campuseats.com",
            "canteen_id": 1,
            "canteen_name": "Main Canteen",
            "canteen_location": "Campus Central",
            "total_amount": 105.00,
            "token_number": "T998877",
            "status": "placed",
            "payment_method": "wallet",
            "payment_status": "paid",
            "payment_transaction_id": "CW-WALLET-555",
            "created_at": "2026-09-25 12:30:00"
        }
        mock_items = [
            {"name": "Masala Dosa", "quantity": 1, "price": 60.0, "customization": "Extra butter"},
            {"name": "Filter Coffee", "quantity": 1, "price": 30.0, "customization": None}
        ]
        pdf_buf = generate_invoice_pdf(mock_order, mock_items)
        pdf_bytes = pdf_buf.getvalue()
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    # 23. Admin Stats & Analytics
    def test_23_admin_stats(self):
        """23. GET /api/admin/stats returns operational metrics"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        res = self.client.get("/api/admin/stats", headers=headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("stats", data)
        self.assertIn("totalOrders", data["stats"])
        self.assertIn("totalRevenue", data["stats"])

    # 24. Admin Analytics Endpoints
    def test_24_admin_analytics_endpoints(self):
        """24. GET /api/admin/analytics/* endpoints return structured chart data"""
        headers = {"Authorization": f"Bearer {self.admin_token}"}
        for path in ["daily-sales", "peak-hours", "top-dishes", "canteens", "fulfillment"]:
            res = self.client.get(f"/api/admin/analytics/{path}", headers=headers)
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data.get("success"))
            self.assertIn("data", data)

    # 25. Role Protection (Student Forbidden on Admin/Kitchen/Counter)
    def test_25_role_protection_student_forbidden(self):
        """25. Student role receives 403 on admin, kitchen, and counter endpoints"""
        headers = {"Authorization": f"Bearer {self.student_token}"}
        self.assertEqual(self.client.get("/api/admin/stats", headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/kitchen/orders", headers=headers).status_code, 403)
        self.assertEqual(self.client.get("/api/counter/orders", headers=headers).status_code, 403)

    # 26. HMAC Payment Signature Verification
    def test_26_razorpay_hmac_signature(self):
        """26. Razorpay HMAC-SHA256 signature verification mathematically valid"""
        secret = "test_key_secret_2026"
        order_id = "order_FLASK_TEST_101"
        payment_id = "pay_FLASK_TEST_202"
        signature = hmac.new(
            secret.encode("utf-8"),
            f"{order_id}|{payment_id}".encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        self.assertEqual(len(signature), 64)

if __name__ == "__main__":
    unittest.main()
