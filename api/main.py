from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import HTTPException as HTTPExcept
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from src.models import init_db
from src.routes import (
    ActivityLogRouter,
    MaterialRouter,
    ProjectRouter,
    TaskRouter,
    UserRouter,
)
from src.utils.errors import error_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


user_router = UserRouter()
projects_router = ProjectRouter()
material_router = MaterialRouter()
activity_router = ActivityLogRouter()
task_router = TaskRouter()

app = FastAPI(lifespan=lifespan)
app.add_exception_handler(RequestValidationError, error_handler)
app.add_exception_handler(HTTPExcept, error_handler)
app.add_exception_handler(HTTPException, error_handler)
app.add_exception_handler(Exception, error_handler)

app.include_router(user_router)
app.include_router(projects_router)
app.include_router(material_router)
app.include_router(activity_router)
app.include_router(task_router)
