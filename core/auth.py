"""
Authentication & authorization module with JWT and RBAC support.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, List
from enum import Enum
import os

from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# Configuration
SECRET_KEY = os.getenv("AGENTRIC_SECRET_KEY", "change-me-in-production-with-strong-key")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


# ============================================================================
# Models
# ============================================================================

class Role(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    POWER_USER = "power_user"
    USER = "user"
    GUEST = "guest"


class User(BaseModel):
    """User model."""
    username: str
    email: Optional[str] = None
    role: Role = Role.USER
    disabled: bool = False
    full_name: Optional[str] = None


class UserInDB(User):
    """User with hashed password."""
    hashed_password: str


class LoginRequest(BaseModel):
    """Login request."""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response."""
    access_token: str
    token_type: str = "bearer"
    user: User


class Token(BaseModel):
    """Token model."""
    access_token: str
    token_type: str
    expires_in: int


class TokenData(BaseModel):
    """Token data."""
    username: str
    scopes: List[str] = []


# ============================================================================
# Password Utilities
# ============================================================================

def hash_password(password: str) -> str:
    """Hash password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password."""
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# Token Utilities
# ============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Verify and decode JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        
        if username is None:
            raise credentials_exception
        
        scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=scopes)
    except JWTError:
        raise credentials_exception
    
    return token_data


# ============================================================================
# In-Memory User Store (Replace with Database)
# ============================================================================

USERS_DB: Dict[str, UserInDB] = {
    "admin": UserInDB(
        username="admin",
        email="admin@agentricai.local",
        hashed_password=hash_password("admin"),
        role=Role.ADMIN,
        full_name="Administrator"
    ),
    "user": UserInDB(
        username="user",
        email="user@agentricai.local",
        hashed_password=hash_password("user"),
        role=Role.USER,
        full_name="Default User"
    ),
}


def get_user_from_db(username: str) -> Optional[UserInDB]:
    """Get user from database."""
    return USERS_DB.get(username)


def create_user(username: str, password: str, email: str, role: Role = Role.USER, full_name: str = "") -> User:
    """Create a new user."""
    if username in USERS_DB:
        raise ValueError(f"User {username} already exists")
    
    user = UserInDB(
        username=username,
        email=email,
        hashed_password=hash_password(password),
        role=role,
        full_name=full_name
    )
    
    USERS_DB[username] = user
    return User(**user.model_dump(exclude={"hashed_password"}))


def authenticate_user(username: str, password: str) -> Optional[User]:
    """Authenticate user with username and password."""
    user = get_user_from_db(username)
    
    if not user or not verify_password(password, user.hashed_password):
        return None
    
    if user.disabled:
        return None
    
    return User(**user.model_dump(exclude={"hashed_password"}))


# ============================================================================
# Dependency Functions
# ============================================================================

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """Get current authenticated user."""
    token_data = verify_token(token)
    user = get_user_from_db(token_data.username)
    
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return User(**user.model_dump(exclude={"hashed_password"}))


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user."""
    if current_user.disabled:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


def require_role(*allowed_roles: Role):
    """Require user to have specific role."""
    async def check_role(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    
    return check_role


# ============================================================================
# Session Management
# ============================================================================

class SessionManager:
    """Simple session manager for tracking active users."""
    
    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
    
    def create_session(self, user: User, token: str) -> str:
        """Create a new session."""
        session_id = f"sess_{user.username}_{datetime.now().timestamp()}"
        self.sessions[session_id] = {
            "user": user,
            "token": token,
            "created_at": datetime.now(),
            "last_activity": datetime.now()
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session info."""
        return self.sessions.get(session_id)
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def get_user_sessions(self, username: str) -> List[str]:
        """Get all sessions for a user."""
        return [sid for sid, sess in self.sessions.items() if sess["user"].username == username]


session_manager = SessionManager()
