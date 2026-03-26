"""Chatbot routes — /chat and /chat/stream endpoints."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.schemas import AIRequest, ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_orchestrator(request: Request):
    return request.app.state.orchestrator


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request):
    session_store = request.app.state.session_store
    orchestrator = _get_orchestrator(request)

    context = body.context
    if context == "auto":
        context = orchestrator.detect_context(body.message)

    history = session_store.get_history(body.session_id) if body.session_id else []

    ai_request = AIRequest(
        query=body.message,
        context=context,
        feature="chat",
        options={"history": history, "session_id": body.session_id},
    )
    response = await orchestrator.handle(ai_request)

    if body.session_id and response.data.get("supported", False):
        session_store.add_turn(
            body.session_id,
            body.message,
            response.data.get("answer", ""),
        )

    return ChatResponse(success=response.success, data=response.data, meta=response.meta)


@router.post("/chat/stream")
async def chat_stream(body: ChatRequest, request: Request):
    """SSE endpoint — streams chat tokens as Server-Sent Events."""
    session_store = request.app.state.session_store
    orchestrator = _get_orchestrator(request)

    context = body.context
    if context == "auto":
        context = orchestrator.detect_context(body.message)

    history = session_store.get_history(body.session_id) if body.session_id else []

    ai_request = AIRequest(
        query=body.message,
        context=context,
        feature="chat",
        options={"history": history, "session_id": body.session_id},
    )

    orchestrator.check_request(ai_request)

    async def event_generator():
        full_answer: list[str] = []
        supported = True
        try:
            async for token in orchestrator.handle_stream(ai_request):
                full_answer.append(token)
                yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception:
            logger.exception("Streaming error")
            supported = False
            yield f"data: {json.dumps({'error': 'An error occurred during generation.'})}\n\n"

        answer_text = "".join(full_answer)

        if answer_text.startswith("I don't have enough information"):
            supported = False

        if body.session_id and supported:
            session_store.add_turn(body.session_id, body.message, answer_text)

        yield f"data: {json.dumps({'done': True, 'supported': supported, 'context': context})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
