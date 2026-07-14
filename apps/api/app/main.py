from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.admin_ops import router as admin_ops_router
from app.api.account import router as account_router
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.marking import router as marking_router
from app.api.media import router as media_router
from app.api.reports import router as reports_router
from app.api.school_data import router as school_data_router
from app.api.student_ai import router as student_ai_router
from app.api.suggestions import router as suggestions_router
from app.api.tasks import router as tasks_router
from app.api.writing import router as writing_router
from app.core.config import get_settings
from app.core.responses import ApiException, ErrorCode, error_response
from app.middleware import request_id_middleware


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.project_name, version="0.0.0")

    app.middleware("http")(request_id_middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_router)
    app.include_router(account_router)
    app.include_router(auth_router)
    app.include_router(admin_ops_router)
    app.include_router(school_data_router)
    app.include_router(student_ai_router)
    app.include_router(tasks_router)
    app.include_router(writing_router)
    app.include_router(marking_router)
    app.include_router(media_router)
    app.include_router(suggestions_router)
    app.include_router(reports_router)

    @app.exception_handler(ApiException)
    async def api_exception_handler(request: Request, exc: ApiException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(request, exc.error_code, exc.message),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=error_response(
                request,
                ErrorCode.HEALTH_CHECK_FAILED,
                "Unexpected server error.",
            ),
        )

    return app


app = create_app()
