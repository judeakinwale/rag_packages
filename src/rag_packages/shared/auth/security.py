from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError, VerifyMismatchError


password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return False


def verify_and_rehash_password(
    password: str, password_hash: str
) -> tuple[bool, str | None]:
    try:
        password_is_valid = password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return False, None

    if not password_is_valid:
        return False, None

    if password_hasher.check_needs_rehash(password_hash):
        return True, password_hasher.hash(password)

    return True, None
