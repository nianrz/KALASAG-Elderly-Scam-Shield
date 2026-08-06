import pytest

from app.retrieval.contacts import rebuttal_for_brand, top_contacts
from app.retrieval.embedder import DIMENSION, embed_passages, embed_queries
from app.retrieval.store import ChunkStore


@pytest.fixture(scope="module")
def store(kb_path):
    return ChunkStore(kb_path)


class TestEmbedder:
    def test_dimension(self):
        vectors = embed_queries(["throwaway"])
        assert vectors.shape == (1, DIMENSION)

    def test_passages_normalized(self):
        vector = embed_passages(["a passage"])[0]
        assert abs(float(vector @ vector) - 1.0) < 1e-5


class TestChunkStore:
    def test_embeddings_populated_on_first_load(self, store):
        assert store.chunk_count > 0

    def test_taglish_query_retrieves_english_lure(self, store):
        results = store.search(
            ["Naka-hold daw ang account ko, kailangan i-verify sa link bago bukas"]
        )
        chunk_ids = [c.chunk_id for c in results]
        assert any(
            cid.startswith(("lure-", "advisory-")) for cid in chunk_ids
        ), chunk_ids

    def test_no_legit_row_ever_returned(self, store):
        # Query worded to be nearest the LEGIT chunks in the fixture.
        results = store.search(
            ["BDO advisory never share your OTP visit bdo.com.ph for tips",
             "DTI reminder beware of text scams report to 1682"],
            top_k=store.chunk_count,
        )
        chunk_ids = {c.chunk_id for c in results}
        assert "example-fx-msg-101" not in chunk_ids
        assert "example-fx-msg-102" not in chunk_ids

    def test_concept_queries_surface_casino_pattern(self, store):
        results = store.search(
            ["free deposit bonus", "online casino promotion", "guaranteed winnings"]
        )
        assert any(c.chunk_id == "lure-casino-promo" for c in results)

    def test_top_k_respected(self, store):
        assert len(store.search(["scam"], top_k=3)) == 3

    def test_empty_query_returns_nothing(self, store):
        assert store.search([]) == []


class TestContacts:
    def test_keyed_lookup_returns_exact_hotline(self, kb_path):
        contacts = top_contacts(kb_path=kb_path)
        assert contacts[0].organisation == "Inter-Agency Response Center (I-ARC)"
        assert contacts[0].hotline == "1326"

    def test_priority_order(self, kb_path):
        contacts = top_contacts(n=2, kb_path=kb_path)
        assert [c.contact_id for c in contacts] == ["i-arc-1326", "pnp-acg"]

    def test_rebuttal_by_key(self, kb_path):
        rebuttal = rebuttal_for_brand("gcash", kb_path=kb_path)
        assert rebuttal is not None
        assert rebuttal.official_hotline == "2882"
        assert "NEVER" in rebuttal.rebuttal_quote

    def test_unknown_brand_is_none(self, kb_path):
        assert rebuttal_for_brand("metrobank", kb_path=kb_path) is None
