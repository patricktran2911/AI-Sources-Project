# Team Guide

## Local Development

```bash
docker compose up -d
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

## How To Add Or Change Behavior

### Adjust persona behavior

- Update `.env` with `PERSONA_NAME` and `PERSONA_ALIASES`.
- Tune context instructions in `app/contexts/context_registry.py`.
- Update seed data under `data/`.

### Add new grounded knowledge behavior

- Prefer changing contexts, retrieval thresholds, or prompt rules before adding new route types.
- If you need new ingestion labeling behavior, extend `app/contexts/knowledge_categorizer.py`.
- If you need new prompt compaction behavior, change `app/prompt/prompt_budget.py` or `app/prompt/prompt_builder.py`.

### Add a new internal capability

Use this order:

1. Write or update tests.
2. Add or change the local service module.
3. Wire it through the orchestrator if it affects request flow.
4. Update docs and QA instructions.

## Debugging Checklist

### Chat returns refusal too often

- Check `/api/v1/health`
- Inspect `RELEVANCE_THRESHOLD`
- Verify data exists in `knowledge_chunks`
- Confirm the query is being routed to the expected context

### Chat answers but feels expensive

- Inspect `meta.prompt_budget` in the chat response
- Lower `MAX_HISTORY_MESSAGES` or `MAX_EVIDENCE_CHUNKS`
- Lower `MAX_CONTEXT_TOKENS`
- Check whether unsupported queries are slipping through the relevance gate

### Streaming issues

- Verify `/api/v1/ai/chat/stream` emits a final `done` event
- Check logs for provider streaming exceptions
- Compare behavior with the non-streaming `/chat` endpoint

## Testing Commands

```bash
py -3.12 -m pytest tests -q
py -3.12 -m pytest tests/test_chat.py -q
py -3.12 -m pytest tests/test_features.py -q
```

## QA Checklist

- Supported profile question returns an answer and prompt budget metadata.
- Unsupported or malicious prompt is refused without a normal answer.
- Streaming chat finishes with a `done` event.
- Knowledge add/list/delete works for a user-scoped workflow.
- `/api/v1/ai/features` only lists `chat`.

## Definition Of Done

- Behavior works locally.
- Tests pass.
- Docs match the code.
- No new provider call was added unless it is essential.
