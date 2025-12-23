# api/src/models/database_config.py
from sqlmodel import Session, create_engine

from .config import settings

engine = create_engine(settings.database_url)


def init_db():
    from src.models.database import SQLModel

    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session
