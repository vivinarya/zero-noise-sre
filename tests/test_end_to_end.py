"""End-to-end integration test for Zero-Noise SRE Core autonomous triage loop."""

import os
import time
import pytest
from src.ingestion.otel_receiver import OTelReceiver, SpanData
from src.agent.coordinator import SRECoordinator
from src.agent.llm_client import LLMClient
from src.ingestion.anomaly_detector import IncidentPayload


@pytest.mark.asyncio
async def test_full_sre_triage_lifecycle():
    # 1. Setup Mock Incident
    now_ns = int(time.time() * 1e9)
    trace_id = "trc-e2e-001"

    s1 = SpanData(
        trace_id=trace_id,
        span_id="sp-fe",
        service_name="frontend-gateway",
        operation_name="POST /checkout",
        start_time_ns=now_ns,
        duration_ms=1200.0,
        status_code="ERROR",
        http_status_code=500
    )
    s2 = SpanData(
        trace_id=trace_id,
        span_id="sp-co",
        parent_span_id="sp-fe",
        service_name="checkout-service",
        operation_name="process_order",
        start_time_ns=now_ns + 10_000_000,
        duration_ms=1150.0,
        status_code="ERROR",
        http_status_code=500
    )
    s3 = SpanData(
        trace_id=trace_id,
        span_id="sp-pm",
        parent_span_id="sp-co",
        service_name="payment-service",
        operation_name="charge_payment",
        start_time_ns=now_ns + 20_000_000,
        duration_ms=1100.0,
        status_code="ERROR",
        http_status_code=500,
        error_message="AttributeError: 'NoneType' object has no attribute 'upper' at app.py:18",
        attributes={"currency": None, "amount": 100.0}
    )

    incident = IncidentPayload(
        incident_id="INC-E2E-TEST",
        service_name="payment-service",
        trigger_reason="Error rate 15% > 2%",
        observed_p99_ms=1100.0,
        observed_error_rate_pct=15.0,
        failing_trace_ids=[trace_id],
        sample_spans=[s1, s2, s3]
    )

    # 2. Instantiate LLM Client in mock mode (simulating Gemma deterministic output)
    llm_client = LLMClient(backend="mock")

    fixtures_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures"))
    coordinator = SRECoordinator(llm_client=llm_client, service_repo_base=fixtures_dir)

    # 3. Execute Triage
    state = await coordinator.execute_triage(incident)

    # 4. Assertions
    assert state.stage == "RESOLVED"
    assert state.causal_result is not None
    assert state.causal_result.culprit_service == "payment-service"
    assert state.causal_result.culprit_operation == "charge_payment"
    assert state.validation_summary is not None
    assert state.validation_summary.passed is True
    assert state.rca is not None
    assert "Incident Root Cause Analysis" in state.rca.markdown_report
    assert state.pr_result is not None
    assert state.pr_result.success is True
    assert "pull" in state.pr_result.pr_url
