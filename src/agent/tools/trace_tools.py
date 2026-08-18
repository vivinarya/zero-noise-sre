"""Jaeger / OTel Trace query tool."""

import httpx
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from src.ingestion.otel_receiver import SpanData


class SpanHierarchy(BaseModel):
    trace_id: str
    spans: List[SpanData]
    root_service: str
    error_count: int


class TraceTools:
    """Queries distributed trace hierarchies from Jaeger/Tempo or local OTel receiver."""

    def __init__(self, jaeger_url: str = "http://localhost:16686/api/traces", local_receiver: Optional[Any] = None):
        self.jaeger_url = jaeger_url
        self.local_receiver = local_receiver

    async def query_trace(self, trace_id: str) -> SpanHierarchy:
        # Check local receiver memory first
        if self.local_receiver:
            spans = self.local_receiver.get_spans_by_trace_id(trace_id)
            if spans:
                errors = [s for s in spans if s.status_code == "ERROR" or (s.http_status_code and s.http_status_code >= 500)]
                return SpanHierarchy(
                    trace_id=trace_id,
                    spans=spans,
                    root_service=spans[0].service_name,
                    error_count=len(errors)
                )

        # Fallback to Jaeger HTTP API
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.jaeger_url}/{trace_id}")
                if resp.status_code == 200:
                    # In production, parse Jaeger format into SpanData
                    pass
        except Exception:
            pass

        return SpanHierarchy(
            trace_id=trace_id,
            spans=[],
            root_service="unknown",
            error_count=0
        )
