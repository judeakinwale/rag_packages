import time

from rag_packages.shared.auth.schema import JWTConfig, TokenPayload
from rag_packages.shared.auth.token import JWTToken


def test_issue_token_sets_exp_in_unix_seconds() -> None:
    jwt_token = JWTToken(JWTConfig(secret="secret"))
    payload = TokenPayload(sub="123", email="user@example.com")

    before_issue = int(time.time())
    encoded_token = jwt_token.issue_token(payload)
    decoded_payload = jwt_token.decode_token(encoded_token)
    after_issue = int(time.time())

    assert decoded_payload.exp is not None
    assert before_issue + 3600 * 24 <= decoded_payload.exp <= after_issue + 3600 * 24


def test_decode_token_preserves_explicit_seconds_expiry() -> None:
    jwt_token = JWTToken(JWTConfig(secret="secret"))
    expected_exp = int(time.time()) + 120
    payload = TokenPayload(sub="123", email="user@example.com", exp=expected_exp)

    encoded_token = jwt_token.issue_token(payload)
    decoded_payload = jwt_token.decode_token(encoded_token)

    assert decoded_payload.exp == expected_exp