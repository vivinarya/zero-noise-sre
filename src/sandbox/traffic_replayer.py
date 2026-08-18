"""Traffic replayer for sanitizing and replaying production requests against sandbox instances."""

import re
from typing import Dict, Any, Optional
from pydantic import BaseModel


class ReplayRequest(BaseModel):
    method: str
    endpoint: str
    headers: Dict[str, str]
    payload: Dict[str, Any]


class ReplayResult(BaseModel):
    status_code: int
    response_body: Dict[str, Any]
    latency_ms: float
    error: Optional[str] = None


class TrafficReplayer:
    """Sanitizes sensitive headers/tokens and replays failing requests."""

    SENSITIVE_PATTERNS = [
        re.compile(r"bearer\s+[a-zA-Z0-9_\-\.]+", re.IGNORECASE),
        re.compile(r"api[_-]?key", re.IGNORECASE),
        re.compile(r"authorization", re.IGNORECASE),
        re.compile(r"cookie", re.IGNORECASE),
        re.compile(r"password", re.IGNORECASE),
    ]

    def sanitize_request(self, req: ReplayRequest) -> ReplayRequest:
        sanitized_headers = {}
        for k, v in req.headers.items():
            if any(p.search(k) for p in self.SENSITIVE_PATTERNS):
                sanitized_headers[k] = "[REDACTED_BY_SRE]"
            else:
                sanitized_headers[k] = v

        sanitized_payload = self._sanitize_dict(req.payload)
        return ReplayRequest(
            method=req.method,
            endpoint=req.endpoint,
            headers=sanitized_headers,
            payload=sanitized_payload
        )

    def _sanitize_dict(self, data: Any) -> Any:
        if isinstance(data, dict):
            new_dict = {}
            for k, v in data.items():
                if any(p.search(str(k)) for p in self.SENSITIVE_PATTERNS):
                    new_dict[k] = "[REDACTED]"
                else:
                    new_dict[k] = self._sanitize_dict(v)
            return new_dict
        elif isinstance(data, list):
            return [self._sanitize_dict(item) for item in data]
        return data
