"""Hugging Face Spaces Entrypoint for Zero-Noise SRE Core."""

import os
import sys
import uvicorn
import gradio as gr

# Ensure repo root is on path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from cmd.daemon.main import app

# Create Gradio wrapper to satisfy Hugging Face Spaces SDK while serving full SRE Cockpit
with gr.Blocks(title="Zero-Noise SRE Core", theme=gr.themes.Default()) as demo:
    gr.HTML("""
    <iframe src="/" style="width:100%; height:94vh; border:none; border-radius:12px;"></iframe>
    """)

# Mount FastAPI app
app = gr.mount_gradio_app(app, demo, path="/gradio")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"Starting Zero-Noise SRE Core on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
