"""SeshOps authentication and session management endpoints.

Provides operator registration, login, session lifecycle, and the
``get_current_user`` / ``get_current_session`` dependency functions used
by all protected endpoints.
"""


import uuid
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
)
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import bind_context, logger
from app.core.sanitisation import sanitize_email, sanitize_string, validate_password_strength
from app.core.security import (
    SessionResponse,
    Token,
    TokenResponse,
    UserCreate,
    UserResponse,
    create_access_token,
    verify_token,
)
from app.models.session import Session
from app.models.user import User
from app.services.database import DatabaseService

router = APIRouter()
security = HTTPBearer()
db_service = DatabaseService()


# ── Dependency functions ─────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Extract and validate the operator from the Bearer token."""
    try:
        token = sanitize_string(credentials.credentials)
        user_id = verify_token(token)

        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await db_service.get_user(int(user_id))
        if user is None:
            raise HTTPException(
                status_code=404,
                detail="Operator not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        bind_context(user_id=int(user_id))
        return user

    except ValueError as exc:
        logger.error("seshops_token_validation_failed", error=str(exc))
        raise HTTPException(
            status_code=422,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Session:
    """Extract and validate the triage session from the Bearer token."""
    try:
        token = sanitize_string(credentials.credentials)
        session_id = verify_token(token)

        if session_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        session_id = sanitize_string(session_id)
        session = await db_service.get_session(session_id)

        if session is None:
            raise HTTPException(
                status_code=404,
                detail="Session not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        bind_context(user_id=session.user_id)
        return session

    except ValueError as exc:
        logger.error("seshops_token_validation_failed", error=str(exc))
        raise HTTPException(
            status_code=422,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/register", response_model=UserResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
async def register_operator(request: Request, user_data: UserCreate):
    """Register a new SeshOps operator account."""
    try:
        email = sanitize_email(user_data.email)
        password = user_data.password.get_secret_value()
        validate_password_strength(password)

        if await db_service.get_user_by_email(email):
            raise HTTPException(status_code=400, detail="Email already registered")

        user = await db_service.create_user(
            email=email, password=User.hash_password(password)
        )
        token = create_access_token(str(user.id))
        return UserResponse(id=user.id, email=user.email, token=token)

    except ValueError as exc:
        logger.error("seshops_registration_failed", error=str(exc))
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["login"][0])
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    grant_type: str = Form(default="password"),
):
    """Authenticate an existing SeshOps operator and issue a JWT."""
    try:
        username = sanitize_string(username)
        password = sanitize_string(password)
        grant_type = sanitize_string(grant_type)

        if grant_type != "password":
            raise HTTPException(
                status_code=400,
                detail="Unsupported grant type. Must be 'password'",
            )

        user = await db_service.get_user_by_email(username)
        if not user or not user.verify_password(password):
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = create_access_token(str(user.id))
        return TokenResponse(
            access_token=token.access_token,
            token_type="bearer",
            expires_at=token.expires_at,
        )

    except ValueError as exc:
        logger.error("seshops_login_failed", error=str(exc))
        raise HTTPException(status_code=422, detail=str(exc))


@router.post("/session", response_model=SessionResponse)
async def create_session(user: User = Depends(get_current_user)):
    """Create a new triage session for the authenticated operator."""
    try:
        session_id = str(uuid.uuid4())
        session = await db_service.create_session(session_id, user.id)
        token = create_access_token(session_id)

        logger.info(
            "seshops_session_created",
            session_id=session_id,
            user_id=user.id,
        )
        return SessionResponse(
            session_id=session_id, name=session.name, token=token
        )

    except ValueError as exc:
        logger.error("seshops_session_creation_failed", error=str(exc))
        raise HTTPException(status_code=422, detail=str(exc))


@router.patch("/session/{session_id}/name", response_model=SessionResponse)
async def update_session_name(
    session_id: str,
    name: str = Form(...),
    current_session: Session = Depends(get_current_session),
):
    """Rename an existing triage session."""
    try:
        sid = sanitize_string(session_id)
        new_name = sanitize_string(name)

        if sid != sanitize_string(current_session.id):
            raise HTTPException(status_code=403, detail="Cannot modify other sessions")

        session = await db_service.update_session_name(sid, new_name)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found")
        token = create_access_token(sid)
        return SessionResponse(session_id=sid, name=session.name, token=token)

    except ValueError as exc:
        logger.error("seshops_session_rename_failed", error=str(exc))
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    current_session: Session = Depends(get_current_session),
):
    """Delete a triage session."""
    try:
        sid = sanitize_string(session_id)
        if sid != sanitize_string(current_session.id):
            raise HTTPException(status_code=403, detail="Cannot delete other sessions")

        await db_service.delete_session(sid)
        logger.info("seshops_session_deleted", session_id=sid)

    except ValueError as exc:
        logger.error("seshops_session_deletion_failed", error=str(exc))
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/sessions", response_model=List[SessionResponse])
async def get_operator_sessions(user: User = Depends(get_current_user)):
    """List all triage sessions for the authenticated operator."""
    try:
        sessions = await db_service.get_user_sessions(user.id)
        return [
            SessionResponse(
                session_id=sanitize_string(s.id),
                name=sanitize_string(s.name),
                token=create_access_token(s.id),
            )
            for s in sessions
        ]
    except ValueError as exc:
        logger.error("seshops_sessions_list_failed", error=str(exc))
        raise HTTPException(status_code=422, detail=str(exc))
