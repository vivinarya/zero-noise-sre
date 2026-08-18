"""Ephemeral Sandbox Runner using Docker Engine SDK or isolated subprocess."""

import os
import tempfile
import subprocess
import shutil
from typing import Optional, Dict, Any
from pydantic import BaseModel


class SandboxExecutionResult(BaseModel):
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time_seconds: float
    runner_type: str  # "docker" or "isolated_subprocess"


class SandboxRunner:
    """Spins up an ephemeral isolated environment to apply patches and execute reproduction tests."""

    def __init__(self, docker_image: str = "python:3.11-slim", allow_local_fallback: bool = True):
        self.docker_image = docker_image
        self.allow_local_fallback = allow_local_fallback

    def run_reproduction(
        self,
        service_dir: str,
        target_file: str,
        patch_content: str,
        test_file: str,
        test_code: str,
        test_command: str = "pytest"
    ) -> SandboxExecutionResult:
        """Copies service to a sandbox directory, applies patch and reproduction test, and runs tests."""
        import time
        start_time = time.time()

        # Create temporary isolated directory
        temp_dir = tempfile.mkdtemp(prefix="sre_sandbox_")
        try:
            # Copy service files if directory exists
            if os.path.exists(service_dir):
                for item in os.listdir(service_dir):
                    s = os.path.join(service_dir, item)
                    d = os.path.join(temp_dir, item)
                    if os.path.isdir(s):
                        shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)

            # Apply target file patch
            target_path = os.path.join(temp_dir, target_file)
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(patch_content)

            # Apply reproduction test
            test_path = os.path.join(temp_dir, test_file)
            os.makedirs(os.path.dirname(test_path), exist_ok=True)
            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_code)

            # Try Docker execution if available
            docker_success, docker_result = self._try_docker_run(temp_dir, test_command)
            if docker_success and docker_result is not None:
                duration = time.time() - start_time
                docker_result.execution_time_seconds = duration
                return docker_result

            # Subprocess fallback
            if self.allow_local_fallback:
                proc = subprocess.run(
                    test_command,
                    cwd=temp_dir,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                duration = time.time() - start_time
                return SandboxExecutionResult(
                    success=(proc.returncode == 0),
                    exit_code=proc.returncode,
                    stdout=proc.stdout,
                    stderr=proc.stderr,
                    execution_time_seconds=duration,
                    runner_type="isolated_subprocess"
                )
            else:
                raise RuntimeError("Docker runner failed and local fallback is disabled.")

        except Exception as e:
            duration = time.time() - start_time
            return SandboxExecutionResult(
                success=False,
                exit_code=-1,
                stdout="",
                stderr=str(e),
                execution_time_seconds=duration,
                runner_type="error"
            )
        finally:
            # Clean up temp dir
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    def _try_docker_run(self, mount_dir: str, test_command: str) -> tuple[bool, Optional[SandboxExecutionResult]]:
        try:
            import docker
            client = docker.from_env()
            container = client.containers.run(
                image=self.docker_image,
                command=f"sh -c '{test_command}'",
                volumes={os.path.abspath(mount_dir): {"bind": "/app", "mode": "rw"}},
                working_dir="/app",
                remove=True,
                detach=False,
                stdout=True,
                stderr=True
            )
            return True, SandboxExecutionResult(
                success=True,
                exit_code=0,
                stdout=container.decode("utf-8") if isinstance(container, bytes) else str(container),
                stderr="",
                execution_time_seconds=0.0,
                runner_type="docker"
            )
        except Exception:
            return False, None
