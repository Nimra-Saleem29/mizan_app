"""
Wakeel وکیل — Authentication Router
======================================
Handles user registration, login, logout, and profile using Supabase Auth.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger
from supabase.client import AsyncClient

from database import get_supabase
from models.schemas import (
    AuthResponse,
    LoginRequest,
    SignUpRequest,
    UserProfileResponse,
)

router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# POST /auth/signup
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Wakeel user",
)
async def signup(
    payload: SignUpRequest,
    db: AsyncClient = Depends(get_supabase),
) -> AuthResponse:
    """
    Creates a new user in Supabase Auth and a matching profile row
    in public.users (via the DB trigger in schema.sql).

    The preferred_language is stored in user metadata so the trigger
    can populate the profile row automatically.
    """
    logger.info(f"[/auth/signup] Attempting signup for: {payload.email}")

    try:
        response = await db.auth.sign_up({
            "email": payload.email,
            "password": payload.password,
            "options": {
                "data": {
                    "full_name": payload.full_name,
                    "preferred_language": payload.preferred_language,
                }
            }
        })
    except Exception as exc:
        logger.error(f"[/auth/signup] Supabase error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    if not response.user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signup failed. Email may already be registered.",
        )

    # Supabase may require email confirmation depending on your project settings.
    # If so, session will be None until the user confirms their email.
    session = response.session
    access_token = session.access_token if session else "email-confirmation-required"

    logger.info(f"[/auth/signup] ✓ User created: {response.user.id}")

    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=response.user.id,
        full_name=payload.full_name,
        preferred_language=payload.preferred_language,
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /auth/login
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/login",
    response_model=AuthResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password",
)
async def login(
    payload: LoginRequest,
    db: AsyncClient = Depends(get_supabase),
) -> AuthResponse:
    """
    Authenticates the user via Supabase and returns a JWT access token.
    Store this token in the app and send it as:
    Authorization: Bearer <token>
    on all subsequent requests.
    """
    logger.info(f"[/auth/login] Login attempt: {payload.email}")

    try:
        response = await db.auth.sign_in_with_password({
            "email": payload.email,
            "password": payload.password,
        })
    except Exception as exc:
        logger.warning(f"[/auth/login] Failed for {payload.email}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. غلط ای میل یا پاسورڈ۔",
        )

    if not response.user or not response.session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login failed. Please check your credentials.",
        )

    # Fetch profile from public.users for full_name + language
    try:
        profile_result = await (
            db.table("users")
            .select("full_name, preferred_language")
            .eq("id", str(response.user.id))
            .single()
            .execute()
        )
        profile = profile_result.data or {}
    except Exception:
        profile = {}

    full_name = profile.get("full_name", "")
    preferred_language = profile.get("preferred_language", "urdu")

    logger.info(f"[/auth/login] ✓ Login successful: {response.user.id}")

    return AuthResponse(
        access_token=response.session.access_token,
        token_type="bearer",
        user_id=response.user.id,
        full_name=full_name,
        preferred_language=preferred_language,
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /auth/logout
# ─────────────────────────────────────────────────────────────────────────────
@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Logout current session",
)
async def logout(
    db: AsyncClient = Depends(get_supabase),
) -> dict:
    """Invalidates the current Supabase session."""
    try:
        await db.auth.sign_out()
        logger.info("[/auth/logout] ✓ Session signed out")
    except Exception as exc:
        logger.warning(f"[/auth/logout] Sign out error (non-fatal): {exc}")

    return {"message": "Logged out successfully. خدا حافظ!"}


# ─────────────────────────────────────────────────────────────────────────────
# GET /auth/me
# ─────────────────────────────────────────────────────────────────────────────
@router.get(
    "/me",
    response_model=UserProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
)
async def get_me(
    db: AsyncClient = Depends(get_supabase),
) -> UserProfileResponse:
    """
    Returns the authenticated user's profile from public.users.
    The client must send: Authorization: Bearer <access_token>
    """
    try:
        user_response = await db.auth.get_user()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token. دوبارہ لاگ ان کریں۔",
        )

    if not user_response or not user_response.user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated.",
        )

    user_id = str(user_response.user.id)

    try:
        result = await (
            db.table("users")
            .select("*")
            .eq("id", user_id)
            .single()
            .execute()
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found.",
        )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found. Please sign up again.",
        )

    return UserProfileResponse(**result.data)
