from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from src.models import init_db
from src.routes import UserRouter
from src.utils.errors import validation_exception_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


user_router = UserRouter()
app = FastAPI(lifespan=lifespan)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.include_router(user_router)
