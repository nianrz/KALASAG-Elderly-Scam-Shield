"""Build kb_fixture.sqlite against Nian's seven-table schema.

Stands in for knowledge-base/out/kb.sqlite until it lands. Seed content is
drawn from Nian's committed content/ files so the fixture speaks the same
vocabulary as the real KB. The embedding column ships NULL; the backend
populates it with the local model on first load.

Run: uv run python tests/fixtures/make_fixture.py
"""

import sqlite3
from pathlib import Path

FIXTURE_PATH = Path(__file__).resolve().parent / "kb_fixture.sqlite"

# The fixture executes Nian's committed DDL verbatim so its shape cannot
# drift from the real KB's.
SCHEMA_FILE = (
    Path(__file__).resolve().parents[3]
    / "knowledge-base" / "schema" / "001_schema.sqlite.sql"
)

SOURCES = [
    ("scottleechua-ph-sms", "PH Spam and Marketing SMS (with timestamps)", "Scott Lee Chua",
     "https://github.com/scottleechua/data/tree/main/spam-and-marketing-sms", "2026-08-06",
     "CC BY 4.0",
     'Chua, Scott Lee. "Spam and marketing SMS with timestamps." Licensed under CC BY 4.0.',
     "Fixture subset; examples paraphrase corpus templates and exclude eval-set text."),
    ("gcash-fraud-advisory", "How can I protect my GCash account?", "GCash",
     "https://help.gcash.com/hc/en-us/articles/19578518834457", "2026-08-06",
     "public advisory", "GCash Help Center.", None),
    ("bdo-fraud-advisory", "#BDOStopScam", "BDO Unibank",
     "https://www.bdo.com.ph/about-bdo/learn/stop-scam", "2026-08-06",
     "public advisory", "BDO Unibank #BDOStopScam.", None),
    ("cybersecurity-ph-reporting", "Cybercrime reporting — I-ARC 1326", "DICT / CICC / NPC / NTC",
     "https://www.cybersecurity.ph/cybercrime-reporting/", "2026-08-06",
     "public advisory", "cybersecurity.ph cybercrime reporting page.", None),
    ("pnp-acg-advisories", "PNP Anti-Cybercrime Group advisories", "Philippine National Police",
     "https://acg.pnp.gov.ph/", "2026-08-06",
     "public advisory", "PNP Anti-Cybercrime Group public advisories.", None),
]

BRAND_REBUTTALS = [
    ("gcash", "GCash",
     "GCash will NEVER send you links via SMS/email or ask for your MPIN/OTP.",
     "2882", "https://help.gcash.com/", "In-app help center; hotline 2882.",
     39, "gcash-fraud-advisory"),
    ("bdo", "BDO Unibank",
     "Don't click links! BDO messages will not contain links, and sender IDs can be spoofed.",
     "(02) 8888-0000", "https://www.bdo.com.ph/about-bdo/learn/stop-scam",
     "Official app and branches; hotline (02) 8888-0000.",
     24, "bdo-fraud-advisory"),
]

