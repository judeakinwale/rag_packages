import logging
from fastapi import FastAPI, HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from rag_packages.shared.exception.exception import APIException
from rag_packages.contracts.dto.shared_dto import APIErrorResponse

logger = logging.getLogger(__name__)


def format_validation_error(error):
    str_loc = ".".join(map(str, error["loc"]))  # convert location tuple to string
    return {
        "loc": str_loc,
        "msg": error["msg"],
        "type": error["type"],
    }


def register_exception_handlers(app: FastAPI):

    @app.exception_handler(APIException)
    async def api_exception_handler(request, exc: APIException):
        error_content = APIErrorResponse(
            success=False,
            message=exc.message,
            error={
                "message": exc.message,
                "code": exc.code,
                "reason": exc.reason,
                "details": exc.details,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_content.model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc: RequestValidationError):

        structured_errors = [format_validation_error(err) for err in exc.errors()]
        error_content = APIErrorResponse(
            success=False,
            message="Validation error",
            error={
                "message": "Validation error",
                "code": "REQUEST_VALIDATION_ERROR",
                # "reason": "Invalid request data",
                "details": structured_errors,
            },
        )
        return JSONResponse(
            status_code=422,
            content=error_content.model_dump(),
        )

    # HTTPException inherits from StarletteHTTPException
    @app.exception_handler(HTTPException)
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request, exc: StarletteHTTPException):
        details_str = "HTTP Exception"
        if isinstance(exc.detail, str):
            details_str = exc.detail
        elif isinstance(exc.detail, dict):
            details_str = (
                exc.detail.get("message") or exc.detail.get("detail") or details_str
            )
        details = exc.detail if isinstance(exc.detail, (dict, list)) else None
        error_content = APIErrorResponse(
            success=False,
            message=details_str,
            error={
                "message": details_str,
                "code": "HTTP_ERROR",
                "details": details,
            },
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_content.model_dump(),
            headers=exc.headers,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request, exc: Exception):
        logger.exception("Unhandled exception")

        error_content = APIErrorResponse(
            success=False,
            message="An unexpected error occurred",
            error={
                "message": "An unexpected error occurred",
                "code": "INTERNAL_SERVER_ERROR",
                # "details": str(exc),
            },
        )
        return JSONResponse(
            status_code=500,
            content=error_content.model_dump(),
        )
