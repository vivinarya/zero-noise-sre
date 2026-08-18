import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


def test_charge_with_valid_currency():
    response = client.post("/charge", json={"amount": 50.0, "currency": "usd", "account_id": "acc_001"})
    assert response.status_code == 200
    assert response.json()["currency"] == "USD"


def test_charge_invalid_amount():
    response = client.post("/charge", json={"amount": -10.0, "currency": "usd", "account_id": "acc_001"})
    assert response.status_code == 400
