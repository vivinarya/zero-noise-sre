"""Unit tests for Anomaly Detector."""

import time
import pytest
from src.ingestion.otel_receiver import OTelReceiver, SpanData
from src.ingestion.anomaly_detector import AnomalyDetector, SLOThresholds


def test_anomaly_detector_trigger():
    receiver = OTelReceiver()
    thresholds = SLOThresholds(latency_p99_ms=500.0, error_rate_percent=5.0, sliding_window_seconds=60.0, min_sample_count=5)
    detector = AnomalyDetector(receiver, thresholds)

    now_ns = int(time.time() * 1e9)

    # Record 4 healthy spans and 2 failing spans
    for i in range(4):
        receiver.record_span(SpanData(
            trace_id=f"t{i}",
            span_id=f"s{i}",
            service_name="payment-service",
            operation_name="charge",
            start_time_ns=now_ns,
            duration_ms=50.0,
            status_code="OK"
        ))

    for i in range(4, 6):
        receiver.record_span(SpanData(
            trace_id=f"t{i}",
            span_id=f"s{i}",
            service_name="payment-service",
            operation_name="charge",
            start_time_ns=now_ns,
            duration_ms=850.0,
            status_code="ERROR",
            http_status_code=500
        ))

    incident = detector.evaluate_service_health("payment-service")
    assert incident is not None
    assert incident.service_name == "payment-service"
    assert incident.observed_error_rate_pct > 5.0
