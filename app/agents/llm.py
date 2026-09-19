from langchain_deepseek import ChatDeepSeek

from app.config import settings


def get_llm() -> ChatDeepSeek:
    return ChatDeepSeek(
        model="deepseek-v4-flash",
        api_key=settings.DEEPSEEK_API_KEY,
        temperature=0,
        max_tokens=4096,
    )


def get_llm_structured() -> ChatDeepSeek:
    """LLM configured for structured output (no thinking mode)."""
    return ChatDeepSeek(
        model="deepseek-v4-flash",
        api_key=settings.DEEPSEEK_API_KEY,
        temperature=0,
        max_tokens=4096,
        extra_body={"thinking": {"type": "disabled"}},
    )
