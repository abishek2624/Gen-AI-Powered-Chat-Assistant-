import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


logger = logging.getLogger(__name__)


def _validation_message(exc: RequestValidationError) -> str:
    for error in exc.errors():
        location = error.get("loc", [])
        message = error.get("msg", "Invalid request")
        if "message" in location:
            if "required" in message.lower() or "Message field is required" in message:
                return "Message field is required"
            return message
        if "sessionId" in location:
            return "SessionId field is required"
    return "Invalid request payload"


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(status_code=422, content={"error": _validation_message(exc)})

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed"
        return JSONResponse(status_code=exc.status_code, content={"error": detail})

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled application error")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})
