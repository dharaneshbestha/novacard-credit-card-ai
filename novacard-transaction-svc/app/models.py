from uuid import UUID

from pydantic import BaseModel, Field


class PurchaseRequest(BaseModel):
    account_id: UUID
    amount_minor: int = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)

class PurchaseResponse(BaseModel):
    status: str
    transaction_id: str
    reason: str | None = None
