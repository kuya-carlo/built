import datetime
import uuid
from typing import List, Optional

from fastapi import APIRouter, Body, Depends
from pydantic import BaseModel
from sqlmodel import Session
from starlette.responses import JSONResponse

from src.models import (
    ErrorResponse,
    GroupSuccessResponse,
    SingleSuccessResponse,
    Status,
    SuccessResponse,
    TaskResponse,
    Tasks,
)
from src.utils import create, delete, get_session, log, prep_create, read, update
from src.utils.helper import FilterMode, db_filter


class TaskCreate(BaseModel):
    model_config = {
        "json_schema_extra": {
            "example": {
                "project_id": "John",
                "name": "Create 15 pre-engineered slabs",
                "description": "Create 15 pre-engineered slabs with the size of 15m x 30m",
                "due_date": "2025-12-01",
                "status": "in_progress",
            }
        }
    }
    task_id: Optional[uuid.UUID] = None
    project_id: uuid.UUID
    name: str
    description: str
    due_date: datetime.date
    status: Status


class TaskUpdate(BaseModel):
    model_config = {
        "json_schema_extra": {"example": {"name": "John", "email": "john@example.com"}}
    }
    project_id: Optional[uuid.UUID] = None
    name: Optional[str] = None
    description: Optional[str] = None
    due_date: Optional[datetime.date] = None
    status: Optional[Status] = None


class TaskRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/task", tags=["Task"])
        self._register_routes()

    def _register_routes(self):
        @self.get(
            "/{task_id}",
            responses={
                200: {
                    "description": "Task exists",
                    "model": SingleSuccessResponse[TaskResponse],
                },
                404: {"description": "Task not found", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def get_task(task_id: uuid.UUID, session: Session = Depends(get_session)):
            task = read(session, task_id, Tasks)
            log(
                session=session,
                action="GET_TASK",
                message=f"Got task with id {task_id}",
            )
            return self._parse_task(task)

        @self.post(
            "/",
            responses={
                200: {
                    "description": "Task created",
                    "model": SingleSuccessResponse[TaskResponse],
                },
                409: {"description": "Conflict", "model": ErrorResponse},
                422: {"description": "Validation Error", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def create_task(
            task_data: TaskCreate,
            session: Session = Depends(get_session),
        ):
            task_dict = prep_create(task_data, "task_id")
            task = Tasks.model_validate(task_dict)
            new_task = create(session, task)
            log(
                "CREATE_TASK",
                f"Created task with id {new_task.task_id}",
                session,
            )
            return self._parse_task(new_task)

        @self.patch(
            "/{task_id}",
            responses={
                200: {
                    "description": "Updated task successfully",
                    "model": SingleSuccessResponse[TaskResponse],
                },
                422: {"description": "Validation Error", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def update_task(
            task_id: uuid.UUID,
            task_data: TaskUpdate = Body(...),
            session: Session = Depends(get_session),
        ):
            updated_task = update(session, task_id, task_data, Tasks)
            log(
                "UPDATE_TASK",
                f"Updated task with id {task_id}",
                task_id,
                session,
            )
            return self._parse_task(updated_task)

        @self.delete(
            "/{task_id}",
            responses={
                200: {
                    "description": "Task deleted",
                    "model": SuccessResponse,
                },
                404: {"description": "Task not found", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def delete_task(
            task_id: uuid.UUID,
            session: Session = Depends(get_session),
        ):
            delete(session, task_id, Tasks)
            log(
                "DELETE_TASK",
                f"Deleted task with id {task_id}",
                task_id,
                session,
            )
            return JSONResponse(
                status_code=200, content=SuccessResponse(result="ok").model_dump_json()
            )

        @self.get(
            "/",
            responses={
                200: {
                    "description": "Successfully got tasks",
                    "model": GroupSuccessResponse[TaskResponse],
                },
                404: {"description": "Task not found", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def get_tasks(
            project_id: uuid.UUID,
            limit: int = 5,
            offset: int = 0,
            session: Session = Depends(get_session),
        ):
            tasks = db_filter(
                session,
                Tasks,
                project_id,
                Tasks.project_id,
                Tasks.name,
                FilterMode.ALL,
                limit,
                offset,
            )
            if not tasks:
                log(
                    "LIST_TASKS",
                    f"Listed task from project {project_id}",
                    code=404,
                    session=session,
                )
                raise ValueError(f"Materials with project id {project_id} not found")
            log(
                action="LIST_TASKS",
                message=f"Listed task from project {project_id}",
                session=session,
            )
            return self._parse_tasks(tasks)

    @staticmethod
    def _parse_task(task: Tasks) -> SingleSuccessResponse[TaskResponse]:
        return SingleSuccessResponse[TaskResponse](
            data=TaskResponse(
                id=task.task_id,
                project_id=task.project_id,
                name=task.name,
                description=task.description,
                due_date=task.due_date,
                status=task.status,
            )
        )

    @staticmethod
    def _parse_tasks(tasks: List[Tasks]) -> GroupSuccessResponse[TaskResponse]:
        return GroupSuccessResponse(
            data=[
                TaskResponse(
                    id=task.task_id,
                    project_id=task.project_id,
                    name=task.name,
                    description=task.description,
                    due_date=task.due_date,
                    status=task.status,
                )
                for task in tasks
            ]
        )


if __name__ == "__main__":
    pass
