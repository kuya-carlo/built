import datetime
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session, select
from starlette.responses import JSONResponse

from src.models import (
    ErrorResponse,
    GroupSuccessResponse,
    Project,
    ProjectAttribute,
    ProjectResponse,
    SingleSuccessResponse,
    Status,
    SuccessResponse,
    Users,
    UserSummary,
)
from src.models.database import CostEntry
from src.utils import create, delete, get_session, log, prep_create, read, update
from src.utils.helper import FilterMode, db_filter


class ProjectCreate(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "John",
                "description": "my first project",
                "start_date": "2020-01-01",
                "end_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "total_budget": 7107.63,
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
    total_budget: float
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
    total_budget: Optional[float] = None
    status: Optional[Status] = None


class CostEntryCreate(BaseModel):
    description: str
    amount: float
    category: str
    vendor_name: str = "Unknown"


class ProjectFinancialSummary(BaseModel):
    project_name: str
    total_budget: float
    total_actual: float
    budget_remaining: float
    cost_breakdown: list[dict]


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
                project_id=project_id,
                session=session,
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
                project_id=new_project.project_id,
                session=session,
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
                project_id=project_id,
                session=session,
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
                project_id=project_id,
                session=session,
            )
            return JSONResponse(
                status_code=200, content=SuccessResponse(result="ok").model_dump_json()
            )

        @self.get(
            "/{project_id}/financials",
            responses={
                200: {
                    "description": "Project financial summary",
                    "model": SingleSuccessResponse[ProjectFinancialSummary],
                },
                404: {"description": "Project not found", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def get_project_financials(
            project_id: uuid.UUID, session: Session = Depends(get_session)
        ):
            """Get budget vs actual costs for a project"""
            project = session.get(Project, project_id)
            if not project:
                return {"error": "Project not found"}

            # Calculate totals from cost entries
            cost_entries = session.exec(
                select(CostEntry).where(CostEntry.project_id == project_id)
            ).all()

            cost_entries = db_filter(
                session,
                CostEntry,
                project_id,
                CostEntry.project_id,
                CostEntry.date_incurred,
                FilterMode.ALL,
            )

            if isinstance(cost_entries, list):
                total_actual = sum(cost.amount for cost in cost_entries)
                cost_breakdown = [
                    {
                        "category": cost.category,
                        "amount": cost.amount,
                        "vendor": cost.vendor_name,
                        "description": cost.description,
                        "date": (
                            cost.date_incurred.isoformat()
                            if cost.date_incurred
                            else None
                        ),
                    }
                    for cost in cost_entries
                ]
            elif cost_entries is not None:
                total_actual = cost_entries.amount if cost_entries else 0
                cost: CostEntry = cost_entries
                cost_breakdown = [
                    {
                        "category": cost.category,
                        "amount": cost.amount,
                        "vendor": cost.vendor_name,
                        "description": cost.description,
                        "date": (
                            cost.date_incurred.isoformat()
                            if cost.date_incurred
                            else None
                        ),
                    }
                ]
            else:
                total_actual = 0
                cost_breakdown = []

            budget_remaining = project.total_budget - total_actual

            financial_data = ProjectFinancialSummary(
                project_name=project.name,
                total_budget=project.total_budget,
                total_actual=total_actual,
                budget_remaining=budget_remaining,
                cost_breakdown=cost_breakdown,
            )

            log(
                "GET_PROJECT_FINANCIALS",
                f"Retrieved financials for project {project_id}",
                project_id=project_id,
                session=session,
            )

            return SingleSuccessResponse[ProjectFinancialSummary](data=financial_data)

        @self.post(
            "/{project_id}/costs",
            responses={
                200: {
                    "description": "Cost added successfully",
                    "model": SingleSuccessResponse[CostEntry],
                },
                404: {"description": "Project not found", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def add_project_cost(
            project_id: uuid.UUID,
            cost_data: CostEntryCreate,
            session: Session = Depends(get_session),
        ):
            """Add a cost entry to project"""
            project = session.get(Project, project_id)
            if not project:
                return {"error": "Project not found"}

            cost_entry = CostEntry(
                project_id=project_id,
                description=cost_data.description,
                amount=cost_data.amount,
                category=cost_data.category,
                vendor_name=cost_data.vendor_name,
                date_incurred=datetime.date.today(),
            )
            create(session, cost_entry)

            log(
                "ADD_PROJECT_COST",
                f"Added cost ${cost_data.amount} for {cost_data.description} to project {project_id}",
                project_id=project_id,
                session=session,
            )

            return SingleSuccessResponse(data=cost_entry)

        @self.get(
            "/",
            responses={
                200: {
                    "description": "Successfully got projects",
                    "model": GroupSuccessResponse[ProjectAttribute],
                },
                404: {
                    "description": "Project from user not found",
                    "model": ErrorResponse,
                },
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def list_projects(
            user_id: uuid.UUID,
            limit: int = 5,
            offset: int = 0,
            session: Session = Depends(get_session),
        ):
            projects = db_filter(
                session,
                Project,
                user_id,
                Project.user_id,
                Project.end_date,
                FilterMode.ALL,
                limit,
                offset,
            )
            if not projects:
                log(
                    "LIST_PROJECT",
                    f"Listed projects from user {user_id}",
                    code=404,
                    user_id=user_id,
                    session=session,
                )
                return self._parse_projects([])

            log(
                "LIST_PROJECT",
                f"Listed projects from user {user_id}",
                user_id=user_id,
                session=session,
            )
            return self._parse_projects(projects)

    @staticmethod
    def _parse_project(
        project: Project, session: Optional[Session] = None
    ) -> SingleSuccessResponse[ProjectResponse]:
        user_summary = None
        if session:
            user_obj = read(session, project.user_id, Users)
            if user_obj:
                # Convert User to UserSummary
                user_summary = UserSummary(
                    id=user_obj.user_id,
                    username=user_obj.username,
                    name=user_obj.name,
                    email=user_obj.email,
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
                total_budget=project.total_budget,
                owner=user_summary,
            )
        )

    @staticmethod
    def _parse_projects(
        projects: List[Project],
    ) -> GroupSuccessResponse[ProjectAttribute]:
        return GroupSuccessResponse(
            data=[
                ProjectAttribute(
                    id=project.project_id,
                    name=project.name,
                    user_id=project.user_id,
                    description=project.description,
                    start_date=project.start_date,
                    end_date=project.end_date,
                    total_budget=project.total_budget,
                    status=project.status,
                )
                for project in projects
            ]
        )
