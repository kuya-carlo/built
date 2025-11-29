import uuid
from enum import Enum
from typing import List, Optional, Type, TypeVar, Union

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, select

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


class FilterMode(Enum):
    FIRST = "first"
    LAST = "last"
    ALL = "all"


T = TypeVar("T", bound=SQLModel)


def db_filter(
    session: Session,
    db: Type[T],
    obj_id,
    field_comp,
    indexer,
    mode: FilterMode = FilterMode.FIRST,
    limit: int = 5,
    offset: int = 0,
) -> Union[List[T], Optional[T]]:
    errors = []

    if limit < 0:
        errors.append("Limit cannot be less than 0")
    if offset < 0:
        errors.append("Offset cannot be less than 0")

    if errors:
        raise ValueError(" | ".join(errors))

    if limit > 100:
        raise ValueError("Limit must not exceed by 100 per transaction")
    if limit == 0:
        return []

    query = select(db)
    if bool(obj_id) ^ bool(field_comp):
        raise ValueError("obj_id and field_comp must both be provided together.")

    if obj_id and field_comp:
        query = query.where(field_comp == obj_id)

    match mode:
        case FilterMode.ALL:
            final_query = query.limit(limit).offset(offset)
            return list(session.exec(final_query).all())

        case FilterMode.FIRST:
            return session.exec(query).first()

        case FilterMode.LAST:
            last_query = query.order_by(indexer.desc()).limit(1)
            return session.exec(last_query).first()

        case _:
            raise ValueError("Invalid filter mode")
