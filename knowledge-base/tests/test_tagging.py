from kb.tagging import (
    classify_scam_type,
    count_taglish_markers,
    detect_brand,
    has_url,
)


def test_detects_bank_impersonation():
    text = "BDO ALERT Your online access is suspended. To reactivate, register your device."
    assert classify_scam_type(text) == "bank-impersonation"


def test_detects_casino():
    text = "Magdeposito ng 100P, makakuha ng 117P na libre, 1X turnover 100k.cfd"
    assert classify_scam_type(text) == "casino"


def test_bank_impersonation_wins_over_casino_when_both_present():
    # "W19 Games, Official partner with GCash" is a casino ad naming a brand.
    # Brand mention alone must not make it bank impersonation.
    text = "W19 Games, Official partner with GCash, magdeposito para makakuha ng cashback!"
    assert classify_scam_type(text) == "casino"


def test_unmatched_returns_none():
    assert classify_scam_type("Kumusta ka na? Tara kain tayo bukas.") is None


def test_detect_brand_is_case_insensitive():
    assert detect_brand("Gcash. Account verification needed") == "gcash"
    assert detect_brand("[ BANCO DE ORO ] Your account") == "bdo"
    assert detect_brand("UNIONBANK FINAL WARNING") == "unionbank"
    assert detect_brand("#PAYMAYA Your voucher is expiring") == "maya"
    assert detect_brand("Kumusta ka na?") is None


def test_has_url_detects_bare_domains_and_schemes():
    assert has_url("Verify here: https://mybdo-fake.com") is True
    assert has_url("Visit centi.ai/GCashCarePH now") is True
    assert has_url("join us at 100k.cfd") is True
    assert has_url("Call us at 1326 for help") is False


def test_count_taglish_markers():
    assert count_taglish_markers("Magdeposito ka na ngayon para sa iyong bonus") >= 3
    assert count_taglish_markers("Your account has been suspended") == 0
