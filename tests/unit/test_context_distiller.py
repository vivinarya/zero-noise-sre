"""Unit tests for Gemma Context Distiller."""

import pytest
from src.ingestion.otel_receiver import SpanData
from src.topology.causal_tracer import CausalPathResult
from src.topology.context_distiller import ContextDistiller


def test_context_distiller():
    causal_res = CausalPathResult(
        culprit_service="payment-service",
        culprit_operation="charge_payment",
        culprit_span_id="sp_99",
        root_error_message="AttributeError: NoneType",
        call_chain=["frontend", "checkout", "payment-service"],
        root_cause_summary="Payment failed due to null currency"
    )

    span = SpanData(
        trace_id="t1",
        span_id="sp_99",
        service_name="payment-service",
        operation_name="charge_payment",
        start_time_ns=1000,
        duration_ms=500.0,
        attributes={"currency": None, "http.method": "POST"}
    )

    distilled = ContextDistiller.distill(
        causal_result=causal_res,
        spans=[span],
        recent_git_diff="+ curr = req.currency.upper()"
    )

    assert "payment-service" in distilled.compact_prompt_block
    assert "charge_payment" in distilled.compact_prompt_block
    assert "RECENT_COMMITS_DIFF" in distilled.compact_prompt_block
    assert len(distilled.compact_prompt_block) < 3000
