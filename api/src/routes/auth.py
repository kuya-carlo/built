import uuid
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Response
from fastapi.routing import APIRouter
from pydantic import BaseModel, EmailStr, field_validator
from sqlmodel import Session, select

from src.models import ErrorResponse, Users
from src.models.database import Credentials
from src.models.response import LoginToken
from src.utils import create, delete, get_session, settings
from src.utils.auth import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from src.utils.common import log


class UserLogin(BaseModel):
    username: str
    password: str


class UserSignup(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "John Black",
                "username": "testuser",
                "email": "john@example.com",
                "password": "p4s5w0rd",
            }
        }
    }
    username: str
    name: str
    email: EmailStr
    password: str

    @field_validator("password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class AuthService(APIRouter):
    def __init__(self):
        super().__init__(tags=["Authentication"])
        self._register_routes()

    def _register_routes(self):
        @self.post(
            "/login",
            responses={
                200: {"description": "Login successfully", "model": LoginToken},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def login(
            user_data: UserLogin,
            response: Response,
            session: Session = Depends(get_session),
            use_cookie: bool = False,
        ):
            user = session.exec(
                select(Users).where(Users.username == user_data.username)
            ).first()

            # Check if user exists
            if not user:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid credentials",
                )
            credential = session.exec(
                select(Credentials).where(Credentials.user_id == user.user_id)
            ).first()
            # Check if credentials exist
            if not credential:
                raise HTTPException(
                    status_code=401,
                    detail=f"No credential associated with user `{user_data.username}`",
                )
            # Check if password is invalid
            if not verify_password(user_data.password, credential.password_hash):
                raise HTTPException(
                    status_code=401,
                    detail="Invalid credentials",
                )
            # Check if account is active
            if not user.is_active:
                raise HTTPException(status_code=403, detail="Account is not active")

            access_token, refresh_token = self._create_token(
                user.username,
                str(user.user_id),
                user.email,
                session,  # Convert to string
            )
            log(
                "LOGIN",
                f"Logged onto the account with id {user.user_id}",
                user.user_id,
                session=session,
            )
            if use_cookie:
                self._set_login_cookie(response, access_token)
            return LoginToken(access_token=access_token)

        @self.post(
            "/signup",
            responses={
                200: {"description": "Signuped successfully", "model": LoginToken},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def signup(
            user_data: UserSignup,
            response: Response,
            session: Session = Depends(get_session),
            use_cookie: bool = False,
        ):
            new_user = None
            try:
                # Check if user already exists
                existing_user = session.exec(
                    select(Users).where(Users.username == user_data.username)
                ).first()
                if existing_user:
                    raise HTTPException(
                        status_code=409, detail="Username already exists"
                    )

                existing_email = session.exec(
                    select(Users).where(Users.email == user_data.email)
                ).first()
                if existing_email:
                    raise HTTPException(status_code=409, detail="Email already exists")

                # Create user
                user_data_dict = user_data.model_dump()
                user_data_dict.pop("password")  # Remove password before creating user
                new_user = Users(**user_data_dict)
                new_user = create(session, new_user)

                # Create credentials
                credential = Credentials(
                    user_id=new_user.user_id,
                    password_hash=get_password_hash(user_data.password),
                )
                create(session, credential)

                # Create tokens
                log(
                    "SIGNUP",
                    f"Created account with id {new_user.user_id}",
                    new_user.user_id,
                    session=session,
                )
                access_token, _ = self._create_token(
                    new_user.username,
                    str(new_user.user_id),
                    new_user.email,
                    session,  # Convert to string
                )
                if use_cookie:
                    self._set_login_cookie(response, access_token)
                return LoginToken(access_token=access_token)

            except HTTPException:
                # Re-raise HTTP exceptions (like 409 conflicts)
                raise
            except Exception:
                # Rollback only if user was created
                if new_user and new_user.user_id:
                    delete(session, new_user.user_id, Users)
                # Re-raise the exception so FastAPI can handle it
                raise

    @staticmethod
    def _create_token(
        username: str,
        user_id: str,
        email: EmailStr,
        session: Session,  # user_id is now string
    ) -> tuple[str, str]:
        data = {
            "sub": username,
            "user_id": user_id,  # This is now a string
            "email": email,
        }
        access_token = create_access_token(data)
        refresh_token = create_refresh_token(data)
        # Convert user_id back to UUID for database lookup
        user_uuid = uuid.UUID(user_id)
        user = session.get(Credentials, user_uuid)
        if user:
            setattr(user, "refresh_token", refresh_token)
            setattr(user, "refresh_token_expires", datetime.now() + timedelta(days=7))
            create(session, user)

        return access_token, refresh_token

    @staticmethod
    def _set_login_cookie(
        response, token: str, key: str = "refresh_token", expiry: int = 7 * 24 * 60 * 60
    ):
        response.set_cookie(
            key=key,
            value=token,
            httponly=True,
            secure=not settings.debug,
            samesite="lax",
            max_age=expiry,
        )
