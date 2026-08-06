"""Shared fixtures. Feature-specific fixtures belong in their own test module."""

from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_KB = BACKEND_ROOT / "tests" / "fixtures" / "kb_fixture.sqlite"


@pytest.fixture(scope="session")
def kb_path() -> Path:
    """The fixture knowledge base, built on demand."""
    if not FIXTURE_KB.exists():
        from tests.fixtures.make_fixture import build
        build()
    return FIXTURE_KB
