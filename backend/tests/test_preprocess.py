from app.preprocess import detect_message_type, preprocess, redact


class TestMessageTypeDetection:
    def test_bare_url_is_url(self):
        assert detect_message_type("https://bit.ly/gc-verify") == "url"

    def test_www_url_is_url(self):
        assert detect_message_type("  www.luck888.icu/promo  ") == "url"

    def test_subject_line_is_email(self):
        text = "Subject: Account Verification Required\nDear customer, verify now."
        assert detect_message_type(text) == "email"

    def test_from_header_is_email(self):
        text = "From: security@bdo-alerts.xyz\nYour account is on hold."
        assert detect_message_type(text) == "email"

    def test_plain_text_is_sms(self):
        assert detect_message_type("BDO ALERT: verify your account now") == "sms"

    def test_text_containing_url_is_still_sms(self):
        assert detect_message_type("Click here https://bit.ly/x to verify") == "sms"


class TestRedaction:
    def test_otp_near_keyword(self):
        redacted, labels = redact("Your OTP is 123456. Do not share it.")
        assert "123456" not in redacted
        assert "[OTP]" in redacted
        assert "OTP" in labels

    def test_otp_keyword_after_digits(self):
        redacted, labels = redact("Use 4821 as your verification code")
        assert "4821" not in redacted
        assert "OTP" in labels

    def test_card_number(self):
        redacted, labels = redact("Card 4532015112830366 has been charged")
        assert "4532015112830366" not in redacted
        assert "[CARD]" in redacted
        assert "CARD" in labels

    def test_account_number(self):
        redacted, labels = redact("Deposit to acct 1234567890 today")
        assert "1234567890" not in redacted
        assert "[ACCOUNT]" in redacted
        assert "ACCOUNT" in labels

    def test_phone_09_format(self):
        redacted, labels = redact("Text me at 09171234567 now")
        assert "09171234567" not in redacted
        assert "[PHONE]" in redacted
        assert "PHONE" in labels

    def test_phone_plus639_format(self):
        redacted, labels = redact("Call +639171234567 to claim")
        assert "+639171234567" not in redacted
        assert "[PHONE]" in redacted

    def test_phone_not_mislabelled_as_account(self):
        _, labels = redact("Text me at 09171234567 now")
        assert "ACCOUNT" not in labels

    def test_email_address(self):
        redacted, labels = redact("Send details to winner@luck888.icu now")
        assert "winner@luck888.icu" not in redacted
        assert "[EMAIL]" in redacted
        assert "EMAIL" in labels

    def test_urls_preserved(self):
        text = "Verify at https://bdo-verify.xyz/login?acct=1234567890 today"
        redacted, _ = redact(text)
        assert "https://bdo-verify.xyz/login?acct=1234567890" in redacted

    def test_url_digits_not_redacted(self):
        redacted, labels = redact("Visit www.promo123456789012.com now")
        assert "www.promo123456789012.com" in redacted
        assert "ACCOUNT" not in labels

    def test_labels_are_unique(self):
        _, labels = redact("Call 09171234567 or 09181234567")
        assert labels == ["PHONE"]

    def test_clean_text_untouched(self):
        text = "GCASH Notice: I-verify ang iyong account"
        redacted, labels = redact(text)
        assert redacted == text
        assert labels == []


class TestPreprocess:
    def test_bundles_type_and_redaction(self):
        result = preprocess("Your OTP is 123456")
        assert result.message_type == "sms"
        assert result.redactions == ["OTP"]
        assert "123456" not in result.redacted_text
