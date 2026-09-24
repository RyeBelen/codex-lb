import re

from pydantic import Field, StrictBool, field_validator, model_validator

from app.modules.shared.schemas import DashboardModel

_MODEL_ID_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,127}$")


class ModelRoutingPolicy(DashboardModel):
    model: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:/-]*$")
    restricted: StrictBool
    account_ids: list[str] = Field(default_factory=list, max_length=1000)

    @field_validator("model", mode="before")
    @classmethod
    def normalize_model(cls, value: str) -> str:
        return value.strip().lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_accounts(self) -> "ModelRoutingPolicy":
        if not self.restricted and self.account_ids:
            raise ValueError("Removing a reservation must have no selected accounts")
        if any(not account_id.strip() for account_id in self.account_ids):
            raise ValueError("Account IDs must not be blank")
        self.account_ids = sorted(set(self.account_ids))
        return self


class ModelRoutingPolicies(DashboardModel):
    rules: list[ModelRoutingPolicy]


class AccountModelOption(DashboardModel):
    id: str
    name: str


class AccountAllowedModels(DashboardModel):
    account_id: str
    allowed_models: list[str]
    available_models: list[AccountModelOption]
    catalog_available: bool


class AccountAllowedModelsUpdate(DashboardModel):
    allowed_models: list[str] = Field(default_factory=list, max_length=1000)

    @field_validator("allowed_models")
    @classmethod
    def normalize_models(cls, values: list[str]) -> list[str]:
        normalized = [value.strip().lower() for value in values]
        if any(not _MODEL_ID_PATTERN.fullmatch(value) for value in normalized):
            raise ValueError("Model IDs must be valid and non-blank")
        return sorted(set(normalized))