LURE_PATTERNS = [
    ("verify-update-account", "Verify or update your account",
     "Claims the recipient must verify or update their account details, usually via a link, or lose access. The most common bank-impersonation lure.",
     "bank-impersonation", 0.34, 44,
     "Asks you to verify an account by SMS link; no bank or e-wallet does this. Link domain is not the bank's official domain. Often a URL shortener.",
     "verify your account; account verification; update your account; verify here",
     "i-verify ang iyong account; kailangan i-update; magparehistro; pakiverify",
     "scottleechua-ph-sms"),
    ("account-suspended", "Account suspended or restricted",
     "States the account is already suspended, restricted, disabled, or on hold, creating alarm before the recipient can check.",
     "bank-impersonation", 0.24, 31,
     "Alarming status claim delivered by SMS rather than in the app. Real suspensions appear when you log in, not as a text with a link.",
     "temporarily disabled; account suspended; restricted; on hold; final warning",
     "naka-hold ang account; sinuspinde; hindi na magagamit; huling babala",
     "scottleechua-ph-sms"),
    ("urgency-deadline", "Urgency deadline",
     "Attaches a short deadline — 24 hours, tomorrow, immediately — so the recipient acts before verifying through an official channel.",
     "bank-impersonation", 0.17, 22,
     "A countdown is a pressure tactic. Any genuine issue will still be there after you call the official hotline.",
     "within 24 hours; expires today; immediately; act now",
     "ngayon din; bukas na; agad; bago mag-expire",
     "scottleechua-ph-sms"),
    ("click-this-link", "Click this link",
     "The payload is the link itself, very often a shortener that hides the destination domain.",
     "bank-impersonation", 0.17, 22,
     "Shortened links hide where they go. A link is a strong signal but its absence proves nothing.",
     "click here; visit; tap this link; continue here",
     "pindutin dito; bisitahin; i-click",
     "scottleechua-ph-sms"),
    ("casino-promo", "Online casino or gambling promotion",
     "Deposit-bonus, cashback, free-spin, or jackpot promotions for unlicensed online gambling sites. The single largest category in the corpus.",
     "casino", 0.562, 465,
     "Guaranteed winnings, free money for registering, and throwaway domains. Often names GCash or Maya as a deposit channel, which is not endorsement.",
     "free bonus; deposit bonus; cashback; jackpot; welcome gift",
     "magdeposito; makakuha ng libre; manalo; magparehistro; taya",
     "scottleechua-ph-sms"),
    ("package-delivery", "Package or delivery problem",
     "Claims a parcel is held pending an unpaid fee or address confirmation.",
     "package", 0.017, 14,
     "Unexpected parcel, small fee demanded by link, courier not named or misspelled.",
     "parcel on hold; unpaid balance; delivery failed; confirm your address",
     "naka-hold ang parcel; may bayad pa; kumpirmahin ang address",
     "scottleechua-ph-sms"),
    ("prize-raffle", "Prize or raffle win",
     "Announces a prize or raffle win the recipient never entered, then asks for a fee or personal details to claim it.",
     "prize", 0.017, 14,
     "You cannot win a raffle you never joined. Claiming a real prize never requires paying first.",
     "congratulations you won; claim your prize; raffle winner",
     "nanalo ka; i-claim ang premyo; binabati kita",
     "scottleechua-ph-sms"),
]

REPORTING_CONTACTS = [
    ("i-arc-1326", "Inter-Agency Response Center (I-ARC)", "1326", "",
     "https://www.cybersecurity.ph/cybercrime-reporting/",
     "Joint DICT / CICC / NPC / NTC reporting hotline for cybercrime and online scams. The single number to give first.",
     1, "cybersecurity-ph-reporting"),
    ("pnp-acg", "PNP Anti-Cybercrime Group", "", "",
     "https://acg.pnp.gov.ph/",
     "Criminal complaints for cybercrime, including online fraud and smishing.",
     2, "pnp-acg-advisories"),
]

ADVISORIES = [
    ("gcash-protect-account", "How can I protect my GCash account?",
     "GCash will NEVER send you links via SMS/email or ask for your MPIN/OTP. "
     "Unexpected offers about winning a prize or a job offer out of nowhere are a scam sign. "
     "Pressure to act fast is a scam sign: scammers rush you so you don't have time to think.",
     None, "en", "gcash-fraud-advisory"),
    ("bdo-stop-scam", "#BDOStopScam",
     "Scam texts (Smishing): Don't click links! BDO messages will not contain links, and sender IDs can be spoofed. "
     "Is the message triggering panic? Requires you to act fast and has a link? If you say yes to all these, it's a scam. "
     "Never share your OTP. In case of fraud, call BDO at (02) 8888-0000.",
     None, "en", "bdo-fraud-advisory"),
]

# Paraphrased corpus templates. None of these matches eval-set.csv.
MESSAGE_EXAMPLES = [
    ("fx-msg-001",
     "BDO ALERT Your online access is suspended. Reactivate here bdo-verify.xyz/login",
     "SCAM", "spam", "bank-impersonation", "bdo", 1, 0, 1),
    ("fx-msg-002",
     "GCASH Notice: I-verify ang iyong account bago mag-expire bukas para hindi ma-deactivate. Click https://bit.ly/gc-verify",
     "SCAM", "spam", "bank-impersonation", "gcash", 1, 3, 1),
    ("fx-msg-003",
     "Deposit 100 get 3% cashback daily! Official GCash partner casino. Register now win jackpot https://luck888.icu",
     "SCAM", "spam", "casino", None, 1, 0, 1),
    ("fx-msg-004",
     "Magdeposito na at makakuha ng libreng 777 bonus! Bagong member welcome gift, manalo agad.",
     "SCAM", "spam", "casino", None, 0, 4, 1),
    ("fx-msg-005",
     "Your parcel is on hold due to unpaid customs fee of P25. Confirm your address here to release: ph-track.top",
     "SCAM", "spam", "package", None, 1, 0, 1),
    ("fx-msg-006",
     "Congratulations! Your number won P150,000 in our anniversary raffle. Claim your prize, contact this number now.",
     "SCAM", "spam", "prize", None, 0, 0, 1),
    ("fx-msg-007",
     "Final warning: your account will be permanently disabled within 24 hours. Update your information immediately.",
     "SCAM", "spam", "bank-impersonation", None, 0, 0, 1),
    ("fx-msg-008",
     "Get your cash advance today! Mababang interes, mabilis na approval. Text me back to avail 50k.",
     "SCAM", "spam", "loan", None, 0, 2, 1),
    # LEGIT rows: stored as contrast, never retrievable.
    ("fx-msg-101",
     "BDO Advisory: For your security, never share your OTP. BDO will never ask for it. Visit bdo.com.ph for more tips.",
     "LEGIT", "ads", None, "bdo", 1, 0, 0),
    ("fx-msg-102",
     "DTI reminder: Beware of text scams this holiday season. Report scam texts to 1682.",
     "LEGIT", "gov", None, None, 0, 0, 0),
]


