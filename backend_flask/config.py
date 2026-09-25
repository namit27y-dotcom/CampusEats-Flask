import os
from pathlib import Path
from dotenv import load_dotenv

# Load all relevant .env files in priority order: backend_flask/.env > backend/.env > root .env
root_env = Path(__file__).resolve().parent.parent / ".env"
backend_env = Path(__file__).resolve().parent.parent / "backend" / ".env"
local_env = Path(__file__).resolve().parent / ".env"

if root_env.exists():
    load_dotenv(dotenv_path=root_env, override=False)
if backend_env.exists():
    load_dotenv(dotenv_path=backend_env, override=True)
if local_env.exists():
    load_dotenv(dotenv_path=local_env, override=True)

class Config:
    PORT = int(os.getenv("PORT", "5000"))
    DB_HOST = os.getenv("DATABASE_HOST") or os.getenv("DB_HOST", "localhost")
    DB_USER = os.getenv("DATABASE_USER") or os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DATABASE_PASSWORD") if os.getenv("DATABASE_PASSWORD") is not None else os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DATABASE_NAME") or os.getenv("DB_NAME", "campuseats_db")
    DB_PORT = int(os.getenv("DATABASE_PORT") or os.getenv("DB_PORT", "3306"))
    
    JWT_SECRET = os.getenv("JWT_SECRET_KEY") or os.getenv("JWT_SECRET", "supersecretjwtkey_campuseats_production_2026")
    JWT_EXPIRES_DAYS = 7
    
    RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    
    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
    CORS_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "https://campus-eats-ruby.vercel.app"
    ]
