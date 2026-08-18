"""Sample payment microservice with an unhandled null currency bug."""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Payment Service")


class PaymentRequest(BaseModel):
    amount: float
    currency: Optional[str] = None
    account_id: str


@app.post("/charge")
def charge_payment(req: PaymentRequest):
    # BUG: If currency is None, calling .upper() causes AttributeError (500 error)
    curr = req.currency.upper()

    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")

    return {
        "status": "SUCCESS",
        "currency": curr,
        "charged": req.amount
    }
