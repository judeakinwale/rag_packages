import logging
from time import perf_counter
from typing import Iterable

from starlette.middleware.base import BaseHTTPMiddleware

from .packages import BASE_LOGGER_NAME


# from uuid import uuid4
# from fastapi import Request

# logger = logging.getLogger("request")


# async def log_requests(request: Request, call_next):
#     request_id = str(
#         uuid4()
#     )  # TODO: update this as request id is already generated in the RequestIdMiddleware and can be accessed via request.state.request_id
#     start_time = time.time()

#     response = await call_next(request)

#     process_time = (time.time() - start_time) * 1000

#     logger.info(
#         f"request_id={request_id} "
#         f"method={request.method} "
#         f"path={request.url.path} "
#         f"status={response.status_code} "
#         f"latency_ms={process_time:.2f}"
#     )

#     response.headers["X-Request-ID"] = request_id
#     return response


class LoggingMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        logger_name: str = BASE_LOGGER_NAME,
        request_id_header: str = "X-Request-ID",
        excluded_headers: Iterable[str] | None = None,
    ):
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)
        self.request_id_header = request_id_header
        self.excluded_headers = {
            header.lower()
            for header in (
                excluded_headers
                or {
                    "authorization",
                    "cookie",
                    "set-cookie",
                    "x-api-key",
                }
            )
        }

    async def dispatch(self, request, call_next):
        started_at = perf_counter()
        request_id = self._get_request_id(request)

        self.logger.info(
            "request_started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client": self._get_client(request),
                "headers": self._get_headers(request),
            },
        )

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            self.logger.exception(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
                    "client": self._get_client(request),
                    "duration_ms": duration_ms,
                },
            )
            raise

        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        response.headers.setdefault(self.request_id_header, request_id)

        self.logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client": self._get_client(request),
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response

    def _get_request_id(self, request) -> str:
        state_request_id = getattr(request.state, "request_id", None)
        if state_request_id:
            return str(state_request_id)

        header_request_id = request.headers.get(self.request_id_header)
        if header_request_id:
            return header_request_id

        return "unknown"

    def _get_client(self, request) -> str | None:
        client = request.client
        if client is None:
            return None
        return f"{client.host}:{client.port}"

    def _get_headers(self, request) -> dict[str, str]:
        return {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in self.excluded_headers
        }
