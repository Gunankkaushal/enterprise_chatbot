import pytest
from pydantic import ValidationError

from services.database.schemas import UserCreate


def test_user_create_accepts_valid_password():
    user = UserCreate(
        email="valid@example.com",
        password="ValidPass@123",
        is_admin=True,
        department_id=None
    )
    assert user.email == "valid@example.com"


@pytest.mark.parametrize(
    "password",
    [
        "short1A!",
        "nouppercase123!",
        "NOLOWERCASE123!",
        "NoNumber!!!",
        "NoSpecial12345",
    ],
)
def test_user_create_rejects_weak_passwords(password):
    with pytest.raises(ValidationError):
        UserCreate(
            email="invalid@example.com",
            password=password,
            is_admin=True,
            department_id=None
        )
