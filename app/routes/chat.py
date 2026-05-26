from fastapi import APIRouter, Depends

from app.models.schemas import ChatRequest, ChatResponse
from app.services.rag_service import rag_service
from app.utils.auth import require_auth


router = APIRouter(dependencies=[Depends(require_auth)])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    return await rag_service.answer(request.sessionId, request.message)
