import datetime
import uuid
from enum import Enum
from typing import Optional

from pydantic import EmailStr
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine


class User(SQLModel, table=True):
    """Defines user database

    Attributes:
        user_id: unique id of the user
        name: name of the user
        email: email of the user

        activity_logs: back reference to activity logs
        projects: references to the projects the user has
    """

    user_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str
    email: EmailStr = Field(index=True, unique=True)

    activity_logs: Optional[list["ActivityLog"]] = Relationship(back_populates="user")
    projects: Optional[list["Project"]] = Relationship(back_populates="user")


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
    user_id: Optional[uuid.UUID] = Field(foreign_key="user.user_id")
    project_id: Optional[uuid.UUID] = Field(foreign_key="project.project_id")
    status_code: int = Field(default=200)
    # allow logging of user changes(untied to anything really)
    action_type: str
    action_desc: str
    details: Optional[str] = None
    timestamp: datetime.datetime = Field(
        default_factory=datetime.datetime.now, index=True
    )

    user: Optional[User] = Relationship(back_populates="activity_logs")
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

    user_id: uuid.UUID = Field(foreign_key="user.user_id")
    name: str
    description: str
    start_date: datetime.date
    end_date: datetime.date
    status: Status

    user: User = Relationship(back_populates="projects")
    activity_logs: Optional[list["ActivityLog"]] = Relationship(
        back_populates="project"
    )
    tasks: Optional[list["Tasks"]] = Relationship(back_populates="project")
    materials: Optional[list["Materials"]] = Relationship(back_populates="project")


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

    project: Optional[Project] = Relationship(back_populates="materials")


# DB
DATABASE_URL = "sqlite:///./app.db"
DATABASE_TEST = "sqlite:///:memory:"

engine = create_engine(DATABASE_URL, echo=True)


def init_db():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
