# CampusEats Flask Backend

A modular Python Flask backend for the **CampusEats** cafeteria pre-order and digital token management platform.

---

## 🛠️ Technology Stack
- **Framework**: Flask 3.x
- **Real-time WebSockets**: Flask-SocketIO (with `simple-websocket`)
- **Database**: MySQL with PyMySQL connection pooling
- **Authentication**: JWT (`pyjwt`) & `bcrypt` password hashing
- **AI Recommendation Engine**: Google Gemini API (`google-genai` / `gemini-2.5-flash`) with fallback heuristic rule-matcher
- **Digital Invoices**: ReportLab PDF generator & QRCode generator with Indian Rupee formatting
- **Payment Verification**: Razorpay HMAC-SHA256 signature verification

---

## 📂 Project Architecture

```
backend_flask/
├── .env.example              # Environment variables template
├── requirements.txt          # Python dependencies
├── README.md                 # Setup & API documentation
├── config.py                 # Configuration and environment loader
├── extensions.py             # Flask extensions (SocketIO, Limiter, CORS)
├── app.py                    # Application factory & Socket.IO handlers
├── middleware/
│   ├── auth_middleware.py    # JWT Bearer token validation
│   └── role_middleware.py    # Role-based access control (RBAC)
├── services/
│   ├── db_service.py         # PyMySQL connection pool & transaction manager
│   ├── ai_service.py         # Gemini 2.5 Flash SDK + heuristic fallbacks
│   └── invoice_service.py    # ReportLab itemized PDF receipt generator
├── controllers/              # Business logic controllers
│   ├── auth_controller.py
│   ├── canteen_controller.py
│   ├── menu_controller.py
│   ├── order_controller.py
│   ├── payment_controller.py
│   ├── wallet_controller.py
│   ├── kitchen_controller.py
│   ├── counter_controller.py
│   ├── rating_controller.py
│   ├── admin_controller.py
│   └── ai_controller.py
├── routes/                   # Flask Blueprints
│   ├── auth_routes.py
│   ├── canteen_routes.py
│   ├── menu_routes.py
│   ├── order_routes.py
│   ├── payment_routes.py
│   ├── wallet_routes.py
│   ├── kitchen_routes.py
│   ├── counter_routes.py
│   ├── rating_routes.py
│   ├── admin_routes.py
│   └── ai_routes.py
└── test_flask_backend.py     # Comprehensive automated test suite
```

---

## 🚀 Setup & Execution

### 1. Install Dependencies
```bash
pip install -r backend_flask/requirements.txt
```

### 2. Configure Environment
Copy `.env.example` to `.env` in your project root or `backend_flask/`:
```bash
cp backend_flask/.env.example backend_flask/.env
```

### 3. Run Development Server
```bash
python -m backend_flask.app
```
Server runs at `http://localhost:5000`.

### 4. Run Automated Tests
```bash
python -m unittest backend_flask/test_flask_backend.py
```
