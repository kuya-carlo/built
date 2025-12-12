import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr
from sqlmodel import Session, select
from starlette.responses import JSONResponse

from src.models import (
    ErrorResponse,
    Project,
    ProjectAttribute,
    SingleSuccessResponse,
    SuccessResponse,
    UserResponse,
    Users,
)
from src.utils import create, delete, get_session, log, prep_create, read, update

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class UserCreate(BaseModel):
    model_config = {
        "json_schema_extra": {"example": {"name": "John", "email": "john@example.com"}}
    }
    name: str
    email: EmailStr
    username: str
    user_id: Optional[uuid.UUID] = None


class UserUpdate(BaseModel):
    model_config = {
        "json_schema_extra": {"example": {"name": "John", "email": "john@example.com"}}
    }

    name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/user", tags=["User"])
        self._register_routes()

    def _register_routes(self):
        @self.get(
            "/{user_id}",
            responses={
                200: {
                    "description": "User exists",
                    "model": SingleSuccessResponse[UserResponse],
                },
                404: {"description": "User not found", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def get_user(user_id: uuid.UUID, session: Session = Depends(get_session)):
            user = read(session, user_id, Users)
            log(
                session=session,
                action="GET_USERPROFILE",
                message=f"Got user profile for {user_id}",
                user_id=user_id,
            )
            return self._parse_user(user, session)

        @self.post(
            "/",
            responses={
                200: {
                    "description": "User created",
                    "model": SingleSuccessResponse[UserResponse],
                },
                409: {"description": "Conflict", "model": ErrorResponse},
                422: {"description": "Validation Error", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def create_user(
            user_data: UserCreate,
            session: Session = Depends(get_session),
        ):
            user = prep_create(user_data, "user_id")
            user = Users.model_validate(user)
            new_user = create(session, user)
            log(
                "CREATE_USERPROFILE",
                f"Created user profile for {user_data.user_id}",
                new_user.user_id,
                session=session,
            )
            return self._parse_user(new_user)

        @self.patch(
            "/{user_id}",
            responses={
                200: {
                    "description": "Updated user profile successfully",
                    "model": SingleSuccessResponse[UserResponse],
                },
                422: {"description": "Validation Error", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def update_user(
            user_id: uuid.UUID,
            user_data: UserUpdate,
            session: Session = Depends(get_session),
        ):
            updated_user = update(session, user_id, user_data, Users)
            log(
                "UPDATE_USERPROFILE",
                f"Updated user profile of {user_id}",
                user_id=user_id,
                session=session,
            )
            return self._parse_user(updated_user)

        @self.delete(
            "/{user_id}",
            responses={
                200: {
                    "description": "User profile deleted",
                    "model": SuccessResponse,
                },
                404: {"description": "User not found", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def delete_user(
            user_id: uuid.UUID,
            session: Session = Depends(get_session),
        ):
            delete(session, user_id, Users)
            log(
                "DELETE_USERPROFILE",
                f"Deleted user profile of {user_id}",
                user_id,
                session=session,
            )
            return JSONResponse(
                status_code=200, content=SuccessResponse(result="ok").model_dump_json()
            )

    @staticmethod
    def _parse_user(
        user: Users, session: Optional[Session] = None
    ) -> SingleSuccessResponse[UserResponse]:
        projects = None
        if session:
            projects = session.exec(
                select(Project).where(Project.user_id == user.user_id).limit(5)
            ).all()
            projects = [
                ProjectAttribute(
                    id=p.project_id,
                    user_id=p.user_id,
                    name=p.name,
                    description=p.description,
                    start_date=p.start_date,
                    end_date=p.end_date,
                    status=p.status,
                    total_budget=p.total_budget,
                )
                for p in projects
            ]

        return SingleSuccessResponse[UserResponse](
            data=UserResponse(
                id=user.user_id,
                username=user.username,
                name=user.name,
                email=user.email,
                is_active=user.is_active,
                projects=projects if projects else [],
            )
        )
