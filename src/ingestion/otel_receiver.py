"""OTel receiver and telemetry data structures."""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
import time


class SpanData(BaseModel):
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    service_name: str
    operation_name: str
    start_time_ns: int
    duration_ms: float
    status_code: str = "OK"  # "OK", "ERROR", "UNSET"
    error_message: Optional[str] = None
    http_status_code: Optional[int] = None
    http_method: Optional[str] = None
    http_url: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)
    events: List[Dict[str, Any]] = Field(default_factory=list)


class MetricSample(BaseModel):
    metric_name: str
    service_name: str
    timestamp: float = Field(default_factory=time.time)
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)


class OTelReceiver:
    """Ingests and holds sliding window telemetry buffers for anomaly detection."""

    def __init__(self, max_buffer_size: int = 5000):
        self.max_buffer_size = max_buffer_size
        self._spans: List[SpanData] = []
        self._metrics: List[MetricSample] = []

    def record_span(self, span: SpanData) -> None:
        self._spans.append(span)
        if len(self._spans) > self.max_buffer_size:
            self._spans.pop(0)

    def record_metric(self, metric: MetricSample) -> None:
        self._metrics.append(metric)
        if len(self._metrics) > self.max_buffer_size:
            self._metrics.pop(0)

    def get_recent_spans(self, window_seconds: float = 60.0) -> List[SpanData]:
        cutoff_ns = (time.time() - window_seconds) * 1e9
        return [s for s in self._spans if s.start_time_ns >= cutoff_ns]

    def get_spans_by_trace_id(self, trace_id: str) -> List[SpanData]:
        return [s for s in self._spans if s.trace_id == trace_id]

    def get_recent_metrics(self, metric_name: Optional[str] = None, window_seconds: float = 60.0) -> List[MetricSample]:
        cutoff = time.time() - window_seconds
        return [
            m for m in self._metrics
            if m.timestamp >= cutoff and (metric_name is None or m.metric_name == metric_name)
        ]
