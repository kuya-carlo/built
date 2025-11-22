import json
import uuid
from typing import List, Optional, Sequence

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select
from src.models import (
    ErrorDescription,
    ErrorResponse,
    Project,
    ProjectAttribute,
    SingleSuccessResponse,
    User,
    UserResponse,
    get_session,
)
from starlette.responses import JSONResponse


class UserCreate(BaseModel):
    model_config = {
        "json_schema_extra": {"example": {"name": "John", "email": "john@example.com"}}
    }
    name: str
    email: str
    user_id: Optional[uuid.UUID] = None


def error_response(status: int, title: str, detail: str) -> JSONResponse:

    error = ErrorResponse(
        result="error",
        errors=[
            ErrorDescription(
                status=status,
                title=title,
                detail=detail,
            )
        ],
    )
    return JSONResponse(status_code=status, content=json.loads(error.json()))


class UserRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/user", tags=["User"])
        self._register_routes()

    def _register_routes(self):
        @self.get(
            "/{user_id}",
            response_model=SingleSuccessResponse[UserResponse],
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
            try:
                user: Optional[User] = session.get(User, user_id)
                if not user:
                    return error_response(
                        status=404,
                        title="User not found",
                        detail=f"User with id {user_id} not found",
                    )
                projects = session.exec(
                    select(Project).where(Project.user_id == user_id)
                ).all()
                return self._parse_user(user, self._parse_projects(projects))
            except Exception as e:
                return error_response(
                    status=500,
                    title="Internal Server Error",
                    detail=str(e),
                )

        @self.post(
            "/",
            response_model=SingleSuccessResponse[UserResponse],
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
            if not user_data.name or not user_data.email:
                return error_response(
                    422, "Validation Error", "name and email are required"
                )
            with session:
                if user_data.user_id and session.get(User, user_data.user_id):
                    return error_response(
                        409,
                        "Conflict in data",
                        f"User with id {user_data.user_id} already exists",
                    )
                if user_data.user_id:
                    user = User(
                        user_id=user_data.user_id,
                        name=user_data.name,
                        email=user_data.email,
                    )
                else:
                    user = User(name=user_data.name, email=user_data.email)
                session.add(user)
                try:

                    session.commit()
                    session.refresh(user)
                except ValidationError as e:
                    session.rollback()
                    return error_response(
                        status=409, title="Conflict in data", detail=str(e)
                    )
                except IntegrityError as e:
                    session.rollback()
                    return error_response(
                        status=422, title="Validation Error", detail=str(e.orig)
                    )
                except Exception as e:
                    session.rollback()
                    return error_response(
                        status=500,
                        title="Internal Server Error",
                        detail=str(e),
                    )
            return self._parse_user(user)

    @staticmethod
    def _parse_projects(projects: Sequence[Project]) -> List[ProjectAttribute]:
        parsed_projects = []
        for project in projects:
            parsed_projects.append(
                ProjectAttribute(
                    id=project.project_id,
                    user_id=project.user_id,
                    name=project.name,
                    description=project.description,
                    start_date=project.start_date,
                    end_date=project.end_date,
                    status=project.status,
                )
            )
        return parsed_projects

    @staticmethod
    def _parse_user(
        user: User, projects: Optional[List[ProjectAttribute]] = None
    ) -> SingleSuccessResponse[UserResponse]:
        return SingleSuccessResponse[UserResponse](
            data=UserResponse(
                id=user.user_id,
                name=user.name,
                email=user.email,
                projects=projects if projects else [],
            )
        )
