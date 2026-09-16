import pytest
from pydantic import ValidationError

from app.modules.accounts.schemas import AccountAccessRequest

pytestmark = pytest.mark.unit


def test_restricted_empty_is_distinct_from_shared():
    assert AccountAccessRequest(restricted=True, api_key_ids=[]).restricted is True
    assert AccountAccessRequest(restricted=False, api_key_ids=[]).restricted is False


@pytest.mark.parametrize(
    "body",
    [
        {"restricted": None, "apiKeyIds": []},
        {"restricted": 1, "apiKeyIds": []},
        {"restricted": True, "apiKeyIds": [1]},
        {"restricted": True, "apiKeyIds": [" padded "]},
        {"restricted": False, "apiKeyIds": ["key"]},
        {"restricted": True},
    ],
)
def test_invalid_access_policy_rejected(body):
    with pytest.raises(ValidationError):
        AccountAccessRequest.model_validate(body)
