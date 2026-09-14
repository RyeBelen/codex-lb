from pydantic import Field, StrictBool, field_validator, model_validator

from app.modules.shared.schemas import DashboardModel


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
