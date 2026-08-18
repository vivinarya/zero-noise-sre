"""Unit tests for Topology Graph and Causal Tracer."""

import pytest
from src.ingestion.otel_receiver import SpanData
from src.topology.graph_builder import TopologyGraphBuilder
from src.topology.causal_tracer import CausalTracer


@pytest.fixture
def sample_spans():
    now = 1723990000000000000
    s1 = SpanData(
        trace_id="t1",
        span_id="sp1",
        service_name="frontend",
        operation_name="GET /items",
        start_time_ns=now,
        duration_ms=100.0,
        status_code="ERROR",
        http_status_code=500
    )
    s2 = SpanData(
        trace_id="t1",
        span_id="sp2",
        parent_span_id="sp1",
        service_name="item-service",
        operation_name="fetch_item",
        start_time_ns=now + 5_000_000,
        duration_ms=90.0,
        status_code="ERROR",
        http_status_code=500,
        error_message="KeyError: 'item_id'"
    )
    return [s1, s2]


def test_topology_graph_builder(sample_spans):
    builder = TopologyGraphBuilder()
    graph = builder.build_from_spans(sample_spans)
    assert "frontend" in graph.nodes
    assert "item-service" in graph.nodes
    assert graph.has_edge("frontend", "item-service")

    deps = builder.get_service_dependencies("item-service")
    assert "frontend" in deps["upstream"]


def test_causal_tracer(sample_spans):
    tracer = CausalTracer()
    res = tracer.trace_root_cause(sample_spans)
    assert res is not None
    assert res.culprit_service == "item-service"
    assert res.culprit_operation == "fetch_item"
    assert "KeyError" in res.root_error_message