def _chunk_rows() -> list[tuple]:
    rows = []
    for (pattern_id, name, description, _scam_type, _share, _count,
         red_flags, trig_en, trig_tl, source_id) in LURE_PATTERNS:
        rows.append((
            f"lure-{pattern_id}",
            f"{name}. {description} Red flags: {red_flags}",
            "lure_pattern", pattern_id, source_id, trig_en, trig_tl, None,
        ))
    for (brand_id, brand_name, quote, _hotline, _url, _channels,
         _freq, source_id) in BRAND_REBUTTALS:
        rows.append((
            f"rebuttal-{brand_id}",
            f"{brand_name} official statement: {quote}",
            "brand_rebuttal", brand_id, source_id,
            f"{brand_name} official statement; never asks OTP; no links in SMS",
            "hindi hihingin ang OTP; walang link sa text",
            None,
        ))
    for (advisory_id, title, body, _published, _lang, source_id) in ADVISORIES:
        rows.append((
            f"advisory-{advisory_id}",
            f"{title}. {body}",
            "advisory", advisory_id, source_id,
            "official fraud advisory; how to spot a scam",
            "paano makilala ang scam; opisyal na paalala",
            None,
        ))
    for (message_id, text, label, _cat, scam_type, _brand, _url,
         _markers, _retrievable) in MESSAGE_EXAMPLES:
        # LEGIT examples get chunks too — store.py must provably filter them
        # out via the retrievable flag, so the fixture includes the trap.
        rows.append((
            f"example-{message_id}",
            text,
            "message_example", message_id, "scottleechua-ph-sms",
            scam_type, None, None,
        ))
    return rows


def build(path: Path = FIXTURE_PATH) -> Path:
    path.unlink(missing_ok=True)
    con = sqlite3.connect(path)
    try:
        con.executescript(SCHEMA_FILE.read_text())
        con.executemany("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?)", SOURCES)
        con.executemany("INSERT INTO brand_rebuttals VALUES (?,?,?,?,?,?,?,?)", BRAND_REBUTTALS)
        con.executemany("INSERT INTO lure_patterns VALUES (?,?,?,?,?,?,?,?,?,?)", LURE_PATTERNS)
        con.executemany("INSERT INTO reporting_contacts VALUES (?,?,?,?,?,?,?,?)", REPORTING_CONTACTS)
        con.executemany("INSERT INTO advisories VALUES (?,?,?,?,?,?)", ADVISORIES)
        con.executemany(
            "INSERT INTO message_examples VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                (mid, text, " ".join(text.lower().split()),
                 label, cat, scam_type, brand, has_url, markers, retrievable, 0,
                 None, "scottleechua-ph-sms")
                for (mid, text, label, cat, scam_type, brand,
                     has_url, markers, retrievable) in MESSAGE_EXAMPLES
            ],
        )
        con.executemany("INSERT INTO kb_chunks VALUES (?,?,?,?,?,?,?,?)", _chunk_rows())
        con.commit()
    finally:
        con.close()
    return path


if __name__ == "__main__":
    built = build()
    con = sqlite3.connect(built)
    tables = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    chunks = con.execute("SELECT COUNT(*) FROM kb_chunks").fetchone()[0]
    orphans = con.execute(
        "SELECT COUNT(*) FROM kb_chunks c LEFT JOIN sources s USING (source_id) "
        "WHERE s.source_id IS NULL").fetchone()[0]
    con.close()
    print(f"built {built}")
    print(f"tables: {tables}")
    print(f"chunks: {chunks}, orphaned source_ids: {orphans}")
