"""Hugging Face Spaces Entrypoint for Zero-Noise SRE Core."""

import os
import sys
import uvicorn

# Ensure repo root is on path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from cmd.daemon.main import app

if __name__ == "__main__":
    # Hugging Face Spaces listens on port 7860 by default
    port = int(os.environ.get("PORT", 7860))
    print(f"Starting Zero-Noise SRE Core on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
