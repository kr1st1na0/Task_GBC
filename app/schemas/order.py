from pydantic import BaseModel
from datetime import date


class Order(BaseModel):
    order_id: int
    customer: str
    product: str
    amount: float
    currency: str
    order_date: date
    review: str | None = None
