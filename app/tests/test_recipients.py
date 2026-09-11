import pytest

from whatsapp_scheduler.recipients import RecipientError, normalize_recipient


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+55 11 99999-8888", "5511999998888@c.us"),
        ("5511999998888", "5511999998888@c.us"),
        ("11999998888", "5511999998888@c.us"),
        ("  +5511999998888 ", "5511999998888@c.us"),
        ("5511999998888@c.us", "5511999998888@c.us"),
        ("120363000000000000@g.us", "120363000000000000@g.us"),
        ("104311971410143@lid", "104311971410143@lid"),
    ],
)
def test_normalize_recipient(raw, expected):
    assert normalize_recipient(raw) == expected


@pytest.mark.parametrize("raw", ["", "abc", "123", "+1 000"])
def test_normalize_recipient_invalid(raw):
    with pytest.raises(RecipientError):
        normalize_recipient(raw)
