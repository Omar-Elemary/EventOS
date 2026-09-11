from app.services.auth import hash_password, issue_token, parse_token, verify_password


def test_password_roundtrip():
    stored = hash_password("secret12")
    assert verify_password("secret12", stored)
    assert not verify_password("wrong-pass", stored)


def test_token_roundtrip():
    token = issue_token("user-1", "a@b.co", "Ada")
    assert parse_token(token) == "user-1"
    assert parse_token("not-a-token") is None
    from app.services.auth import parse_token_claims

    claims = parse_token_claims(token)
    assert claims is not None
    assert claims["email"] == "a@b.co"
    assert claims["name"] == "Ada"
