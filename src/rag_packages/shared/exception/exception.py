class APIException(Exception):
    def __init__(
        self,
        status_code: int,
        message: str,
        code: str | None = None,
        reason: str | None = None,
        details: dict | list[dict] | None = None,
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.code = code
        self.reason = reason
        self.details = details


class NotFoundException(APIException):
    def __init__(
        self,
        message: str = "Resource not found",
        details: dict | list[dict] | None = None,
    ) -> None:
        super().__init__(
            status_code=404,
            message=message,
            code="NOT FOUND",
            details=details,
        )


class ValidationException(APIException):
    def __init__(
        self,
        message: str = "Validation error",
        details: dict | list[dict] | None = None,
    ) -> None:
        super().__init__(
            status_code=422,
            message=message,
            code="VALIDATION ERROR",
            details=details,
        )


class BadRequestException(APIException):
    def __init__(
        self,
        message: str = "Bad request",
        details: dict | list[dict] | None = None,
    ) -> None:
        super().__init__(
            status_code=400,
            message=message,
            code="BAD REQUEST",
            details=details,
        )


class UnauthorizedException(APIException):
    def __init__(
        self,
        message: str = "Unauthorized",
        details: dict | list[dict] | None = None,
    ) -> None:
        super().__init__(
            status_code=401,
            message=message,
            code="UNAUTHORIZED",
            details=details,
        )
