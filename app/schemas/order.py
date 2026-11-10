from pydantic import BaseModel
from datetime import date

#? потом допилить (по идее правда в файле только такие)
SUPPORTED_CURRENCIES = {"USD", "EUR", "GBP", "RUB"}


class Order(BaseModel):
    order_id: int
    customer: str
    product: str
    amount: float
    currency: str
    order_date: date
    review: str | None = None
