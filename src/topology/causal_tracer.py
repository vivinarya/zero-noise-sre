"""Traverses causal paths to isolate root-cause microservices and offending spans."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import networkx as nx
from ..ingestion.otel_receiver import SpanData


class CausalPathResult(BaseModel):
    culprit_service: str
    culprit_operation: str
    culprit_span_id: str
    root_error_message: Optional[str]
    call_chain: List[str]
    root_cause_summary: str


class CausalTracer:
    """Isolates the root failure in a distributed trace tree."""

    def __init__(self, graph: Optional[nx.DiGraph] = None):
        self.graph = graph

    def trace_root_cause(self, trace_spans: List[SpanData]) -> Optional[CausalPathResult]:
        if not trace_spans:
            return None

        # Build tree of spans
        span_lookup = {s.span_id: s for s in trace_spans}
        children_map: Dict[str, List[SpanData]] = {}
        roots: List[SpanData] = []

        for s in trace_spans:
            if not s.parent_span_id or s.parent_span_id not in span_lookup:
                roots.append(s)
            else:
                children_map.setdefault(s.parent_span_id, []).append(s)

        # Find the deepest span with an error or unhandled exception
        error_spans = [
            s for s in trace_spans
            if s.status_code == "ERROR" or (s.http_status_code and s.http_status_code >= 500)
        ]

        if not error_spans:
            # Fallback to slowest span if latency triggered
            slowest = max(trace_spans, key=lambda s: s.duration_ms)
            return CausalPathResult(
                culprit_service=slowest.service_name,
                culprit_operation=slowest.operation_name,
                culprit_span_id=slowest.span_id,
                root_error_message=f"High latency bottleneck ({slowest.duration_ms:.2f}ms)",
                call_chain=[slowest.service_name],
                root_cause_summary=f"Degradation isolated to {slowest.service_name}:{slowest.operation_name} (latency {slowest.duration_ms:.2f}ms)"
            )

        # Identify the deepest leaf error span (the root culprit)
        # An error span is a leaf error if none of its child spans are error spans
        error_span_ids = {s.span_id for s in error_spans}
        leaf_error_spans = []
        for s in error_spans:
            children = children_map.get(s.span_id, [])
            has_error_child = any(c.span_id in error_span_ids for c in children)
            if not has_error_child:
                leaf_error_spans.append(s)

        # Prefer leaf error with explicit exception message/events if available
        culprit_span = None
        for s in leaf_error_spans:
            if s.error_message or s.events:
                culprit_span = s
                break
        if not culprit_span:
            culprit_span = leaf_error_spans[0] if leaf_error_spans else error_spans[-1]

        earliest_error = culprit_span

        # Reconstruct call chain from root down to earliest_error
        chain: List[str] = []
        curr = earliest_error
        while curr:
            chain.append(f"{curr.service_name}:{curr.operation_name}")
            if curr.parent_span_id and curr.parent_span_id in span_lookup:
                curr = span_lookup[curr.parent_span_id]
            else:
                break
        chain.reverse()

        error_msg = earliest_error.error_message
        if not error_msg and earliest_error.events:
            for event in earliest_error.events:
                if "exception.message" in event.get("attributes", {}):
                    error_msg = event["attributes"]["exception.message"]
                    break
        if not error_msg and earliest_error.http_status_code:
            error_msg = f"HTTP {earliest_error.http_status_code} Internal Server Error"

        return CausalPathResult(
            culprit_service=earliest_error.service_name,
            culprit_operation=earliest_error.operation_name,
            culprit_span_id=earliest_error.span_id,
            root_error_message=error_msg,
            call_chain=chain,
            root_cause_summary=f"Isolated root failure in service '{earliest_error.service_name}' at operation '{earliest_error.operation_name}': {error_msg}"
        )
