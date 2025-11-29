from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import HTTPException as HTTPExcept
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from starlette.exceptions import HTTPException

from src.routes import (
    ActivityLogRouter,
    AuthService,
    MaterialRouter,
    ProjectRouter,
    TaskRouter,
    UserRouter,
)
from src.utils import init_db, settings
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
auth_service = AuthService()

app = FastAPI(lifespan=lifespan, title=settings.project_title)
app.add_exception_handler(RequestValidationError, error_handler)
app.add_exception_handler(HTTPExcept, error_handler)
app.add_exception_handler(HTTPException, error_handler)
app.add_exception_handler(Exception, error_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.backend_cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
app.include_router(user_router)
app.include_router(projects_router)
app.include_router(material_router)
app.include_router(activity_router)
app.include_router(task_router)
app.include_router(auth_service)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=settings.project_name,
        version=settings.version,
        description=settings.project_description,
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
