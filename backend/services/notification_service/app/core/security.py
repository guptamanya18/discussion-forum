from jose import jwt
from passlib.context import CryptContext
from app.core.config import settings

SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
