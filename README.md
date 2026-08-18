# Zero-Noise SRE Core

**Autonomous Agentic Site Reliability Engineering & Real-time Causal Debugger**  
*Optimized for Lightweight & In-Browser Open Source Gemma (WebGPU / Local Edge) & Frontier Models*

---

## Overview

**Zero-Noise SRE Core** is an autonomous reliability framework that continuously monitors OpenTelemetry/Prometheus telemetry, isolates root cause microservices via DAG topological causal tracing, synthesizes verified deterministic code patches using **Google Gemma (2B / 3 1B-4B)**, and publishes Pull Requests with strict Markdown Post-Mortem RCAs.

### Key Highlights
- **In-Browser WebGPU Inference**: Run Gemma 2B directly in any consumer browser window using WebGPU shader acceleration via WebLLM — zero cloud GPU bills and zero API key requirements.
- **Local Edge Support**: Run against local `ollama run gemma2:2b` or `llama.cpp` on low-end CPUs (< 1.5 GB RAM).
- **Topology DAG & Context Distillation**: Pre-compresses verbose distributed traces into ultra-compact, high-signal prompt blocks (< 1000 tokens) guaranteeing high reasoning accuracy with small parameter models.
- **Ephemeral Sandbox Verification**: Validates generated patches and reproduction tests in an isolated Docker container / subprocess sandbox before touching Git branches.
- **Strict RCA Schema**: Enforces standard SRE post-mortem format (Summary, Root Cause, Evidence, Validation).

---

## Architecture

```
                                [Production Cluster / Microservices]
                                                │
                                                ▼
                                    [OTel Collector & Vector]
                                                │
                 ┌──────────────────────────────┴──────────────────────────────┐
                 ▼                                                             ▼
       [Prometheus (Metrics)]                                         [Jaeger (Traces)]
                 │                                                             │
                 └──────────────────────────────┬──────────────────────────────┘
                                                ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   ZERO-NOISE SRE CORE                                       │
│                                                                                             │
│  ┌───────────────────────┐      ┌─────────────────────────┐      ┌───────────────────────┐  │
│  │   Telemetry Ingest    │ ───► │  Topology DAG & Context │ ───► │ Gemma Reasoning Engine│  │
│  │   • Trace Aggregator  │      │  Distiller (NetworkX)   │      │ • In-Browser WebGPU   │  │
│  │   • Anomaly Detector  │      │                         │      │ • Local Ollama / Edge │  │
│  └───────────────────────┘      └─────────────────────────┘      └───────────┬───────────┘  │
│                                                                              │              │
│  ┌───────────────────────────────────────────────────────────────────────────┘              │
│  ▼                                                                                          │
│  ┌───────────────────────┐      ┌─────────────────────────┐      ┌───────────────────────┐  │
│  │ Ephemeral Sandbox     │ ───► │  Test Validator Loop    │ ───► │ Remediation           │  │
│  │ Runner (Docker Engine)│      │  (Pytest / Regression)  │      │ Dispatcher            │  │
│  └───────────────────────┘      └─────────────────────────┘      └───────────┬───────────┘  │
└──────────────────────────────────────────────────────────────────────────────┼──────────────┘
                                                                               ▼
                                                                  [GitHub Draft PR + Markdown RCA]
```

---

## Repository Structure

```
zero-noise-sre/
├── cmd/
│   └── daemon/
│       └── main.py              # Telemetry watcher & FastAPI/WebSocket server
├── config/
│   ├── config.yaml              # Dynamic SLO thresholds & LLM configuration
│   ├── otel-collector.yaml      # OTLP pipeline definitions
│   └── prometheus.yml           # Prometheus scrape configuration
├── src/
│   ├── ingestion/
│   │   ├── otel_receiver.py     # Ingests spans, metrics, and logs
│   │   └── anomaly_detector.py  # Sliding-window statistical outlier detector
│   ├── topology/
│   │   ├── graph_builder.py     # Constructs microservices DAG via NetworkX
│   │   ├── causal_tracer.py     # Upstream/downstream causal path isolation
│   │   └── context_distiller.py # Distills mega-traces into compact prompts for Gemma
│   ├── agent/
│   │   ├── coordinator.py       # 4-stage autonomous triage state machine
│   │   ├── prompt_templates.py  # SRE-TriageAgent prompts & JSON schemas
│   │   ├── llm_client.py        # Bridge for WebGPU, Ollama, and OpenAI endpoints
│   │   └── tools/               # Git, Prometheus PromQL, and Jaeger tools
│   ├── sandbox/
│   │   ├── docker_runner.py     # Ephemeral Docker / subprocess runner
│   │   ├── traffic_replayer.py  # Sanitizes sensitive production request payloads
│   │   └── test_validator.py    # Sandbox pytest execution loop
│   └── remediation/
│       ├── patch_generator.py   # Unified git diff synthesizer
│       ├── pr_issuer.py         # Automates branch creation & Draft PR dispatch
│       └── rca_formatter.py     # Formats strict Markdown Post-Mortems
├── web/
│   ├── index.html               # Real-time Web Cockpit UI
│   ├── app.js                   # WebGPU WebLLM runner & WebSocket bridge
│   └── style.css                # Cyber-SRE dark glassmorphic styling
├── tests/
│   ├── fixtures/                # Mock telemetry traces & sample microservice
│   └── unit/                    # Unit tests for all modules
├── docker-compose.infra.yml     # Local Jaeger, Prometheus, OTel Collector
├── pyproject.toml
└── README.md
```

---

## Quick Start

### 1. Installation

```bash
# Clone and navigate to directory
cd c:/ai/zero-noise-sre

# Install dependencies with pip or uv
pip install -e .
```

### 2. Run the Autonomous SRE Web Cockpit

```bash
python cmd/daemon/main.py --port 8000
```
Open **`http://localhost:8000`** in your browser (Google Chrome or Edge recommended for WebGPU support).

### 3. Run a CLI Simulation

To run an autonomous triage simulation directly in your terminal:
```bash
python cmd/daemon/main.py --mock-incident --model-backend mock
```

### 4. Run with Local Ollama Gemma 2B

```bash
# In terminal 1: pull and run Gemma 2B
ollama run gemma2:2b

# In terminal 2: run SRE daemon with Ollama backend
python cmd/daemon/main.py --mock-incident --model-backend ollama
```

### 5. Run Unit & Integration Tests

```bash
pytest -v
```

---

## RCA Post-Mortem Output Format

All generated pull requests include an RCA adhering to the standard production schema:
1. **Summary**: Concise description of incident impact.
2. **Root Cause**: Specific offending line of code and broken invariant.
3. **Evidence**: Trace IDs, error log snippets, and metric anomaly graphs.
4. **Sandbox Validation**: Full test suite output verifying the reproduction test passed.
5. **Preventative Actions**: Concrete recommendations to prevent recurrence.
