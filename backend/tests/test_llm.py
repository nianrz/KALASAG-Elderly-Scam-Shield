import pytest

from app import llm


class Boom(Exception):
    def __init__(self, message="boom", status_code=None):
        super().__init__(message)
        self.status_code = status_code


class FlakyRunnable:
    """Raises `failures` times, then returns."""

    def __init__(self, exc, failures):
        self.exc = exc
        self.failures = failures
        self.calls = 0

    def invoke(self, payload):
        self.calls += 1
        if self.calls <= self.failures:
            raise self.exc
        return f"ok:{payload}"


@pytest.fixture
def no_sleep(monkeypatch):
    slept = []
    monkeypatch.setattr(llm.time, "sleep", slept.append)
    return slept


@pytest.fixture
def fast_backoff(monkeypatch):
    monkeypatch.setenv("SHIELD_RETRY_BACKOFF", "2")
    llm.get_settings.cache_clear()
    yield
    llm.get_settings.cache_clear()


def test_get_model_passes_max_tokens_and_no_sampling_params(monkeypatch):
    captured = {}

    def fake_init(model_id, **kwargs):
        captured["model_id"] = model_id
        captured["kwargs"] = kwargs
        return "model"

    monkeypatch.setenv("SHIELD_MODEL", "google_genai:gemini-2.5-pro")
    monkeypatch.setenv("SHIELD_MAX_TOKENS", "1234")
    llm.get_settings.cache_clear()
    monkeypatch.setattr(llm, "init_chat_model", fake_init)

    try:
        assert llm.get_model() == "model"
    finally:
        llm.get_settings.cache_clear()

    assert captured["model_id"] == "google_genai:gemini-2.5-pro"
    assert captured["kwargs"] == {"max_tokens": 1234}


@pytest.mark.parametrize(
    "exc",
    [
        Boom("service unavailable", status_code=429),
        Boom("429 RESOURCE_EXHAUSTED: quota for requests per minute"),
        Boom("Rate limit reached for this model"),
        Boom("ThrottlingException: too many requests"),
    ],
)
def test_is_rate_limit_recognises_provider_variants(exc):
    assert llm.is_rate_limit(exc)


@pytest.mark.parametrize(
    "exc",
    [Boom("invalid api key", status_code=401), ValueError("malformed prompt")],
)
def test_is_rate_limit_ignores_other_failures(exc):
    assert not llm.is_rate_limit(exc)


def test_retries_a_rate_limited_call_until_it_succeeds(no_sleep, fast_backoff):
    runnable = FlakyRunnable(Boom(status_code=429), failures=2)

    assert llm.invoke_with_retry(runnable, "hi") == "ok:hi"
    assert runnable.calls == 3
    assert no_sleep == [2.0, 4.0]


def test_does_not_retry_a_non_429(no_sleep, fast_backoff):
    runnable = FlakyRunnable(Boom("invalid api key", status_code=401), failures=99)

    with pytest.raises(Boom):
        llm.invoke_with_retry(runnable, "hi")

    assert runnable.calls == 1
    assert no_sleep == []


def test_gives_up_after_max_attempts(no_sleep, fast_backoff):
    runnable = FlakyRunnable(Boom(status_code=429), failures=99)

    with pytest.raises(Boom):
        llm.invoke_with_retry(runnable, "hi")

    assert runnable.calls == llm.MAX_ATTEMPTS
    assert len(no_sleep) == llm.MAX_ATTEMPTS - 1
