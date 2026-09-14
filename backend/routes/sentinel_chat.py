import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from google.cloud.firestore import Client

from auth.dependencies import get_current_user
from database.firebase import get_firestore
from models.models import UserDoc
from models.schemas import SentinelChatRequest
from services.sentinel_context import build_sentinel_context
from services.sentinel_llm import (
    GENERIC_HUGGINGFACE_SNAPSHOT_HEADER,
    RATE_LIMIT_SNAPSHOT_HEADER,
    is_quota_or_rate_limit,
    stream_sentinel_reply,
)
from services.sentinel_offline import stream_offline_sentinel

router = APIRouter(prefix="/sentinel", tags=["Sentinel AI"])

def _sse_data(payload: dict) -> str:
    """Formats a dictionary into a Server-Sent Event string."""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

@router.post("/chat/stream")
def sentinel_chat_stream(
    payload: SentinelChatRequest,
    current_user: UserDoc = Depends(get_current_user),
    db: Client = Depends(get_firestore),
):
    # Fetch live data snapshot to feed to the LLM
    context = build_sentinel_context(db, current_user)

    def event_stream():
        def emit_snapshot(header: str):
            """Fallback mechanism if the LLM is unavailable."""
            for piece in stream_offline_sentinel(
                context,
                payload.message,
                replace_header=header,
            ):
                yield _sse_data({"t": piece})

        try:
            # Consume the generator from our updated sentinel_llm.py
            for chunk in stream_sentinel_reply(context, payload.message):
                yield _sse_data({"t": chunk})
                
        except BaseException as exc:
            # Handle client disconnects gracefully
            if isinstance(exc, (KeyboardInterrupt, SystemExit, GeneratorExit)):
                raise
                
            # If Hugging Face is unavailable, fall back to the local snapshot.
            hdr = RATE_LIMIT_SNAPSHOT_HEADER if is_quota_or_rate_limit(exc) else GENERIC_HUGGINGFACE_SNAPSHOT_HEADER
            yield from emit_snapshot(hdr)

    # Return the stream to the Vite frontend
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no", # Prevents Nginx/Proxies from buffering the stream
        },
    )
