"""Multimodal chatbot routes for text and speech workflows."""

from __future__ import annotations

import base64
import json
import re
from collections.abc import AsyncIterator

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from app.api.speech_routes import MEDIA_TYPES
from app.core.config import get_settings
from app.core.dependencies import OrchestratorDep, SessionStoreDep, SpeechProviderDep, TranscriptionProviderDep
from app.core.schemas import AIRequest, ChatRequest, ChatSpeechRequest
from app.features.chatbot.routes import run_chat_request
from app.providers.speech_base import SpeechOptions

router = APIRouter()
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_COMPLETE_SENTENCE_RE = re.compile(r"(.+?[.!?])(?:\s+|$)", re.DOTALL)
_MIN_AUDIO_CHUNK_WORDS = 10
_MAX_AUDIO_CHUNK_SENTENCES = 2


def _speech_options(body: ChatSpeechRequest) -> SpeechOptions:
    settings = get_settings()
    speed = body.speed if body.speed is not None else settings.speech_default_speed
    instructions = body.instructions or settings.speech_default_instructions
    return SpeechOptions(
        response_format=body.response_format,
        voice=body.voice,
        instructions=instructions,
        speed=speed,
    )


async def _collect_speech_audio(
    text: str,
    body: ChatSpeechRequest,
    speech_provider,
) -> tuple[bytes, SpeechOptions]:
    options = _speech_options(body)
    chunks = [
        chunk
        async for chunk in speech_provider.synthesize_stream(text, options)
        if chunk
    ]
    return b"".join(chunks), options


def _audio_json(audio_bytes: bytes, response_format: str) -> dict[str, object]:
    return {
        "format": response_format,
        "mime_type": MEDIA_TYPES[response_format],
        "bytes": len(audio_bytes),
        "base64": base64.b64encode(audio_bytes).decode("ascii"),
    }


def _split_sentences_for_speech(text: str) -> list[str]:
    """Split answer text into sentence-sized speech jobs for faster first audio."""
    cleaned = " ".join(text.strip().split())
    if not cleaned:
        return []

    return [part.strip() for part in _SENTENCE_BOUNDARY.split(cleaned) if part.strip()] or [cleaned]


def _pop_complete_sentences(buffer: str) -> tuple[list[str], str]:
    """Return complete sentence-sized speech jobs and keep unfinished text."""
    sentences: list[str] = []
    consumed = 0
    for match in _COMPLETE_SENTENCE_RE.finditer(buffer):
        sentences.append(" ".join(match.group(1).split()))
        consumed = match.end()
    return sentences, buffer[consumed:]


def _should_hold_for_next_sentence(sentence: str) -> bool:
    """Avoid tiny one-sentence audio clips that sound choppy in the UI."""
    return len(sentence.strip().split()) < _MIN_AUDIO_CHUNK_WORDS


