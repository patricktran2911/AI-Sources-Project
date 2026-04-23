"""Feedback route — collect user ratings on AI responses."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from app.core.dependencies import DbPoolDep
from app.core.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter(prefix="/feedback")
logger = logging.getLogger(__name__)

_INSERT_FEEDBACK = """
INSERT INTO feedback (session_id, query, answer, rating, comment, context, feature)
VALUES ($1, $2, $3, $4, $5, $6, $7)
"""


@router.post("", response_model=FeedbackResponse)
async def submit_feedback(body: FeedbackRequest, pool: DbPoolDep):
    """Record user feedback (thumbs_up / thumbs_down) for a response."""
    async with pool.acquire() as conn:
        await conn.execute(
            _INSERT_FEEDBACK,
            body.session_id,
            body.query,
            body.answer,
            body.rating,
            body.comment,
            body.context,
            body.feature,
        )
    logger.info("Feedback recorded: %s (session=%s)", body.rating, body.session_id)
    return FeedbackResponse()
