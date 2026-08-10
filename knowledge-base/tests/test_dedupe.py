from kb.dedupe import redundant_ids, similarity


def test_identical_text_is_fully_similar():
    a = "Make money while watching YouTube, earn 500P per day, contact the tutor"
    assert similarity(a, a) == 1.0


def test_unrelated_messages_are_dissimilar():
    a = "Make money while watching YouTube, earn 500P per day, contact the tutor"
    b = "BDO ALERT: your account has been restricted due to unrecognized attempts"
    assert similarity(a, b) < 0.2


def test_distinct_messages_are_all_kept():
    items = [
        ("m1", "Make money while watching YouTube, earn 500P per day, contact the tutor"),
        ("m2", "BDO ALERT: your account has been restricted due to unrecognized attempts"),
        ("m3", "Nakatanggap ang iyong number ng P7748. Mag-register gamit ang number na ito"),
    ]
    assert redundant_ids(items) == set()


def test_near_duplicate_pair_keeps_one():
    items = [
        ("m1", "Make money while watching YouTube, earn 500P per day, contact the tutor now"),
        ("m2", "Make money while watching YouTube, earn 500P per day, contact the tutor now!"),
    ]
    assert len(redundant_ids(items)) == 1


def test_longest_variant_is_the_representative():
    # The fullest text carries the most retrievable detail, so it survives
    # regardless of the order rows arrive in.
    short = "Kumita habang nanonood ng YouTube, kumita ng 500P bawat araw, tutor"
    long = short + " now"
    assert redundant_ids([("m1", short), ("m2", long)]) == {"m1"}
    assert redundant_ids([("m1", long), ("m2", short)]) == {"m2"}


def test_substantially_longer_superset_is_kept():
    # Jaccard punishes length difference, and that is the behaviour we want:
    # a message carrying much more text is more evidence, not a duplicate.
    short = "Kumita habang nanonood ng YouTube, kumita ng 500P bawat araw"
    long = short + ", makipag-ugnayan sa tutor para matanggap ito ngayon"
    assert redundant_ids([("m1", short), ("m2", long)]) == set()


def test_equal_length_variants_break_ties_deterministically():
    a = "Binabati kita! Mag-log in para ma-claim ang lucky random reward mo"
    b = "Binabati kita! Mag-log in para ma-claim ang lucky random reward ko"
    assert redundant_ids([("m2", b), ("m1", a)]) == {"m2"}


def test_transitive_cluster_collapses_to_one():
    base = "100% na cashback para sa mga bagong dating, hanggang P19800! Magparehistro"
    items = [
        ("m1", base),
        ("m2", base + " at mag-claim"),
        ("m3", base + " at mag-claim na"),
    ]
    assert redundant_ids(items) == {"m1", "m2"}
