# 🍽️ CampusEats — Smart Canteen Pre-Order & Digital Token System

[![Live Demo](https://img.shields.io/badge/Live_Demo-Vercel-black?logo=vercel&logoColor=white)](https://campus-eats-ruby.vercel.app/)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-181717?logo=github&logoColor=white)](https://github.com/namit27y-dotcom/CampusEats-Flask)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.8-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-6.x-646CFF?logo=vite&logoColor=white)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v4-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Socket.IO](https://img.shields.io/badge/Socket.IO-Flask--SocketIO-010101?logo=socket.io&logoColor=white)](https://flask-socketio.readthedocs.io/)

> **CampusEats** is a full-stack smart canteen pre-order and digital token platform that allows students to browse canteens, order food, make payments, track orders in real time, receive invoices, use wallet functionality, and get AI-assisted meal recommendations. Kitchen and counter staff manage the order lifecycle through dedicated dashboards.
>
> 🌐 **Live Application:** [campus-eats-ruby.vercel.app](https://campus-eats-ruby.vercel.app/)  
> 📁 **GitHub Repository:** [github.com/namit27y-dotcom/CampusEats-Flask](https://github.com/namit27y-dotcom/CampusEats-Flask)

---

## 📖 Table of Contents

- [Overview & Architecture](#-overview--architecture)
- [Technology Stack](#-technology-stack)
- [System Security & Authorization](#-system-security--authorization)
- [Roles & Features](#-roles--features)
- [Order Lifecycle State Machine](#-order-lifecycle-state-machine)
- [Database Schema & Migrations](#-database-schema--migrations)
- [Payment & Razorpay Test Mode](#-payment--razorpay-test-mode)
- [PDF Invoices & Safe QR Verification](#-pdf-invoices--safe-qr-verification)
- [AI Assistant & Menu-Grounded Recommendations](#-ai-assistant--menu-grounded-recommendations)
- [Real-Time WebSocket Layer](#-real-time-websocket-layer)
- [API Documentation](#-api-documentation)
- [Environment Configuration](#-environment-configuration)
- [Local Development Setup](#-local-development-setup)
- [Automated Testing](#-automated-testing)
- [Production Deployment Guide](#-production-deployment-guide)
- [Project Structure](#-project-structure)
- [License](#-license)

---

# 🚀 Overview & Architecture

CampusEats connects students, kitchen crews, counter staff, and canteen administrators through a clean, unified full-stack architecture powered by a React 19 single-page application and a modular Python Flask backend:

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    STUDENT / STAFF BROWSER CLIENTS                      │
│                React 19 + TypeScript + Vite + Tailwind CSS              │
└───────────────────▲─────────────────────────────────▲───────────────────┘
                    │                                 │
     HTTPS REST API │ Bearer JWT       WebSocket      │ Flask-SocketIO
     (JSON Payload) │ Handshake       Bi-directional  │ Rooms (order_*, canteen_*)
                    ▼                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          FLASK BACKEND SERVICE                          │
│               Flask 3.x • Flask-SocketIO • Flask-CORS • PyJWT           │
│                                                                         │
│  ┌──────────────────┐  ┌───────────────────┐  ┌──────────────────────┐  │
│  │ Blueprint Routes │  │ Auth & RBAC Guard │  │ Business Controllers │  │
│  └────────┬─────────┘  └─────────┬─────────┘  └──────────┬───────────┘  │
│           │                      │                       │              │
│  ┌────────▼──────────────────────▼───────────────────────▼───────────┐  │
│  │                          Services Layer                           │  │
│  │  • PyMySQL Pool Manager       • ReportLab PDF & QR Engine         │  │
│  │  • Gemini 2.5 AI SDK          • Rule-Based Fallback Matcher       │  │
│  └───────────────────────────────────┬───────────────────────────────┘  │
└──────────────────────────────────────┼──────────────────────────────────┘
                                       │
                                       ▼
                       ┌───────────────────────────────┐
                       │        MySQL 8 DATABASE       │
                       │  InnoDB Engine • ACID Locked  │
                       └───────────────────────────────┘
```

---

# 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React 19, TypeScript 5.8, Vite 6.x, Tailwind CSS v4, Lucide React, Socket.IO Client, Motion, Canvas Confetti |
| **Backend** | Python 3.10+, Flask 3.x, Flask-SocketIO, Flask-CORS, Flask-Limiter, Simple-WebSocket |
| **Database** | MySQL 8 (InnoDB), PyMySQL, DBUtils Connection Pooling |
| **Authentication** | JWT (`pyjwt`), Password Hashing (`bcrypt`), Role-Based Access Control (RBAC) |
| **Real-Time** | Flask-SocketIO (WebSocket rooms for order & canteen updates) |
| **AI Integration** | Google Gemini Python SDK (`google-genai` / Gemini 2.5 Flash) with deterministic heuristic fallback |
| **PDF & Documents** | ReportLab (Itemized PDF Invoices with INR currency formatting), QRCode generator |
| **Payments** | Razorpay Test Mode Integration with HMAC-SHA256 signature verification |
| **Deployment** | Vercel (Frontend SPA) + Python-compatible Cloud Hosting (Render / Railway) |

---

# 🔐 System Security & Authorization

- **JWT Authentication & Stateless Sessions**: Token-based authentication using `pyjwt` with configurable expiry and secret management.
- **Strong Password Hashing**: Passwords are encrypted using salted `bcrypt` hashing before database insertion. Registration enforces strong passwords (minimum 8 characters, at least 1 number, and at least 1 special character).
- **Role-Based Access Control (RBAC)**: Enforced via the `@authorize_roles` decorator supporting `student`, `kitchen`, `counter`, and `admin` roles.
- **Canteen-Level Authorization**: Staff members (`kitchen` and `counter`) are restricted to managing orders within their assigned `canteen_id`.
- **Server-Authoritative Pricing & Stock**: Total amounts, item availability, and stock balances are strictly computed and decremented server-side with database consistency.
- **Protected WebSocket Rooms**: Socket.IO connections join scoped rooms (`order_<id>` and `canteen_<id>`), preventing data leakage across unauthorized clients.
- **HMAC Payment Verification**: Razorpay payment signatures are validated using HMAC-SHA256 hashing to prevent unauthorized status tampering.
- **Secret Isolation**: All credentials, keys, and tokens are loaded via environment variables and excluded from version control.

---

# ✨ Roles & Features

### 👨‍🎓 Student
- **Registration & Login**: Secure account creation and authentication.
- **Browse Active Canteens**: Explore campus canteens and view live operating statuses.
- **Menu Browsing & Filtering**: Filter by category, dietary preferences (Veg / Non-Veg), and preparation time.
- **Cart & Customization**: Add food items with custom instructions and extras.
- **Flexible Checkout**: Pay via Campus Wallet balance or Razorpay (Test Mode).
- **Real-Time Order Tracking**: Live order progression modal with elapsed preparation timers.
- **Order History**: Access historical orders with item details and status logs.
- **Itemized PDF Invoices**: Download generated PDF receipts with token verification QR codes.
- **Ratings & Reviews**: Submit ratings and feedback on completed orders.
- **AI Meal Assistant**: Receive personalized, menu-grounded meal recommendations based on budget and dietary preferences.

### 👨‍🍳 Kitchen Staff
- **Kitchen Display System (KDS)**: Live dashboard of active orders for the assigned canteen.
- **Order State Progression**: Transition orders seamlessly across `placed` ➔ `accepted` ➔ `preparing` ➔ `ready`.
- **Real-Time Sync**: Automatically notify students when their meal preparation starts or is ready for pickup.

### 🧾 Counter Staff
- **Pickup Queue Dashboard**: View all orders currently in `ready` status.
- **Token Verification**: Verify digital pickup tokens presented by students.
- **Order Fulfillment**: Mark verified orders as `completed` / collected, preventing duplicate pickups.
- **Canteen Scoping**: Isolated to orders belonging to their authorized canteen.

### 👨‍💼 Administrator
- **Analytics & Metrics**: View real-time aggregated metrics including total revenue, active orders, and sales trends.
- **Operational Analytics**: Dedicated analytics for daily sales, peak order hours, top dishes, canteen performance, and fulfillment times.
- **Menu & Stock Management**: Add or update menu items, toggle item availability, and update inventory stock counts.
- **User & Order Oversight**: View all registered users, roles, and campus-wide order records.

---

# 🎟️ Order Lifecycle State Machine

Order state progression is enforced strictly server-side through defined stages:

```text
    ┌──────────────┐
    │    PLACED    │ ── (Order created by Student; stock decremented)
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │   ACCEPTED   │ ── (Kitchen acknowledges and accepts order)
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │  PREPARING   │ ── (Kitchen marks food under preparation)
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │    READY     │ ── (Preparation complete; token called for pickup)
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │  COMPLETED   │ ── (Counter verifies token & marks order collected)
    └──────────────┘
```

> **Cancellation Policy**: Students can cancel orders while in `placed` or `accepted` status (`PATCH /api/orders/<id>/cancel`). Cancellation restores stock quantities and refunds wallet balances.

---

# 🗄️ Database Schema & Migrations

The platform utilizes MySQL 8 with `InnoDB` transactional tables.

### Primary Tables

| Table | Purpose | Key Columns |
|---|---|---|
| `users` | User accounts and staff roles | `id`, `name`, `email`, `password`, `role`, `canteen_id`, `created_at` |
| `canteens` | Campus canteen outlets | `id`, `name`, `location`, `is_active`, `created_at` |
| `menu_items` | Dishes and food inventory | `id`, `canteen_id`, `name`, `description`, `price`, `category`, `is_veg`, `is_available`, `stock_quantity`, `is_tracked`, `prep_time` |
| `orders` | Order records and payment states | `id`, `user_id`, `canteen_id`, `total_amount`, `token_number`, `status`, `payment_method`, `payment_status`, `payment_transaction_id`, `razorpay_order_id`, `razorpay_payment_id`, `razorpay_signature`, `created_at` |
| `order_items` | Individual line items per order | `id`, `order_id`, `menu_item_id`, `quantity`, `price`, `customization`, `extra_amount` |
| `wallet_transactions` | Student wallet ledger | `id`, `user_id`, `amount`, `transaction_type`, `order_id`, `balance_after`, `created_at` |
| `ratings` | Student order reviews | `id`, `order_id`, `user_id`, `rating`, `comment`, `created_at` |

### Database Migrations
Database schema updates and idempotent column additions are managed in:
- `backend_flask/migrations/migration_real_order_flow.sql`

---

# 💳 Payment & Razorpay Test Mode

- **Razorpay Checkout**: Backend creates official test-mode orders (`POST /api/payment/create-order`) using server-calculated totals.
- **HMAC Signature Verification**: Validates payment responses (`POST /api/payment/verify-signature`) using SHA256 HMAC calculation over `order_id|payment_id`.
- **Campus Wallet**: Transactional wallet system supporting balance inquiries (`GET /api/wallet/balance`), top-ups (`POST /api/wallet/add-money`), transaction history (`GET /api/wallet/transactions`), and automated cancellation refunds.

---

# 📄 PDF Invoices & Safe QR Verification

- **Itemized Receipts**: Generated dynamically using **ReportLab** (`GET /api/orders/<id>/invoice`).
- **Formatting**: Includes complete order breakdowns, taxes, customizations, extra charges, and Indian Rupee (INR) currency formatting.
- **Safe Verification QR Code**: Embedded QR code links to public token verification (`/verify?orderId=...&token=...`) without exposing sensitive authentication tokens, database IDs, or user credentials.

---

# 🤖 AI Assistant & Menu-Grounded Recommendations

- **Endpoint**: `POST /api/ai/recommend` (Protected by JWT).
- **Menu Grounding**: The recommendation engine queries active menu items from MySQL and grounds Gemini prompt queries to prevent hallucinated dishes.
- **Dietary & Budget Filtering**: Strictly honors vegetarian/non-vegetarian preferences and maximum budget constraints.
- **Deterministic Heuristic Fallback**: If the Gemini API key is unset or external AI rate limits are encountered, the engine seamlessly switches to an internal rule-based heuristic matcher.

---

# ⚡ Real-Time WebSocket Layer

Real-time bi-directional events are powered by **Flask-SocketIO**:

- **Order Tracking Rooms (`order_<order_id>`)**: Broadcasts status transitions (`placed`, `accepted`, `preparing`, `ready`, `completed`, `cancelled`) directly to the ordering student's active session.
- **Canteen Rooms (`canteen_<canteen_id>`)**: Notifies kitchen staff instantly of new incoming orders and status updates.
- **Socket Handshake**: Supports clean client connection handshakes and room joins.

---

# 🔌 API Documentation

Base API URL: `http://localhost:5000/api`

### 🩺 Health Check
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/health` | Public | Service health & live MySQL connection ping |

### 🔑 Authentication (`/api/auth`)
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/auth/register` | Public | Register a new student account |
| `POST` | `/api/auth/login` | Public | Authenticate user and receive JWT token |
| `GET` | `/api/auth/me` | Authenticated | Get current authenticated user profile |

### 🏬 Canteens (`/api/canteens`)
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/canteens` | Public | List all active campus canteens |
| `GET` | `/api/canteens/<id>` | Public | Get details for a specific canteen |

### 📋 Menu (`/api/menu`)
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/menu/<canteen_id>` | Public | Get menu items for a specific canteen |
| `POST` | `/api/menu` | Admin | Create a new menu item |
| `PUT` | `/api/menu/<id>` | Admin | Update an existing menu item |
| `PATCH` | `/api/menu/<id>/availability` | Admin, Kitchen | Toggle item active availability |
| `PATCH` | `/api/menu/<id>/stock` | Admin, Kitchen | Update item stock quantity and tracking |

### 📦 Orders (`/api/orders`)
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/orders` | Student | Place a new order with stock deduction |
| `GET` | `/api/orders/my` | Student | Get authenticated user order history (alias: `/my-orders`) |
| `PATCH` | `/api/orders/<id>/cancel` | Student | Cancel order and refund balance (placed/accepted only) |
| `GET` | `/api/orders/<id>/invoice` | Authenticated | Download itemized PDF receipt |

### 💳 Payments & Wallet (`/api/payment`, `/api/wallet`)
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/payment/create-order` | Student | Create Razorpay test-mode payment order |
| `POST` | `/api/payment/verify-signature` | Student | Verify Razorpay HMAC payment signature |
| `GET` | `/api/wallet/balance` | Student | Retrieve current wallet balance |
| `POST` | `/api/wallet/add-money` | Student | Add funds to student wallet |
| `GET` | `/api/wallet/transactions` | Student | Get wallet transaction ledger history |

### 👨‍🍳 Kitchen (`/api/kitchen`)
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/kitchen/orders` | Kitchen, Admin | Get active orders for staff canteen |
| `PATCH` | `/api/kitchen/orders/<id>/status` | Kitchen, Admin | Update order state (`accepted`, `preparing`, `ready`) |

### 🧾 Counter (`/api/counter`)
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/counter/orders` | Counter, Admin | Get ready orders queue for pickup |
| `PATCH` | `/api/counter/orders/<id>/collect` | Counter, Admin | Verify token and mark order as collected/completed |

### ⭐ Ratings (`/api/ratings`)
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/ratings` | Student | Submit rating and feedback for completed order |
| `GET` | `/api/ratings` | Public | Retrieve dish / canteen ratings |

### 📊 Admin (`/api/admin`)
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `GET` | `/api/admin/stats` | Admin | Aggregate dashboard business statistics |
| `GET` | `/api/admin/analytics/daily-sales` | Admin | Daily sales breakdown analytics |
| `GET` | `/api/admin/analytics/peak-hours` | Admin | Order volume by hour analytics |
| `GET` | `/api/admin/analytics/top-dishes` | Admin | Top-selling dishes rankings |
| `GET` | `/api/admin/analytics/canteens` | Admin | Multi-canteen performance metrics |
| `GET` | `/api/admin/analytics/fulfillment` | Admin | Average fulfillment time analytics |
| `GET` | `/api/admin/users` | Admin | List all registered user accounts |
| `GET` | `/api/admin/orders` | Admin | View all campus order records |

### 🤖 AI Recommendations (`/api/ai`)
| Method | Endpoint | Access | Description |
|---|---|---|---|
| `POST` | `/api/ai/recommend` | Student | Generate menu-grounded meal recommendations |

---

# 🔧 Environment Configuration

### Frontend Configuration (`.env`)
Create a `.env` file in the project root:

```env
VITE_API_URL=http://localhost:5000/api
VITE_WS_URL=http://localhost:5000
VITE_USE_MOCK=false
VITE_SHOW_TEST_ACCOUNTS=false
```

### Backend Configuration (`backend_flask/.env`)
Create a `.env` file inside `backend_flask/` (or duplicate `backend_flask/.env.example`):

```env
PORT=5000

# Database Configuration
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=campuseats_db
DB_PORT=3306

# Security & Authentication
JWT_SECRET=your_secure_jwt_secret_key_change_in_production

# Payment Gateway (Razorpay Test Mode)
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret

# AI Recommendation Service (Google Gemini API)
GEMINI_API_KEY=your_gemini_api_key_here

# Frontend Application Origin for CORS
FRONTEND_URL=http://localhost:5173
```

---

# ⚙️ Local Development Setup

### Prerequisites
- Node.js 18+ & npm
- Python 3.10+
- MySQL 8.0 Server running locally or in the cloud

---

### 1. Backend Setup (Flask)

Open a terminal and navigate to `backend_flask`:

```bash
cd backend_flask
```

Create and activate a Python virtual environment:

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Run database migration if needed:
```bash
mysql -u root -p campuseats_db < migrations/migration_real_order_flow.sql
```

Start the Flask server:
```bash
python -m backend_flask.app
```

The Flask backend will start at `http://localhost:5000`.  
Verify health check at: `http://localhost:5000/api/health`

---

### 2. Frontend Setup (React + Vite)

Open a second terminal in the repository root:

```bash
# Install frontend dependencies
npm install

# Start Vite development server
npm run dev
```

The frontend application will be live at `http://localhost:5173`.

---

# 🧪 Automated Testing

### Backend Test Suite
The Flask backend includes an automated test suite verifying health checks, authentication, authorization, role guards, menu operations, order flows, payment signature mathematics, and PDF generation:

```bash
python -m unittest backend_flask/test_flask_backend.py
```

**Verified Test Result**: `26/26 tests passing (OK)`

### Frontend Validation & Build
```bash
# Type check and linting
npm run lint

# Production build validation
npm run build
```

---

# 🚢 Production Deployment Guide

### 1. Frontend Deployment (Vercel)
- **Framework Preset**: Vite
- **Root Directory**: `.`
- **Build Command**: `npm run build`
- **Output Directory**: `dist`
- **Environment Variables**:
  - `VITE_API_URL`: `https://your-flask-backend.onrender.com/api`
  - `VITE_WS_URL`: `https://your-flask-backend.onrender.com`
  - `VITE_USE_MOCK`: `false`

### 2. Backend Deployment (Render / Railway / Cloud Host)
The Flask backend can be deployed to any Python-compatible cloud host supporting WebSockets:

- **Runtime**: Python 3.10+
- **Root Directory**: `.` (Repository root)
- **Build Command**: `pip install -r backend_flask/requirements.txt`
- **Start Command**: `python -m backend_flask.app`
- **Health Check Path**: `/api/health`
- **Environment Variables**:
  - `PORT`: `5000` (or host provided `$PORT`)
  - `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `DB_PORT`
  - `JWT_SECRET`
  - `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`
  - `GEMINI_API_KEY`
  - `FRONTEND_URL`: URL of your deployed Vercel frontend

> [!NOTE]
> Ensure your cloud hosting service supports WebSocket connections for Flask-SocketIO real-time order updates.

---

# 📂 Project Structure

```text
CampusEats-Flask/
├── backend_flask/                  # Python Flask Backend
│   ├── app.py                      # Flask app factory & Socket.IO initialization
│   ├── config.py                   # Environment configuration loader
│   ├── extensions.py               # Flask extensions (SocketIO, CORS, Limiter)
│   ├── requirements.txt            # Python dependencies
│   ├── test_flask_backend.py       # Automated Flask unit test suite (26 tests)
│   ├── verify_live_flows.py        # End-to-end integration validation script
│   ├── assets/                     # Backend static assets & fonts
│   ├── controllers/                # Business logic controllers
│   │   ├── admin_controller.py
│   │   ├── ai_controller.py
│   │   ├── auth_controller.py
│   │   ├── canteen_controller.py
│   │   ├── counter_controller.py
│   │   ├── kitchen_controller.py
│   │   ├── menu_controller.py
│   │   ├── order_controller.py
│   │   ├── payment_controller.py
│   │   ├── rating_controller.py
│   │   └── wallet_controller.py
│   ├── middleware/                 # JWT authentication & role authorization
│   │   ├── auth_middleware.py
│   │   └── role_middleware.py
│   ├── migrations/                 # MySQL database migration scripts
│   │   └── migration_real_order_flow.sql
│   ├── routes/                     # Blueprint endpoint routing
│   │   ├── admin_routes.py
│   │   ├── ai_routes.py
│   │   ├── auth_routes.py
│   │   ├── canteen_routes.py
│   │   ├── counter_routes.py
│   │   ├── kitchen_routes.py
│   │   ├── menu_routes.py
│   │   ├── order_routes.py
│   │   ├── payment_routes.py
│   │   ├── rating_routes.py
│   │   └── wallet_routes.py
│   └── services/                   # Core backend services
│       ├── ai_service.py           # Gemini 2.5 SDK & fallback engine
│       ├── db_service.py           # PyMySQL connection pooling
│       └── invoice_service.py      # ReportLab PDF invoice generation
├── public/                         # Static web assets
├── src/                            # React 19 Frontend Application
│   ├── assets/                     # Frontend images & styles
│   ├── components/                 # Reusable UI components
│   ├── context/                    # React Context (Auth, Cart, Socket)
│   ├── data/                       # Mock fallback data
│   ├── hooks/                      # Custom React hooks
│   ├── pages/                      # Page views (Student, Kitchen, Counter, Admin)
│   ├── server/                     # Offline mock API plugin
│   ├── types/                      # TypeScript interface declarations
│   ├── utils/                      # Frontend API & invoice download helpers
│   ├── App.tsx                     # Main routing & application view
│   ├── index.css                   # Tailwind CSS v4 styling
│   └── main.tsx                    # React DOM root mounting
├── index.html                      # Single page application HTML entry
├── package.json                    # Frontend dependencies & npm scripts
├── tsconfig.json                   # TypeScript compiler configuration
├── vercel.json                     # Vercel deployment routing config
├── vite.config.ts                  # Vite build tool configuration
├── .env.example                    # Frontend environment template
├── .gitignore                      # Git ignored files
└── README.md                       # Project documentation
```

---

# 📄 License

This project is open source and available under the **MIT License**.
