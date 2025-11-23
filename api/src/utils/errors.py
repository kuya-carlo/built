import json

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from src.models import ErrorDescription, ErrorResponse


def error_response(errors, status: int = 500) -> JSONResponse:
    errorpart = []
    for err in errors:
        errorpart.append(
            ErrorDescription(
                status=err["status"],
                title=err["title"],
                detail=err["detail"],
            )
        )
    error = ErrorResponse(
        result="error",
        errors=errorpart,
    )
    return JSONResponse(status_code=status, content=json.loads(error.model_dump_json()))


async def validation_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, RequestValidationError):
        errors = []
        for err in exc.errors():
            errors.append(
                {
                    "status": 422,
                    "title": "Validation Error",
                    "detail": f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}",
                }
            )
        return error_response(errors, 422)
    else:
        return error_response([{"title": "Validation error", "detail": str(exc)}], 422)
