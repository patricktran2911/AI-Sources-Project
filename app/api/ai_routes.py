"""AI feature routes — thin handlers that delegate to the orchestrator."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.schemas import AIRequest, AIResponse, ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_orchestrator(request: Request):
    return request.app.state.orchestrator


@router.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest, request: Request):
    session_store = request.app.state.session_store
    orchestrator = _get_orchestrator(request)

    # Resolve auto-context before building the request
    context = body.context
    if context == "auto":
        context = orchestrator.detect_context(body.message)

    # Load history for this session
    history = session_store.get_history(body.session_id) if body.session_id else []

    ai_request = AIRequest(
        query=body.message,
        context=context,
        feature="chat",
        options={"history": history, "session_id": body.session_id},
    )
    response = await orchestrator.handle(ai_request)

    # Persist turn only when the answer was supported
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

    # Resolve auto-context eagerly so check_request and the done event both see it
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

    # Validate context/feature eagerly so we can return 404 before streaming starts.
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

        # Check if the answer was an unsupported-gate response
        if answer_text.startswith("I don't have enough information"):
            supported = False

        # Persist turn when supported
        if body.session_id and supported:
            session_store.add_turn(body.session_id, body.message, answer_text)

        yield f"data: {json.dumps({'done': True, 'supported': supported, 'context': context})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/summarize", response_model=AIResponse)
async def summarize(body: AIRequest, request: Request):
    body.feature = "summarize"
    return await _get_orchestrator(request).handle(body)


@router.post("/suggest", response_model=AIResponse)
async def suggest(body: AIRequest, request: Request):
    body.feature = "suggest"
    return await _get_orchestrator(request).handle(body)


@router.get("/contexts")
async def list_contexts(request: Request):
    registry = request.app.state.context_registry
    return {"contexts": registry.list_names()}


@router.get("/features")
async def list_features(request: Request):
    registry = request.app.state.feature_registry
    return {"features": registry.list_names()}
