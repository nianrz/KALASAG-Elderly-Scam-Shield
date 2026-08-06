"""The provider switch. The only module that imports a provider SDK.

No sampling parameters are ever passed. Providers disagree about which they
accept and some reject them outright, so a temperature that works under one
LLM_MODEL and 400s under another defeats the point of the switch.
"""

import time
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable

from app.config import get_settings

MAX_ATTEMPTS = 4

# Each provider raises its own exception type for a 429, so match on the
# wire status and the wording rather than on a type we would have to import.
_RATE_LIMIT_MARKERS = (
    "429",
    "resource_exhausted",
    "resourceexhausted",
    "rate limit",
    "ratelimit",
    "too many requests",
    "throttl",
)


def get_model() -> BaseChatModel:
    settings = get_settings()
    return init_chat_model(settings.model_id, max_tokens=settings.max_tokens)


def is_rate_limit(exc: BaseException) -> bool:
    for attr in ("status_code", "code", "http_status"):
        if getattr(exc, attr, None) == 429:
            return True
    text = str(exc).lower()
    return any(marker in text for marker in _RATE_LIMIT_MARKERS)


def invoke_with_retry(runnable: Runnable, payload: Any) -> Any:
    """Every LLM call goes through here.

    Free tiers rate-limit at roughly 10-15 requests per minute and an eval run
    is ~200 calls, so retry lives in one place and no caller writes its own.
    Build the chain first (including with_structured_output), wrap last.
    """
    backoff = get_settings().retry_backoff
    for attempt in range(MAX_ATTEMPTS):
        try:
            return runnable.invoke(payload)
        except Exception as exc:
            if attempt == MAX_ATTEMPTS - 1 or not is_rate_limit(exc):
                raise
            time.sleep(backoff * (attempt + 1))
