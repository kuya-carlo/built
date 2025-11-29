import json

from fastapi import Request
from fastapi.exceptions import HTTPException, RequestValidationError
from sqlmodel import Session
from starlette.responses import JSONResponse

from src.models import ErrorDescription, ErrorResponse

from .common import log
from .db_create import engine


def error_response(errors, status: int = 500) -> JSONResponse:
    def get_errordesc(err: dict) -> ErrorDescription:
        return ErrorDescription(
            status=err.get("status", status),
            title=err.get("title", "Error"),
            detail=err.get("detail", "An error occurred"),
        )

    error = ErrorResponse(
        result="error",
        errors=[get_errordesc(err) for err in errors],
    )
    return JSONResponse(status_code=status, content=json.loads(error.model_dump_json()))


async def error_handler(request: Request, exc: Exception):
    user_id_from_request = getattr(request.state, "user_id", None)
    log_details = {}
    if isinstance(exc, RequestValidationError):
        status = 422
        title = "Validation Error"
        errors = []
        detail = "RequestValidationError: "
        for err in exc.errors():
            error_location = f"{'.'.join(str(loc) for loc in err['loc'])}"  # basically like (core, body) into core.body
            error_message = f"{error_location}: {err['msg']}"
            errors.append(
                {
                    "status": 422,
                    "title": title,
                    "detail": error_message,
                }
            )
            detail += f"[{error_message}] "

        final_response = error_response(errors, 422)
    elif isinstance(exc, HTTPException):
        status = exc.status_code
        title = "Error"
        detail = exc.detail
        final_response = error_response(
            [
                {
                    "status": status,
                    "title": title,
                    "detail": detail,
                }
            ],
            status,
        )
    elif isinstance(exc, ValueError):
        status = 404
        title = "Error"
        detail = str(exc)
        final_response = error_response(
            [
                {
                    "status": status,
                    "title": title,
                    "detail": detail,
                }
            ],
            status,
        )
    else:
        status = 500
        title = "Internal Server Error"
        detail = "An unhandled critical error occurred."
        final_response = error_response(
            [{"status": status, "title": title, "detail": str(exc)}], 500
        )
        log_details = {
            "path": str(request.url),
            "method": request.method,
            "error_class": exc.__class__.__name__,
        }

    if status >= 400:  # if errored fr
        with Session(engine) as session:  # Manually create a session for logging
            log(
                session=session,
                action="API_CALL_FAIL",  # New generalized action type for failed API calls
                code=status,
                message=f"{title}: {detail}",
                user_id=user_id_from_request,
                details=str(log_details),
            )

    return final_response
