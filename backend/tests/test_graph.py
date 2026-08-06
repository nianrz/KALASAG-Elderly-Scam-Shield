import json

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from app.config import get_settings
from app.graph.build import build_graph, initial_state
from app.retrieval.store import ChunkStore

CONCEPTS = json.dumps(["claims account suspended", "urgency deadline"])


def detect_reply(verdict="SCAM", confidence=0.9, reason=None):
    return json.dumps({
        "verdict": verdict,
        "confidence": confidence,
        "red_flags": [
            {"label": "Claims your account is on hold",
             "detail": "Real suspensions appear in the app.",
             "chunk_id": "lure-account-suspended"}
        ],
        "low_confidence_reason": reason,
    })


ADVISE = json.dumps({
    "explanation": "Scam po ito.",
    "next_steps": ["Huwag i-click ang link.", "I-block ang sender."],
})


@pytest.fixture(scope="module")
def store(kb_path):
    return ChunkStore(kb_path)


@pytest.fixture(autouse=True)
def fixture_kb_settings(kb_path, monkeypatch):
    monkeypatch.setenv("KB_PATH", str(kb_path))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def run(responses, store, threshold=0.70):
    model = FakeListChatModel(responses=responses)
    graph = build_graph(model, store, threshold=threshold)
    state = initial_state(
        redacted_text="BDO alert: account on hold, click bit.ly/x within 24 hours",
        message_type="sms",
        redactions=[],
        output_language="tl",
    )
    return graph.invoke(state)


class TestGraphFlow:
    def test_high_confidence_goes_straight_to_advise(self, store):
        result = run([CONCEPTS, detect_reply(confidence=0.9), ADVISE], store)
        assert result["reflection_count"] == 0
        assert result["verdict"] == "SCAM"
        assert result["advice"].explanation == "Scam po ito."

    def test_low_confidence_reflects_exactly_once(self, store):
        result = run(
            [CONCEPTS,
             detect_reply("UNCLEAR", 0.4, "conflicting signals"),
             detect_reply("LIKELY_SCAM", 0.8),
             ADVISE],
            store,
        )
        assert result["reflection_count"] == 1
        assert result["verdict"] == "LIKELY_SCAM"

    def test_second_low_confidence_pass_still_terminates(self, store):
        result = run(
            [CONCEPTS,
             detect_reply("UNCLEAR", 0.4, "conflicting signals"),
             detect_reply("UNCLEAR", 0.45, "still conflicting"),
             ADVISE],
            store,
        )
        assert result["reflection_count"] == 1
        assert result["verdict"] == "UNCLEAR"
        assert result["advice"].next_steps

    def test_retrieval_populates_state(self, store):
        result = run([CONCEPTS, detect_reply(), ADVISE], store)
        assert result["concepts_en"] == ["claims account suspended", "urgency deadline"]
        assert len(result["retrieved"]) > 0

    def test_contacts_come_from_keyed_lookup(self, store):
        result = run([CONCEPTS, detect_reply(), ADVISE], store)
        orgs = [c.organisation for c in result["advice"].contacts]
        assert "Inter-Agency Response Center (I-ARC)" in orgs
        # "BDO" appears in the message, so the brand rebuttal is included
        # with its exact hotline from the KB.
        bdo = next(c for c in result["advice"].contacts if c.organisation == "BDO Unibank")
        assert bdo.hotline == "(02) 8888-0000"

    def test_fenced_json_is_tolerated(self, store):
        fenced = f"```json\n{detect_reply()}\n```"
        result = run([CONCEPTS, fenced, ADVISE], store)
        assert result["verdict"] == "SCAM"

    def test_unparseable_concepts_fall_back_to_text_search(self, store):
        result = run(["not json at all", detect_reply(), ADVISE], store)
        assert result["concepts_en"] == []
        assert len(result["retrieved"]) > 0
