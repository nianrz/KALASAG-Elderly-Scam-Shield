"""Shared fixtures. Feature-specific fixtures belong in their own test module."""

from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_KB = BACKEND_ROOT / "tests" / "fixtures" / "kb_fixture.sqlite"


@pytest.fixture(scope="session")
def kb_path() -> Path:
    """The fixture knowledge base. Built by tests/fixtures/make_fixture.py."""
    if not FIXTURE_KB.exists():
        pytest.skip(f"{FIXTURE_KB.name} not built — run tests/fixtures/make_fixture.py")
    return FIXTURE_KB
