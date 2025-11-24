import uuid
from typing import Optional

from fastapi import Depends
from sqlmodel import Session

from src.models import ActivityLog, get_session


def log(
    action: str,
    message: str,
    user_id: Optional[uuid.UUID] = None,
    details: str = "",
    code: int = 200,
    session: Session = Depends(get_session),
    project_id: Optional[uuid.UUID] = None,
):
    statuslog: ActivityLog = ActivityLog(
        user_id=user_id,
        project_id=project_id,
        action_type=action,
        action_desc=message[:255],
        status_code=code,
        details=details,
    )
    try:
        session.add(statuslog)
        session.commit()
        session.refresh(statuslog)
    except Exception as e:
        print(f"CRITICAL LOGGING ERROR {e}")
        session.rollback()


def prep_create(data, *pkeys):
    validated_data = data.model_dump(exclude_unset=True)
    for pkey in pkeys:
        if pkey in validated_data and validated_data[pkey] is None:
            del validated_data[pkey]
    return validated_data
