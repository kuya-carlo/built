import datetime
import uuid
from typing import Generic, List, Literal, Optional, TypeVar

from pydantic import BaseModel, EmailStr, Field

from .database import Status

T = TypeVar("T")


class BaseResponse(BaseModel):
    result: Literal["ok", "error"]


class SuccessResponse(BaseResponse):
    result: Literal["ok", "error"] = "ok"


class SingleSuccessResponse(BaseResponse, Generic[T]):
    result: Literal["ok", "error"] = "ok"
    response: Literal["entity", "collection"] = "entity"
    data: T


class GroupSuccessResponse(BaseResponse, Generic[T]):
    result: Literal["ok", "error"] = "ok"
    response: Literal["entity", "collection"] = "collection"
    data: List[T]


class ErrorResponse(BaseResponse):
    result: Literal["ok", "error"] = "error"
    errors: List["ErrorDescription"]


class ErrorDescription(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    status: int
    title: str
    detail: str
    context: Optional[str] = None


class UserSummary(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr


class ProjectAttribute(BaseModel):
    id: uuid.UUID = Field(...)
    user_id: uuid.UUID = Field(...)
    name: str
    description: str
    start_date: datetime.date
    end_date: datetime.date
    status: Status


class ProjectResponse(ProjectAttribute):
    owner: UserSummary


class TaskResponse(BaseModel):
    id: uuid.UUID = Field(...)
    project_id: uuid.UUID = Field(...)
    name: str
    description: str
    due_date: datetime.date
    status: Status


class MaterialResponse(BaseModel):
    id: uuid.UUID = Field(...)
    project_id: uuid.UUID = Field(...)
    name: str
    qty_needed: int
    qty_acquired: int
    unit: str
    project: ProjectAttribute


class UserResponse(BaseModel):
    id: uuid.UUID = Field(...)
    name: str
    email: EmailStr
    projects: List[ProjectAttribute] = []


class ActivityLogResponse(BaseModel):

    id: uuid.UUID = Field(...)
    user_id: Optional[uuid.UUID] = None
    project_id: Optional[uuid.UUID] = None
    status_code: int = Field(default=200)
    # allow logging of user changes(untied to anything really)
    action_type: str
    action_desc: str
    details: Optional[str] = None
    timestamp: datetime.datetime
