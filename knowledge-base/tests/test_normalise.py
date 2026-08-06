from kb.normalise import normalise_text, is_held_out, holdout_index


def test_normalise_collapses_whitespace_and_lowercases():
    assert normalise_text("  BDO   ALERT\n\nYour  account ") == "bdo alert your account"


def test_normalise_strips_surrounding_punctuation():
    assert normalise_text("Verify here!!!") == "verify here"
    assert normalise_text("...Verify here") == "verify here"


def test_normalise_is_idempotent():
    once = normalise_text("  Hello   World!  ")
    assert normalise_text(once) == once


def test_exact_match_is_held_out():
    evals = holdout_index(["BDO ALERT Your account is on hold"])
    assert is_held_out("bdo alert your account is on hold", evals) is True


def test_prefix_match_is_held_out():
    # The eval CSV truncates at 400 chars; the dataset row is longer.
    truncated = "Get up to P2K Cashback with min. required spend at SM Appliance"
    full = truncated + " Center with your BDO Credit Card! T&Cs apply. DTI217131"
    evals = holdout_index([truncated])
    assert is_held_out(full, evals) is True


def test_suffix_match_is_not_held_out():
    evals = holdout_index(["Center with your BDO Credit Card"])
    assert is_held_out("Get up to P2K Center with your BDO Credit Card", evals) is False


def test_unrelated_message_is_not_held_out():
    evals = holdout_index(["BDO ALERT Your account is on hold"])
    assert is_held_out("Nice! You received a P20 voucher from Maya.", evals) is False


def test_empty_eval_text_never_matches():
    # A blank eval row must not hold out the entire corpus by prefix.
    evals = holdout_index(["", "   "])
    assert is_held_out("any message at all", evals) is False
