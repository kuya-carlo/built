import uuid

from fastapi import APIRouter, Depends
from sqlmodel import Session

from src.models import (
    ActivityLog,
    ActivityLogResponse,
    ErrorResponse,
    SingleSuccessResponse,
)
from src.utils import get_session, log, prep_create, read

# Activity log should be read-only.


class ActivityLogRouter(APIRouter):
    def __init__(self):
        super().__init__(prefix="/activity_log", tags=["ActivityLog"])
        self._register_routes()

    def _register_routes(self):
        @self.get(
            "/{activity_log_id}",
            responses={
                200: {
                    "description": "ActivityLog exists",
                    "model": SingleSuccessResponse[ActivityLogResponse],
                },
                404: {"description": "ActivityLog not found", "model": ErrorResponse},
                500: {"description": "Server Error", "model": ErrorResponse},
            },
        )
        def get_activity_log(
            activity_log_id: uuid.UUID, session: Session = Depends(get_session)
        ):
            activity_log = read(session, activity_log_id, ActivityLog)
            log(
                "GET_ACTIVITYLOG",
                f"Got activity_log with id {activity_log_id}",
                session=session,
            )
            return self._parse_activity_log(activity_log)

    @staticmethod
    def _parse_activity_log(
        activity_log: ActivityLog,
    ) -> SingleSuccessResponse[ActivityLogResponse]:
        cleaned = prep_create(activity_log, "user_id", "project_id")
        return SingleSuccessResponse[ActivityLogResponse](
            data=ActivityLogResponse(**cleaned)
        )
