from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from ..ingestion.otel_receiver import SpanData
from .causal_tracer import CausalPathResult


class CompressedContext(BaseModel):
    incident_summary: str
    culprit_service: str
    culprit_operation: str
    error_signature: str
    upstream_callers: List[str]
    critical_attributes: Dict[str, Any]
    stack_trace_snippet: Optional[str] = None
    compact_prompt_block: str


class ContextDistiller:
    """Pre-processes verbose telemetry into ultra-compact, high-signal prompt blocks."""

    @staticmethod
    def distill(
        causal_result: CausalPathResult,
        spans: List[SpanData],
        recent_git_diff: Optional[str] = None
    ) -> CompressedContext:
        culprit_span = next((s for s in spans if s.span_id == causal_result.culprit_span_id), None)
        critical_attrs = {}
        stack_trace = None

        if culprit_span:
            for k, v in culprit_span.attributes.items():
                if any(x in k.lower() for x in ["http", "db", "user", "error", "currency", "id", "code"]):
                    critical_attrs[k] = v

            for ev in culprit_span.events:
                attrs = ev.get("attributes", {})
                if "exception.stacktrace" in attrs:
                    # Only take the top 5 lines of stacktrace for token efficiency
                    lines = attrs["exception.stacktrace"].strip().split("\n")
                    stack_trace = "\n".join(lines[-5:])

        prompt_lines = [
            f"SERVICE: {causal_result.culprit_service}",
            f"OPERATION: {causal_result.culprit_operation}",
            f"CALL_CHAIN: {' -> '.join(causal_result.call_chain)}",
            f"ROOT_ERROR: {causal_result.root_error_message or 'Unknown Error'}",
        ]
        if critical_attrs:
            prompt_lines.append(f"RELEVANT_ATTRIBUTES: {critical_attrs}")
        if stack_trace:
            prompt_lines.append(f"STACK_TRACE_SNIPPET:\n{stack_trace}")
        if recent_git_diff:
            prompt_lines.append(f"RECENT_COMMITS_DIFF:\n{recent_git_diff.strip()[:1500]}")

        compact_block = "\n".join(prompt_lines)

        return CompressedContext(
            incident_summary=causal_result.root_cause_summary,
            culprit_service=causal_result.culprit_service,
            culprit_operation=causal_result.culprit_operation,
            error_signature=causal_result.root_error_message or "Internal Error",
            upstream_callers=causal_result.call_chain[:-1],
            critical_attributes=critical_attrs,
            stack_trace_snippet=stack_trace,
            compact_prompt_block=compact_block
        )
