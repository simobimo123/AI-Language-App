import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from schemas import UserLogin, GoogleLogin
from models import User
from database import get_db


load_dotenv()


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


password_hash = PasswordHash.recommended()


SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

GOOGLE_WEB_CLIENT_ID = os.getenv(
    "GOOGLE_WEB_CLIENT_ID"
)


if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY must be set in the environment"
    )

if not GOOGLE_WEB_CLIENT_ID:
    raise RuntimeError(
        "GOOGLE_WEB_CLIENT_ID must be set in the environment"
    )


security = HTTPBearer()


# =========================================================
# Create application JWT
# =========================================================

def create_access_token(
    user_id: int
):
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "exp": expire
    }

    return jwt.encode(
        payload,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


# =========================================================
# Get current user
# =========================================================

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        security
    ),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = int(payload["sub"])

    except (
        jwt.InvalidTokenError,
        KeyError,
        ValueError,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )

    return user


# =========================================================
# Normal email/password login
# =========================================================

@router.post("/login")
def login(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == user_data.email
    ).first()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not password_hash.verify(
        user_data.password,
        user.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )

    access_token = create_access_token(
        user.id
    )

    return {
        "message": "Login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "native_language": user.native_language,
        "learning_language": user.learning_language
    }


# =========================================================
# Google Login
# =========================================================

@router.post("/google")
def google_login(
    user_data: GoogleLogin,
    db: Session = Depends(get_db)
):
    try:
        google_user = id_token.verify_oauth2_token(
            user_data.id_token,
            google_requests.Request(),
            GOOGLE_WEB_CLIENT_ID
        )

    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid Google ID token"
        )

    # -----------------------------------------------------
    # Verify issuer
    # -----------------------------------------------------

    issuer = google_user.get("iss")

    if issuer not in (
        "accounts.google.com",
        "https://accounts.google.com"
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid Google token issuer"
        )

    # -----------------------------------------------------
    # Get Google identity
    # -----------------------------------------------------

    google_id = google_user.get("sub")
    email = google_user.get("email")
    email_verified = google_user.get("email_verified")
    name = google_user.get("name")

    if not google_id:
        raise HTTPException(
            status_code=401,
            detail="Google account ID is missing"
        )

    if not email:
        raise HTTPException(
            status_code=401,
            detail="Google account email is missing"
        )

    if email_verified is not True:
        raise HTTPException(
            status_code=401,
            detail="Google email is not verified"
        )

    # -----------------------------------------------------
    # Find existing user by Google ID first
    # -----------------------------------------------------

    user = db.query(User).filter(
        User.google_id == google_id
    ).first()

    # -----------------------------------------------------
    # If not found, try verified email
    # -----------------------------------------------------

    if user is None:

        user = db.query(User).filter(
            User.email == email
        ).first()

        if user is not None:

            user.google_id = google_id

            db.commit()
            db.refresh(user)

    # -----------------------------------------------------
    # Create new user
    # -----------------------------------------------------

    if user is None:

        random_password = os.urandom(
            32
        ).hex()

        user = User(
            name=(
                name
                or email.split("@")[0]
            ),
            email=email,
            google_id=google_id,
            password_hash=password_hash.hash(
                random_password
            ),
            native_language="ar",
            learning_language="en",
            is_active=True
        )

        db.add(user)
        db.commit()
        db.refresh(user)

    # -----------------------------------------------------
    # Check account status
    # -----------------------------------------------------

    if not user.is_active:
        raise HTTPException(
            status_code=403,
            detail="User account is inactive"
        )

    # -----------------------------------------------------
    # Create application JWT
    # -----------------------------------------------------

    access_token = create_access_token(
        user.id
    )

    return {
        "message": "Google login successful",
        "access_token": access_token,
        "token_type": "bearer",
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "native_language": user.native_language,
        "learning_language": user.learning_language
    }


# =========================================================
# Current user
# =========================================================

@router.get("/me")
def get_me(
    current_user: User = Depends(get_current_user)
):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "native_language": current_user.native_language,
        "learning_language": current_user.learning_language
    }