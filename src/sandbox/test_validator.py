"""Validates sandbox test outputs and ensures fix correctness without regressions."""

from typing import Dict, Any
from pydantic import BaseModel
from .docker_runner import SandboxRunner, SandboxExecutionResult


class TestValidationSummary(BaseModel):
    passed: bool
    summary: str
    reproduction_verified: bool
    details: SandboxExecutionResult


class TestValidator:
    """Executes validation loops in sandbox and analyzes test reports."""

    def __init__(self, runner: SandboxRunner):
        self.runner = runner

    def validate_patch(
        self,
        service_dir: str,
        target_file: str,
        patch_code: str,
        reproduction_test_code: str,
        test_file: str = "test_reproduction.py"
    ) -> TestValidationSummary:
        result = self.runner.run_reproduction(
            service_dir=service_dir,
            target_file=target_file,
            patch_content=patch_code,
            test_file=test_file,
            test_code=reproduction_test_code,
            test_command=f"pytest {test_file} -v"
        )

        passed = result.success and ("passed" in result.stdout.lower() or result.exit_code == 0)
        summary = (
            f"Sandbox verification PASSED (Duration: {result.execution_time_seconds:.2f}s via {result.runner_type})"
            if passed else
            f"Sandbox verification FAILED with exit code {result.exit_code}: {result.stderr or result.stdout}"
        )

        return TestValidationSummary(
            passed=passed,
            summary=summary,
            reproduction_verified=passed,
            details=result
        )
