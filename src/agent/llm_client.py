"""Unified LLM client supporting local Gemma via Ollama, in-browser WebGPU WebSocket bridge, and mock mode."""

import json
import re
import asyncio
from typing import Dict, Any, Optional
import httpx
from pydantic import BaseModel, Field


class LLMResponse(BaseModel):
    raw_text: str
    parsed_json: Optional[Dict[str, Any]] = None
    model_name: str
    backend: str


class LLMClient:
    """Dispatches reasoning requests to Ollama, OpenAI-compatible local APIs, WebGPU browser bridge, or Mock engine."""

    def __init__(
        self,
        backend: str = "ollama",
        model: str = "gemma2:2b",
        ollama_endpoint: str = "http://localhost:11434",
        openai_endpoint: str = "http://localhost:8080/v1",
        ws_browser_queue: Optional[asyncio.Queue] = None
    ):
        self.backend = backend
        self.model = model
        self.ollama_endpoint = ollama_endpoint.rstrip("/")
        self.openai_endpoint = openai_endpoint.rstrip("/")
        self.ws_browser_queue = ws_browser_queue

    async def generate(self, prompt: str, temperature: float = 0.1) -> LLMResponse:
        if self.backend == "ollama":
            return await self._generate_ollama(prompt, temperature)
        elif self.backend == "openai_compatible":
            return await self._generate_openai_compatible(prompt, temperature)
        elif self.backend == "browser_webgpu":
            return await self._generate_browser_webgpu(prompt)
        elif self.backend == "mock":
            return await self._generate_mock(prompt)
        else:
            raise ValueError(f"Unsupported LLM backend: {self.backend}")

    async def _generate_ollama(self, prompt: str, temperature: float) -> LLMResponse:
        url = f"{self.ollama_endpoint}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data.get("response", "")
            parsed = self._extract_json(raw_text)
            return LLMResponse(
                raw_text=raw_text,
                parsed_json=parsed,
                model_name=self.model,
                backend="ollama"
            )

    async def _generate_openai_compatible(self, prompt: str, temperature: float) -> LLMResponse:
        url = f"{self.openai_endpoint}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw_text = data["choices"][0]["message"]["content"]
            parsed = self._extract_json(raw_text)
            return LLMResponse(
                raw_text=raw_text,
                parsed_json=parsed,
                model_name=self.model,
                backend="openai_compatible"
            )

    async def _generate_browser_webgpu(self, prompt: str) -> LLMResponse:
        """Sends inference task to the connected browser WebGPU worker."""
        if not self.ws_browser_queue:
            # If no browser worker is connected, fallback to mock for safety
            return await self._generate_mock(prompt)

        # Send request to browser queue and wait for response
        response_future = asyncio.get_event_loop().create_future()
        await self.ws_browser_queue.put({"prompt": prompt, "future": response_future})
        raw_text = await asyncio.wait_for(response_future, timeout=90.0)
        parsed = self._extract_json(raw_text)
        return LLMResponse(
            raw_text=raw_text,
            parsed_json=parsed,
            model_name="gemma-2b-webgpu",
            backend="browser_webgpu"
        )

    async def _generate_mock(self, prompt: str) -> LLMResponse:
        """Deterministic mock generator for testing."""
        mock_payload = {
            "hypothesis": "The payment-service crashes when 'currency' attribute is None or omitted in the payload because it calls .upper() without null-check.",
            "root_cause_summary": "AttributeError: 'NoneType' object has no attribute 'upper' at payment_service/app.py:18",
            "target_file": "app.py",
            "patch_code": '''from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Payment Service")

class PaymentRequest(BaseModel):
    amount: float
    currency: Optional[str] = "USD"
    account_id: str

@app.post("/charge")
def charge_payment(req: PaymentRequest):
    # Fixed: Safe default handling for null or missing currency
    curr = (req.currency or "USD").upper()
    if req.amount <= 0:
        raise HTTPException(status_code=400, detail="Invalid amount")
    return {"status": "SUCCESS", "currency": curr, "charged": req.amount}
''',
            "reproduction_test_code": '''import pytest
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_charge_with_null_currency():
    # Reproduction test: None currency should default to USD without 500 error
    response = client.post("/charge", json={"amount": 100.0, "currency": None, "account_id": "acc_123"})
    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"
    assert response.json()["currency"] == "USD"

def test_charge_with_valid_currency():
    response = client.post("/charge", json={"amount": 50.0, "currency": "eur", "account_id": "acc_456"})
    assert response.status_code == 200
    assert response.json()["currency"] == "EUR"
''',
            "rca": {
                "summary": "Payment Service experienced 500 Internal Server Errors due to unhandled NoneType currency attribute during checkout requests.",
                "root_cause": "app.py line 18 performed req.currency.upper() without verifying if currency was None, causing unhandled AttributeError.",
                "evidence": "Span HTTP POST /charge returned status 500. Stack trace confirmed AttributeError on NoneType in payment-service.",
                "preventative_actions": [
                    "Add Pydantic validator to guarantee default currency",
                    "Add automated contract testing for nullable telemetry attributes"
                ]
            }
        }
        raw_text = json.dumps(mock_payload, indent=2)
        return LLMResponse(
            raw_text=raw_text,
            parsed_json=mock_payload,
            model_name="mock-gemma",
            backend="mock"
        )

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        try:
            # Check for ```json block
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            # Check for bare JSON object
            match = re.search(r"(\{.*\})", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            return None
        except Exception:
            return None
