import datetime
import uuid
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session
from starlette.responses import JSONResponse

from src.models import (
    ErrorResponse,
    Project,
    ProjectResponse,
    SingleSuccessResponse,
    Status,
    SuccessResponse,
    User,
    UserSummary,
    get_session,
)
from src.utils import create, delete, log, prep_create, read, update


class ProjectCreate(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "John",
                "description": "my first project",
                "start_date": "2020-01-01",
                "end_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "status": "pending",
            }
        }
    }
    project_id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    name: str
    description: str
    start_date: datetime.date
    end_date: datetime.date
    status: Status


class ProjectUpdate(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "John",
                "description": "my first project",
                "start_date": "2020-01-01",
                "end_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "status": "pending",
            }
        }
    }
    name: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    description: Optional[str] = None
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    status: Optional[Status] = None


class ProjectRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/project", tags=["Project"])
        self._register_routes()

    def _register_routes(self):
        @self.get(
            "/{project_id}",
            responses={
                200: {
                    "description": "Project exists",
                    "model": SingleSuccessResponse[ProjectResponse],
                },
                404: {"description": "Project not found", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def get_project(project_id: uuid.UUID, session: Session = Depends(get_session)):
            project = read(session, project_id, Project)
            log(
                "GET_PROJECT",
                f"Got project info for {project_id}",
                project.user_id,
                session,
            )
            return self._parse_project(project, session)

        @self.post(
            "/",
            responses={
                200: {
                    "description": "Project created",
                    "model": SingleSuccessResponse[ProjectResponse],
                },
                409: {"description": "Conflict", "model": ErrorResponse},
                422: {"description": "Validation Error", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def create_project(
            project_data: ProjectCreate,
            session: Session = Depends(get_session),
        ):
            project_dict = prep_create(project_data, "project_id")
            project = Project.model_validate(project_dict)
            new_project = create(session, project)
            log(
                "CREATE_PROJECT",
                f"Created project with id of {new_project.project_id}",
                new_project.project_id,
                session,
            )
            return self._parse_project(new_project, session)

        @self.patch(
            "/{project_id}",
            responses={
                200: {
                    "description": "Updated project successfully",
                    "model": SingleSuccessResponse[ProjectResponse],
                },
                422: {"description": "Validation Error", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def update_project(
            project_id: uuid.UUID,
            project_data: ProjectUpdate,
            session: Session = Depends(get_session),
        ):
            updated_project = update(session, project_id, project_data, Project)
            log(
                "UPDATE_PROJECT",
                f"Updated project with id {project_id}",
                project_id,
                session,
            )
            return self._parse_project(updated_project, session)

        @self.delete(
            "/{project_id}",
            responses={
                200: {
                    "description": "Project deleted",
                    "model": SuccessResponse,
                },
                404: {"description": "Project not found", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def delete_project(
            project_id: uuid.UUID,
            session: Session = Depends(get_session),
        ):
            delete(session, project_id, Project)
            log(
                "DELETE_PROJECT",
                f"Deleted project with id {project_id}",
                project_id,
                session,
            )
            return JSONResponse(
                status_code=200, content=SuccessResponse(result="ok").model_dump_json()
            )

    @staticmethod
    def _parse_project(
        project: Project, session: Optional[Session] = None
    ) -> SingleSuccessResponse[ProjectResponse]:
        user_summary = None
        if session:
            user_obj = read(session, project.user_id, User)
            if user_obj:
                # Convert User to UserSummary
                user_summary = UserSummary(
                    id=user_obj.user_id, name=user_obj.name, email=user_obj.email
                )

        return SingleSuccessResponse[ProjectResponse](
            data=ProjectResponse(
                id=project.project_id,
                name=project.name,
                user_id=project.user_id,
                description=project.description,
                start_date=project.start_date,
                end_date=project.end_date,
                status=project.status,
                owner=user_summary,
            )
        )
