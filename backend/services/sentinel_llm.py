from huggingface_hub import InferenceClient

from utils.config import get_settings

# Headers for the frontend to display if the LLM fails and it falls back to local data
GENERIC_HUGGINGFACE_SNAPSHOT_HEADER = "Snapshot Mode (Hugging Face Unreachable)\n\n"
RATE_LIMIT_SNAPSHOT_HEADER = "Snapshot Mode (Rate Limited)\n\n"

def is_quota_or_rate_limit(exc: BaseException) -> bool:
    """Helper to detect rate limit errors so the router can failover cleanly."""
    msg = str(exc).lower()
    return "429" in msg or "rate" in msg or "quota" in msg or "limit" in msg or "too many" in msg

def stream_sentinel_reply(context_data: dict, user_message: str):
    """
    Streams a response from Hugging Face Inference API.
    Yields text chunks as they are generated.
    """
    settings = get_settings()
    if not settings.huggingface_llm_enabled or not settings.huggingface_api_key.strip():
        raise RuntimeError("Hugging Face is not configured. Set HUGGINGFACE_API_KEY in backend/.env.")

    system_prompt = """You are Sentinel AI, the cybersecurity assistant for Defendra.
Use the following live system context to answer the user's query.
Keep your answers concise, technical, and directly actionable.
If you don't have enough information in the context, say so clearly."""

    context_str = str(context_data) if context_data else "No system data available."
    
    messages = [
        {
            "role": "system",
            "content": f"{system_prompt}\n\nSYSTEM CONTEXT (Live Firestore Snapshot):\n{context_str}"
        },
        {
            "role": "user", 
            "content": user_message
        }
    ]
    
    # Create the client lazily so environment changes take effect after a restart.
    client = InferenceClient(
        token=settings.huggingface_api_key.strip(),
        provider=settings.huggingface_provider,
    )
    stream = client.chat.completions.create(
        model=settings.huggingface_model,
        messages=messages,
        max_tokens=1024,
        temperature=0.2,
        stream=True
    )
    
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
