from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi import HTTPException as HTTPExcept
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from src.models import init_db
from src.routes import UserRouter
from src.utils.errors import error_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


user_router = UserRouter()
app = FastAPI(lifespan=lifespan)
app.add_exception_handler(RequestValidationError, error_handler)
app.add_exception_handler(HTTPExcept, error_handler)
app.add_exception_handler(HTTPException, error_handler)
app.add_exception_handler(Exception, error_handler)

app.include_router(user_router)
