from typing import Any

from fastapi import Request
from pydantic import BaseModel, ConfigDict


class ApiSuccess(BaseModel):
    success: bool = True
    data: dict[str, Any]
    request_id: str


class ApiError(BaseModel):
    success: bool = False
    error_code: str
    message: str
    request_id: str


class ApiException(Exception):
    def __init__(self, error_code: str, message: str, status_code: int = 400) -> None:
        self.error_code = error_code
        self.message = message
        self.status_code = status_code


class ErrorCode(str):
    AUTH_REQUIRED = "AUTH_REQUIRED"
    ACCESS_DENIED = "ACCESS_DENIED"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    DUPLICATE_RECORD = "DUPLICATE_RECORD"
    TASK_CLOSED = "TASK_CLOSED"
    SUBMISSION_LOCKED = "SUBMISSION_LOCKED"
    AI_MARKING_FAILED = "AI_MARKING_FAILED"
    EXPORT_FAILED = "EXPORT_FAILED"
    SUPPORT_TICKET_NOT_FOUND = "SUPPORT_TICKET_NOT_FOUND"
    HEALTH_CHECK_FAILED = "HEALTH_CHECK_FAILED"


class HealthPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    service: str
    status: str
    environment: str
    checks: dict[str, str] = {}


def request_id_from(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def success_response(request: Request, data: dict[str, Any]) -> dict[str, Any]:
    return {"success": True, "data": data, "request_id": request_id_from(request)}


def error_response(request: Request, error_code: str, message: str) -> dict[str, Any]:
    return {
        "success": False,
        "error_code": error_code,
        "message": message,
        "request_id": request_id_from(request),
    }
