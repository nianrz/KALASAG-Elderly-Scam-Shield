"""One-off connectivity check for whatever LLM_MODEL is configured in .env.

Not a pytest test — it makes a real, billed call. Run directly:

    uv run python check_bedrock_connection.py
"""

import sys

from app.config import get_settings
from app.llm import get_model, invoke_with_retry


def main() -> int:
    settings = get_settings()
    print(f"LLM_MODEL = {settings.model_id}")

    try:
        model = get_model()
    except Exception as exc:
        print(f"\nFailed to build the model client: {exc}")
        return 1

    try:
        response = invoke_with_retry(
            model, [{"role": "user", "content": "Reply with exactly: pong"}]
        )
    except Exception as exc:
        print(f"\nCall failed: {exc}")
        _print_hint(exc)
        return 1

    print(f"\nResponse: {response.content}")
    usage = getattr(response, "usage_metadata", None)
    if usage:
        print(f"Usage: {usage}")
    return 0


def _print_hint(exc: Exception) -> None:
    text = str(exc).lower()
    if "please make sure your api key is valid" in text or "authentication failed" in text:
        print(
            "Hint: the bearer token itself was rejected (not a model-access "
            "issue). Re-check AWS_BEARER_TOKEN_BEDROCK for a copy-paste error "
            "(stray whitespace/quotes), expiry, or wrong sandbox account."
        )
    elif "accessdenied" in text or "not authorized" in text:
        print(
            "Hint: credentials are valid but the request was denied — check "
            "Bedrock console -> Model access for this model in this region."
        )
    elif "could not connect" in text or "endpoint" in text:
        print("Hint: check AWS_REGION matches where the model/profile is served.")
    elif "unrecognizedclientexception" in text or "invalid" in text and "token" in text:
        print(
            "Hint: check AWS_BEARER_TOKEN_BEDROCK is set (not AWS_BEARER_TOKEN) "
            "and hasn't expired."
        )


if __name__ == "__main__":
    sys.exit(main())
