from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import HTTPException as HTTPExcept
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
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

app = FastAPI(lifespan=lifespan, title="Built Cost Management API")
app.add_exception_handler(RequestValidationError, error_handler)
app.add_exception_handler(HTTPExcept, error_handler)
app.add_exception_handler(HTTPException, error_handler)
app.add_exception_handler(Exception, error_handler)

app.include_router(user_router)
app.include_router(projects_router)
app.include_router(material_router)
app.include_router(activity_router)
app.include_router(task_router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Built | Cost Management API",
        version="0.1.1",
        description="A cost management system for construction companies",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
