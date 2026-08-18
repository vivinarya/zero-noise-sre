"""Sliding window anomaly detector evaluating dynamic SLO thresholds."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import numpy as np
import time

from .otel_receiver import OTelReceiver, SpanData


class SLOThresholds(BaseModel):
    latency_p99_ms: float = 800.0
    error_rate_percent: float = 2.0
    sliding_window_seconds: float = 60.0
    min_sample_count: int = 10


class IncidentPayload(BaseModel):
    incident_id: str
    timestamp: float = Field(default_factory=time.time)
    service_name: str
    trigger_reason: str
    observed_p99_ms: float
    observed_error_rate_pct: float
    failing_trace_ids: List[str]
    sample_spans: List[SpanData] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class AnomalyDetector:
    """Evaluates telemetry buffers against statistical SLO degradation thresholds."""

    def __init__(self, receiver: OTelReceiver, thresholds: Optional[SLOThresholds] = None):
        self.receiver = receiver
        self.thresholds = thresholds or SLOThresholds()

    def evaluate_service_health(self, service_name: str) -> Optional[IncidentPayload]:
        recent_spans = self.receiver.get_recent_spans(window_seconds=self.thresholds.sliding_window_seconds)
        service_spans = [s for s in recent_spans if s.service_name == service_name]

        if len(service_spans) < self.thresholds.min_sample_count:
            return None

        durations = [s.duration_ms for s in service_spans]
        p99_latency = float(np.percentile(durations, 99)) if durations else 0.0

        error_spans = [
            s for s in service_spans
            if s.status_code == "ERROR" or (s.http_status_code and s.http_status_code >= 500)
        ]
        error_rate_pct = (len(error_spans) / len(service_spans)) * 100.0

        triggers = []
        if p99_latency > self.thresholds.latency_p99_ms:
            triggers.append(f"p99 latency {p99_latency:.2f}ms exceeds SLO ({self.thresholds.latency_p99_ms}ms)")

        if error_rate_pct > self.thresholds.error_rate_percent:
            triggers.append(f"error rate {error_rate_pct:.2f}% exceeds SLO ({self.thresholds.error_rate_percent}%)")

        if triggers:
            failing_trace_ids = list({s.trace_id for s in error_spans or service_spans[-5:]})
            return IncidentPayload(
                incident_id=f"INC-{int(time.time())}-{service_name}",
                service_name=service_name,
                trigger_reason=" & ".join(triggers),
                observed_p99_ms=p99_latency,
                observed_error_rate_pct=error_rate_pct,
                failing_trace_ids=failing_trace_ids,
                sample_spans=error_spans[:10] if error_spans else service_spans[-10:],
                metadata={
                    "total_samples": len(service_spans),
                    "error_count": len(error_spans),
                }
            )

        return None