def _ndjson_event(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")


async def _answer_with_audio(
    body: ChatSpeechRequest,
    orchestrator,
    session_store,
    speech_provider,
    transcript: str | None = None,
) -> dict[str, object]:
    chat_body = ChatRequest(
        message=body.message,
        context=body.context,
        session_id=body.session_id,
        user_id=body.user_id,
    )
    chat_response = await run_chat_request(chat_body, orchestrator, session_store)
    answer = chat_response.data.get("answer", "")
    audio_bytes, options = await _collect_speech_audio(answer, body, speech_provider) if answer else (b"", _speech_options(body))

    data = dict(chat_response.data)
    data["audio"] = _audio_json(audio_bytes, body.response_format)
    if transcript is not None:
        data["transcript"] = transcript

    meta = dict(chat_response.meta)
    meta["speech"] = {
        "provider": get_settings().speech_provider,
        "format": body.response_format,
        "voice": options.voice,
        "speed": options.speed,
        "instructions": options.instructions,
    }

    return {
        "success": chat_response.success,
        "data": data,
        "meta": meta,
    }


@router.post("/text-to-speech")
async def text_to_speech(
    body: ChatSpeechRequest,
    orchestrator: OrchestratorDep,
    session_store: SessionStoreDep,
    speech_provider: SpeechProviderDep,
):
    """Generate chatbot text and synthesized speech in one JSON response."""
    return await _answer_with_audio(body, orchestrator, session_store, speech_provider)


@router.post("/text-to-speech/stream")
async def text_to_speech_stream(
    body: ChatSpeechRequest,
    orchestrator: OrchestratorDep,
    session_store: SessionStoreDep,
    speech_provider: SpeechProviderDep,
):
    """Stream chatbot text and sentence-level speech audio as NDJSON."""

    async def stream_events() -> AsyncIterator[bytes]:
        context = body.context
        if context == "auto":
            context = await orchestrator.detect_context(body.message)

        history = await session_store.get_history_async(body.session_id) if body.session_id else []
        ai_request = AIRequest(
            query=body.message,
            context=context,
            feature="chat",
            options={"history": history, "session_id": body.session_id, "user_id": body.user_id},
        )
        orchestrator.check_request(ai_request)

        options = _speech_options(body)
        speech_meta = {
            "provider": get_settings().speech_provider,
            "format": body.response_format,
            "voice": options.voice,
            "speed": options.speed,
            "instructions": options.instructions,
            "streaming": "live_sentence",
            "audio_chunking": {
                "strategy": "single_sentence_or_pair_short_sentence",
                "min_single_sentence_words": _MIN_AUDIO_CHUNK_WORDS,
                "max_sentences_per_audio": _MAX_AUDIO_CHUNK_SENTENCES,
            },
        }

        yield _ndjson_event(
            {
                "type": "meta",
                "success": True,
                "context": context,
                "speech": speech_meta,
            }
        )

        full_answer: list[str] = []
        sentence_buffer = ""
        pending_audio_sentences: list[str] = []
        sentence_index = 0
        supported = True
        stream_meta: dict[str, object] = {}

        async def emit_audio_chunk(sentences: list[str], index: int) -> AsyncIterator[bytes]:
            chunk_text = " ".join(sentence.strip() for sentence in sentences if sentence.strip())
            if not chunk_text:
                return
            yield _ndjson_event(
                {
                    "type": "sentence",
                    "index": index,
                    "text": chunk_text,
                    "sentences": sentences,
                }
            )
            audio_bytes, _ = await _collect_speech_audio(chunk_text, body, speech_provider)
            yield _ndjson_event(
                {
                    "type": "audio",
                    "index": index,
                    "text": chunk_text,
                    "sentences": sentences,
                    "audio": _audio_json(audio_bytes, body.response_format),
                }
            )

        async def queue_sentence_for_audio(sentence: str) -> AsyncIterator[bytes]:
            nonlocal sentence_index, pending_audio_sentences

            cleaned = " ".join(sentence.strip().split())
            if not cleaned:
                return

            if pending_audio_sentences:
                pending_audio_sentences.append(cleaned)
                async for event in emit_audio_chunk(pending_audio_sentences, sentence_index):
                    yield event
                sentence_index += 1
                pending_audio_sentences = []
                return

            if _should_hold_for_next_sentence(cleaned):
                pending_audio_sentences = [cleaned]
                return

            async for event in emit_audio_chunk([cleaned], sentence_index):
                yield event
            sentence_index += 1

        try:
            async for chunk in orchestrator.handle_stream(ai_request):
                text = str(chunk or "").strip()
                if not text:
                    continue
                full_answer.append(text)
                yield _ndjson_event({"type": "answer_delta", "text": text})

                sentence_buffer += text + " "
                sentences, sentence_buffer = _pop_complete_sentences(sentence_buffer)
                for sentence in sentences:
                    async for event in queue_sentence_for_audio(sentence):
                        yield event
        except Exception:
            yield _ndjson_event({"type": "error", "error": "An error occurred during generation."})
            return

        final_sentence = " ".join(sentence_buffer.split())
        if final_sentence:
            async for event in queue_sentence_for_audio(final_sentence):
                yield event

        if pending_audio_sentences:
            async for event in emit_audio_chunk(pending_audio_sentences, sentence_index):
                yield event
            sentence_index += 1

        stream_meta = dict(ai_request.options.get("_stream_meta", {}))
        prompt_budget = ai_request.options.get("_prompt_budget")
        supported = bool(stream_meta.get("supported", supported))
        answer_text = " ".join(part.strip() for part in full_answer if part.strip())

        if body.session_id and supported:
            await session_store.add_turn_async(body.session_id, body.message, answer_text)

        done_event: dict[str, object] = {
            "type": "done",
            "success": True,
            "supported": supported,
            "context": context,
            "answer": answer_text,
            "speech": speech_meta,
        }
        if prompt_budget:
            done_event["prompt_budget"] = prompt_budget
        for key in ("guarded", "guard_reason", "gated"):
            if key in stream_meta:
                done_event[key] = stream_meta[key]

        yield _ndjson_event(done_event)

    return StreamingResponse(
        stream_events(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"},
    )


@router.post("/speech-to-text")
async def speech_to_text(
    transcription_provider: TranscriptionProviderDep,
    audio: UploadFile = File(...),
):
    """Transcribe uploaded speech into text."""
    settings = get_settings()
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=422, detail="Audio upload cannot be empty.")
    if len(audio_bytes) > settings.max_speech_upload_bytes:
        raise HTTPException(status_code=413, detail="Audio upload exceeds the configured size limit.")

    transcript = await transcription_provider.transcribe(
        audio_bytes,
        audio.filename or "speech.webm",
        audio.content_type,
    )
    if not transcript:
        raise HTTPException(status_code=422, detail="No transcript was produced from the uploaded audio.")

    return {
        "success": True,
        "data": {"transcript": transcript},
        "meta": {
            "provider": settings.transcription_provider,
            "model": settings.openai_stt_model,
            "filename": audio.filename,
            "content_type": audio.content_type,
            "bytes": len(audio_bytes),
        },
    }


@router.post("/speech-to-speech")
async def speech_to_speech(
    orchestrator: OrchestratorDep,
    session_store: SessionStoreDep,
    speech_provider: SpeechProviderDep,
    transcription_provider: TranscriptionProviderDep,
    audio: UploadFile = File(...),
    context: str = Form("auto"),
    session_id: str | None = Form(None),
    user_id: str | None = Form(None),
    response_format: str = Form("mp3"),
    voice: str | None = Form(None),
    instructions: str | None = Form(None),
    speed: float | None = Form(None),
):
    """Transcribe speech, generate a chatbot answer, and return answer audio."""
    if response_format not in MEDIA_TYPES:
        raise HTTPException(status_code=422, detail=f"Unsupported response format: {response_format}")

    settings = get_settings()
    audio_bytes = await audio.read()
    if not audio_bytes:
        raise HTTPException(status_code=422, detail="Audio upload cannot be empty.")
    if len(audio_bytes) > settings.max_speech_upload_bytes:
        raise HTTPException(status_code=413, detail="Audio upload exceeds the configured size limit.")

    transcript = await transcription_provider.transcribe(
        audio_bytes,
        audio.filename or "speech.webm",
        audio.content_type,
    )
    if not transcript:
        raise HTTPException(status_code=422, detail="No transcript was produced from the uploaded audio.")

    body = ChatSpeechRequest(
        message=transcript,
        context=context,
        session_id=session_id,
        user_id=user_id,
        response_format=response_format,
        voice=voice,
        instructions=instructions,
        speed=speed,
    )
    response = await _answer_with_audio(
        body,
        orchestrator,
        session_store,
        speech_provider,
        transcript=transcript,
    )
    response["meta"]["transcription"] = {
        "provider": settings.transcription_provider,
        "model": settings.openai_stt_model,
        "filename": audio.filename,
        "content_type": audio.content_type,
        "bytes": len(audio_bytes),
    }
    return response
