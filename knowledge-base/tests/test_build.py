from kb.normalise import holdout_index
from scripts.build_kb import build_message_rows


def _row(text, category="spam"):
    return {"text": text, "category": category, "date-received": "2023-01-01"}


def _by_text(messages, text):
    return next(m for m in messages if m["text"] == text)


def test_near_duplicate_scam_rows_keep_one_retrievable():
    # A real template family: identical but for the deadline and the ref.
    base = ("[ BANCO DE ORO ] Your account has been restricted due to unrecognized "
            "attempts. Failure to verify within {} hours will suspend it. Ref {}")
    rows = [_row(base.format(24, "8891")), _row(base.format(48, "8892")),
            _row(base.format(72, "8893"))]

    messages = build_message_rows(rows, [])

    assert len(messages) == 3
    assert sum(m["retrievable"] for m in messages) == 1


def test_deduplication_keeps_the_longest_variant():
    short = "Congrats! Mag-log in para ma-claim ang lucky reward mo ngayon"
    long = short + " po"
    messages = build_message_rows([_row(short), _row(long)], [])

    assert _by_text(messages, long)["retrievable"] == 1
    assert _by_text(messages, short)["retrievable"] == 0


def test_distinct_scam_rows_all_stay_retrievable():
    rows = [
        _row("[ BANCO DE ORO ] Your account has been restricted, verify your device now"),
        _row("Kumita habang nanonood ng YouTube, kumita ng 500P bawat araw, tutor"),
        _row("Nakatanggap ang iyong number ng P7748. Mag-register gamit ang number na ito"),
    ]
    messages = build_message_rows(rows, [])

    assert sum(m["retrievable"] for m in messages) == 3


def test_legit_rows_are_never_deduplicated_into_retrieval():
    base = "Your GCash payment of PHP 500 to Meralco is successful. Ref 1234567890"
    rows = [_row(base, category="notifs"), _row(base + "!", category="notifs")]

    messages = build_message_rows(rows, [])

    assert all(m["retrievable"] == 0 for m in messages)
    assert all(m["label"] == "LEGIT" for m in messages)


def test_deduplication_does_not_reinstate_a_held_out_message():
    # The surviving representative must still respect invariant 5.
    held = "W19 Games, sumali ka na at mag-claim ng cashback ngayon din dito"
    rows = [_row(held), _row(held + "!")]

    messages = build_message_rows(rows, holdout_index([held]))

    assert all(m["retrievable"] == 0 for m in messages)
    assert all(m["eval_holdout"] == 1 for m in messages)
