"""Unit tests for RCA Formatter."""

import pytest
from src.remediation.rca_formatter import RCAFormatter


def test_rca_formatter_structure():
    rca = RCAFormatter.format_rca(
        incident_id="INC-999",
        service_name="payment-service",
        summary="High 500 error rate during checkout",
        root_cause="Null currency caused unhandled AttributeError",
        evidence="Observed 500 status on /charge span",
        validation_output="2 passed in 0.05s",
        patch_diff="+ curr = (req.currency or 'USD').upper()"
    )

    assert "INC-999" in rca.markdown_report
    assert "Summary" in rca.markdown_report
    assert "Root Cause" in rca.markdown_report
    assert "Evidence" in rca.markdown_report
    assert "Sandbox Validation Output" in rca.markdown_report
    assert "Synthesized Patch Diff" in rca.markdown_report
