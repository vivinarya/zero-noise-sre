"""Unified patch synthesizer."""

import difflib
from typing import Optional
from pydantic import BaseModel


class UnifiedPatch(BaseModel):
    target_file: str
    diff_text: str
    original_lines_count: int
    modified_lines_count: int


class PatchGenerator:
    """Generates clean unified diffs from original and patched file contents."""

    @staticmethod
    def generate_diff(
        target_file: str,
        original_content: str,
        patched_content: str
    ) -> UnifiedPatch:
        orig_lines = original_content.splitlines(keepends=True)
        patched_lines = patched_content.splitlines(keepends=True)

        diff = difflib.unified_diff(
            orig_lines,
            patched_lines,
            fromfile=f"a/{target_file}",
            tofile=f"b/{target_file}",
            lineterm=""
        )
        diff_text = "\n".join(diff)

        return UnifiedPatch(
            target_file=target_file,
            diff_text=diff_text or f"# Full rewrite for {target_file}\n" + patched_content,
            original_lines_count=len(orig_lines),
            modified_lines_count=len(patched_lines)
        )
