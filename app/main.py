from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routes.chat import router as chat_router
from app.routes.health import router as health_router
from app.services.rag_service import rag_service
from app.utils.errors import register_exception_handlers
from app.utils.logging import configure_logging


settings = get_settings()
configure_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await rag_service.initialize()
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health_router)
app.include_router(chat_router, prefix="/api")
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
