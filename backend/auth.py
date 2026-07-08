
from jose import jwt
from datetime import datetime, timedelta
import os

SECRET = os.getenv("SECRET_KEY", "dev")

def create_token(data):
    data.update({"exp": datetime.utcnow() + timedelta(hours=12)})
    return jwt.encode(data, SECRET, algorithm="HS256")
