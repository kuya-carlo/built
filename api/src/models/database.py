import datetime
import uuid
from enum import Enum
from typing import Optional

from pydantic import EmailStr, field_validator
from sqlmodel import Field, Relationship, SQLModel


class Credentials(SQLModel, table=True):
    """Defines credentials of the user

    Attributes:
        credential_id: unique id of the user credential
        user_id: id of the user credential is connected to
        email: email of the user
        password: password of the user

        user: the user in reference(won't be stored in DB)

    Note:
        whilst the password field is stated as str, it doesn't mean that the password
        won't be encrypted, its just that the password will be stored as-is by whatever
        this api will do.
    """

    credential_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.user_id")
    password_hash: str
    failed_attempts: int = Field(default=0)
    locked_until: Optional[datetime.datetime] = None
    last_login: Optional[datetime.datetime] = None
    password_changed_at: datetime.datetime = Field(
        default_factory=datetime.datetime.now
    )
    refresh_token: Optional[str] = None
    refresh_token_expires: Optional[datetime.datetime] = None
    user: "Users" = Relationship(back_populates="credential")

    @field_validator("password_hash")
    def password_check(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class Users(SQLModel, table=True):
    """Defines user database

    Attributes:
        user_id: unique id of the user
        username: username of the user
        name: name of the user
        email: email of the user
        is_active: is user active?

        activity_logs: back reference to activity logs
        projects: references to the projects the user has
        credential: the user's login credential
    """

    user_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    username: str
    name: str
    email: EmailStr = Field(index=True, unique=True)
    is_active: bool = Field(default=True)

    activity_logs: Optional[list["ActivityLog"]] = Relationship(back_populates="user")
    projects: Optional[list["Project"]] = Relationship(back_populates="user")
    credential: Optional[Credentials] = Relationship(back_populates="user")


class ActivityLog(SQLModel, table=True):
    """Defines activitylog database

    Attributes:
        activity_id: unique id for the activity
        user_id: id of the user who made the request
        project_id: id of the project the action is associated on
        action_type: type of action done
        action_desc: description of the action
        timestamp: timestamp of the said action

        user: backreference to the associated user
        project: reference to the project it was used upon
    """

    activity_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: Optional[uuid.UUID] = Field(foreign_key="users.user_id", index=True)
    project_id: Optional[uuid.UUID] = Field(foreign_key="project.project_id")
    status_code: int = Field(default=200)
    # allow logging of user changes(untied to anything really)
    action_type: str
    action_desc: str
    details: Optional[str] = None
    timestamp: datetime.datetime = Field(
        default_factory=datetime.datetime.now, index=True
    )

    user: Optional[Users] = Relationship(back_populates="activity_logs")
    project: Optional["Project"] = Relationship(back_populates="activity_logs")


class Status(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class Project(SQLModel, table=True):
    """Defines projects database

    Attributes:
        project_id: unique id of the project
        user_id: id of the project owner
        name: name of project
        description: short description of the project
        start_date: date when project started
        end_date: date when project ends
        status: project status

        user: the associated user with the project
        activity_logs: back reference for activities
        tasks: back reference for the tasks
    """

    project_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    user_id: uuid.UUID = Field(foreign_key="users.user_id", index=True)
    name: str
    description: str
    start_date: datetime.date
    end_date: datetime.date
    status: Status = Field(index=True)
    total_budget: float = 0.0

    user: Users = Relationship(back_populates="projects")
    activity_logs: Optional[list["ActivityLog"]] = Relationship(
        back_populates="project"
    )
    tasks: Optional[list["Tasks"]] = Relationship(back_populates="project")
    materials: Optional[list["Materials"]] = Relationship(back_populates="project")
    budgets: Optional[list["ProjectBudget"]] = Relationship(back_populates="project")
    cost_entries: Optional[list["CostEntry"]] = Relationship(back_populates="project")

    @property
    def total_allocated_budget(self) -> float:
        if self.budgets is not None:
            return sum(budget.allocated_amount for budget in self.budgets)
        return 0.0

    @property
    def total_actual_costs(self) -> float:
        if self.cost_entries is not None:
            return sum(cost.amount for cost in self.cost_entries)
        return 0.0

    @property
    def budget_variance(self) -> float:
        return self.total_allocated_budget - self.total_actual_costs

    @property
    def completion_percentage(self) -> float:
        if self.total_allocated_budget == 0:
            return 0.0
        return (self.total_actual_costs / self.total_allocated_budget) * 100


class Tasks(SQLModel, table=True):
    """Defines task database

    Attributes:
        task_id: unique id of the task
        project_id: key to the project this task is based on
        name: task short name
        description: task short description
        due_date: task short description
        status: task status

        project: the header project itself
    """

    task_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="project.project_id")
    name: str
    description: str
    due_date: datetime.date
    status: Status

    project: Optional[Project] = Relationship(back_populates="tasks")


class Materials(SQLModel, table=True):
    """Defines materials database

    Attributes:
        material_id: unique id of the material
        project_id: id of the project material is needed on
        name: name of the material
        qty_needed: count of quantities needed
        qty_acquired: count of quantities acquired
        unit: unit of measurement

        project: the project project_id states is needed
    """

    material_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="project.project_id")
    name: str
    qty_needed: int
    qty_acquired: int
    unit: str
    unit_cost: float = Field(default=0.0)
    total_cost: float = Field(default=0.0)

    project: Optional[Project] = Relationship(back_populates="materials")


class BudgetCategory(Enum):
    MATERIALS = "materials"
    LABOR = "labor"
    EQUIPMENT = "equipment"
    SUBCONTRACTOR = "subcontractor"
    OVERHEAD = "overhead"


class ProjectBudget(SQLModel, table=True):
    """Tracks budget allocation per category"""

    budget_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="project.project_id")
    category: BudgetCategory
    allocated_amount: float = Field(default=0.0)
    spent_amount: float = Field(default=0.0)

    project: Project = Relationship(back_populates="budgets")


class CostEntry(SQLModel, table=True):
    """Tracks actual costs incurred"""

    cost_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: uuid.UUID = Field(foreign_key="project.project_id")
    vendor_name: str = Field(default="Unknown")
    category: BudgetCategory
    description: str
    amount: float
    date_incurred: datetime.date
    vendor: Optional[str] = None
    receipt_reference: Optional[str] = None

    project: Project = Relationship(back_populates="cost_entries")
