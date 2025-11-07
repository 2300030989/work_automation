import pytest
from engine.helper import extract_yt_term

@pytest.mark.parametrize("cmd,expected", [
    ("play dosti song", "dosti song"),
    ("play dosti song on youtube", "dosti song"),
    ("youtube play dosti song", "dosti song"),
    ("open youtube play dosti song", "dosti song"),
    ("open youtube", None),
    ("youtube", None),
    ("please play bohemian rhapsody on youtube", "bohemian rhapsody"),
])
def test_extract_yt_term(cmd, expected):
    assert extract_yt_term(cmd) == expected
