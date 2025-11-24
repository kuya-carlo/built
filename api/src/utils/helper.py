import uuid
from typing import Type, TypeVar

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

T = TypeVar("T")


# TODO: Move the errors to error class for it to sort.
def create(session: Session, obj: Type[T]) -> Type[T]:
    session.add(obj)
    try:
        session.commit()
        session.refresh(obj)
        assert obj is not None
        return obj
    except IntegrityError as e:
        session.rollback()
        raise HTTPException(409, detail=str(e.orig))
    except ValidationError as e:
        session.rollback()
        raise HTTPException(422, detail=str(e))
    except Exception as e:
        session.rollback()
        raise HTTPException(500, detail=str(e))


def read(session: Session, obj_id: uuid.UUID, db: Type[T], raise_empty=True) -> T:
    try:
        obj = session.get(db, obj_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database read error: {e}")
    if not obj and raise_empty:
        raise HTTPException(
            status_code=404, detail=f"{db.__name__} with id {obj_id} not found"
        )
    assert obj is not None
    return obj


def update(session: Session, obj_id, obj_content, db):
    obj = read(session, obj_id, db)  # raises if not found

    for key, value in obj_content.model_dump(exclude_unset=True).items():
        setattr(obj, key, value)

    return create(session, obj)


def delete(session: Session, obj_id, db) -> bool:
    obj = read(session, obj_id, db)

    try:
        session.delete(obj)
        session.commit()
    except Exception as e:
        session.rollback()
        raise HTTPException(500, detail=str(e))

    return True
