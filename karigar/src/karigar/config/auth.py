"""
Authentication & Authorization System
JWT-based authentication for KARIGAR platform
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
import hashlib
import secrets
from pydantic import BaseModel


class User(BaseModel):
    """User model"""
    id: str
    email: str
    name: str
    role: str  # artisan, customer, admin
    is_active: bool = True
    created_at: datetime


class TokenData(BaseModel):
    """Token payload data"""
    user_id: str
    email: str
    role: str
    exp: datetime


class AuthConfig:
    """Authentication configuration"""
    SECRET_KEY = secrets.token_urlsafe(32)
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS = 7


class PasswordManager:
    """Manage password hashing and verification"""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA-256"""
        salt = secrets.token_hex(32)
        hashed = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            100000
        )
        return f"{salt}${hashed.hex()}"

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        try:
            salt, hashed = hashed_password.split('$')
            return hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                100000
            ).hex() == hashed
        except:
            return False


class JWTManager:
    """Manage JWT token creation and verification"""

    @staticmethod
    def create_access_token(user_id: str, email: str, role: str) -> str:
        """Create access token"""
        payload = {
            "user_id": user_id,
            "email": email,
            "role": role,
            "exp": datetime.utcnow() + timedelta(minutes=AuthConfig.ACCESS_TOKEN_EXPIRE_MINUTES),
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, AuthConfig.SECRET_KEY, algorithm=AuthConfig.ALGORITHM)
        return token

    @staticmethod
    def create_refresh_token(user_id: str) -> str:
        """Create refresh token"""
        payload = {
            "user_id": user_id,
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(days=AuthConfig.REFRESH_TOKEN_EXPIRE_DAYS),
            "iat": datetime.utcnow()
        }
        token = jwt.encode(payload, AuthConfig.SECRET_KEY, algorithm=AuthConfig.ALGORITHM)
        return token

    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode token"""
        try:
            payload = jwt.decode(token, AuthConfig.SECRET_KEY, algorithms=[AuthConfig.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def decode_token(token: str) -> Optional[TokenData]:
        """Decode token and return TokenData"""
        payload = JWTManager.verify_token(token)
        if not payload:
            return None

        return TokenData(
            user_id=payload.get("user_id"),
            email=payload.get("email"),
            role=payload.get("role"),
            exp=datetime.fromtimestamp(payload.get("exp"))
        )


class SessionManager:
    """Manage user sessions"""

    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}

    def create_session(self, user_id: str, token: str) -> str:
        """Create user session"""
        session_id = secrets.token_urlsafe(32)
        self.sessions[session_id] = {
            "user_id": user_id,
            "token": token,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "active": True
        }
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session info"""
        return self.sessions.get(session_id)

    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate session"""
        if session_id in self.sessions:
            self.sessions[session_id]["active"] = False
            return True
        return False

    def cleanup_expired_sessions(self, max_age_hours: int = 24):
        """Clean up expired sessions"""
        now = datetime.utcnow()
        expired = [
            sid for sid, session in self.sessions.items()
            if (now - session["last_activity"]).total_seconds() > max_age_hours * 3600
        ]
        for sid in expired:
            del self.sessions[sid]


class AuthorizationManager:
    """Manage user roles and permissions"""

    ROLES = {
        "artisan": [
            "profile:read",
            "profile:update",
            "orders:read",
            "orders:create",
            "products:read",
            "products:create",
            "analytics:read"
        ],
        "customer": [
            "profile:read",
            "profile:update",
            "orders:create",
            "orders:read",
            "products:read",
            "reviews:create"
        ],
        "admin": [
            "*"  # All permissions
        ]
    }

    @staticmethod
    def has_permission(role: str, action: str) -> bool:
        """Check if role has permission for action"""
        permissions = AuthorizationManager.ROLES.get(role, [])

        # Admin has all permissions
        if "*" in permissions:
            return True

        # Check specific permission
        return action in permissions

    @staticmethod
    def has_role(role: str, required_role: str) -> bool:
        """Check if user has required role"""
        if role == "admin":
            return True
        return role == required_role


# Global instances
password_manager = PasswordManager()
jwt_manager = JWTManager()
session_manager = SessionManager()
auth_manager = AuthorizationManager()


class LoginCredentials(BaseModel):
    """Login credentials"""
    email: str
    password: str


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """User response"""
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    created_at: datetime
