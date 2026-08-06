"""Settings from env. Every SHIELD_* knob is read here and nowhere else."""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_KB = BACKEND_ROOT / "tests" / "fixtures" / "kb_fixture.sqlite"
ENV_FILE = BACKEND_ROOT / ".env"

# Provider credentials share .env with the SHIELD_* settings, but the SDKs read
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

    model_id: str = Field("google_genai:gemini-2.5-flash", alias="SHIELD_MODEL")
    max_tokens: int = Field(4096, alias="SHIELD_MAX_TOKENS")
    confidence_threshold: float = Field(0.70, alias="SHIELD_CONFIDENCE_THRESHOLD")
    retry_backoff: float = Field(20.0, alias="SHIELD_RETRY_BACKOFF")
    kb_path: Path = Field(FIXTURE_KB, alias="SHIELD_KB_PATH")


@lru_cache
def get_settings() -> Settings:
    return Settings()
