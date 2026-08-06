"""Settings from env. Every tunable is read here and nowhere else.

Names describe what they configure, not the app: LLM_* for the provider,
bare CONFIDENCE_THRESHOLD and KB_PATH for the graph and the corpus.
"""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_KB = BACKEND_ROOT / "tests" / "fixtures" / "kb_fixture.sqlite"
REAL_KB = BACKEND_ROOT.parent / "knowledge-base" / "out" / "kb.sqlite"
ENV_FILE = BACKEND_ROOT / ".env"


def default_kb_path() -> Path:
    """The real KB when built, else the fixture — per ARCHITECTURE § Retrieval."""
    return REAL_KB if REAL_KB.exists() else FIXTURE_KB

# Provider credentials share .env with the settings above, but the SDKs read
# them from os.environ, which pydantic-settings does not populate. Existing env
# vars win, so an exported key still overrides the file.
load_dotenv(ENV_FILE, override=False)


class Settings(BaseSettings):
    # protected_namespaces is cleared so the field can be called model_id;
    # pydantic otherwise reserves the model_ prefix for its own methods.
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )

    model_id: str = Field("google_genai:gemini-2.5-flash", alias="LLM_MODEL")
    max_tokens: int = Field(4096, alias="LLM_MAX_TOKENS")
    confidence_threshold: float = Field(0.70, alias="CONFIDENCE_THRESHOLD")
    retry_backoff: float = Field(20.0, alias="LLM_RETRY_BACKOFF")
    kb_path: Path = Field(default_factory=default_kb_path, alias="KB_PATH")


@lru_cache
def get_settings() -> Settings:
    return Settings()
