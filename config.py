# config.py
import os
from dotenv import load_dotenv

# ✅ Load environment variables from .env file
load_dotenv()

class Config:
    # ✅ Secret key for CSRF protection
    SECRET_KEY = os.getenv('SECRET_KEY')

    # ✅ Database URL — supports both DATABASE_URL or SQLALCHEMY_DATABASE_URI
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI') or os.getenv('DATABASE_URL')

    # ✅ Optional: turn off modification tracking (saves resources)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ✅ File upload path
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'images')

    # ✅ Optional: Google Maps API Key
    GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

    # Debugging (optional)
    print("✅ Loaded SECRET_KEY:", bool(SECRET_KEY))  # Will show True if loaded
    print("✅ Loaded DB URI:", SQLALCHEMY_DATABASE_URI)
    print("✅ Loaded UPLOAD_FOLDER:", UPLOAD_FOLDER)

    
