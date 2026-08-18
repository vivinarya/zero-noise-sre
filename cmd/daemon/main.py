"""Zero-Noise SRE Daemon and Web Cockpit entrypoint."""

import os
import sys
import json
import time
import asyncio
import argparse
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
import uvicorn
from rich.console import Console
from rich.panel import Panel

# Add repo root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

try:
    from src.ingestion.otel_receiver import OTelReceiver, SpanData, MetricSample
    from src.ingestion.anomaly_detector import AnomalyDetector, SLOThresholds, IncidentPayload
    from src.agent.coordinator import SRECoordinator, TriageState
    from src.agent.llm_client import LLMClient
except ImportError:
    from ingestion.otel_receiver import OTelReceiver, SpanData, MetricSample
    from ingestion.anomaly_detector import AnomalyDetector, SLOThresholds, IncidentPayload
    from agent.coordinator import SRECoordinator, TriageState
    from agent.llm_client import LLMClient

# Ensure stdout handles unicode cleanly
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

console = Console(force_terminal=True, highlight=False)

app = FastAPI(title="Zero-Noise SRE Core")

# Mount web assets
web_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../web"))
if os.path.exists(web_dir):
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

# Shared state
receiver = OTelReceiver()
thresholds = SLOThresholds(latency_p99_ms=800.0, error_rate_percent=2.0, sliding_window_seconds=60.0, min_sample_count=1)
detector = AnomalyDetector(receiver, thresholds)
active_websockets: List[WebSocket] = []
browser_inference_queue = asyncio.Queue()


async def broadcast_ws(message: Dict[str, Any]):
    for ws in active_websockets:
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            pass


@app.get("/")
async def get_index():
    index_file = os.path.join(web_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h1>Zero-Noise SRE Daemon Running</h1>")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_websockets.append(websocket)
    try:
        while True:
            data_text = await websocket.receive_text()
            data = json.loads(data_text)
            if data.get("type") == "INFERENCE_RESPONSE":
                if not browser_inference_queue.empty():
                    item = await browser_inference_queue.get()
                    item["future"].set_result(data.get("text", ""))
    except WebSocketDisconnect:
        if websocket in active_websockets:
            active_websockets.remove(websocket)


@app.get("/healthz")
@app.get("/api/health")
async def health_check():
    return {"status": "HEALTHY", "service": "zero-noise-sre-core", "version": "0.1.0"}


@app.get("/api/scenarios")
async def get_scenarios():
    return [
        {
            "id": "razorpay_payment_capture",
            "name": "Razorpay Payment Capture (Null Currency Invariant)",
            "service": "payment-service",
            "endpoint": "POST /v1/payments/{id}/capture"
        },
        {
            "id": "razorpay_webhook_hmac",
            "name": "Razorpay Webhook Dispatch (HMAC Verification Exception)",
            "service": "webhook-service",
            "endpoint": "POST /v1/webhooks/razorpay"
        }
    ]


@app.post("/api/trigger-incident")
async def trigger_incident_endpoint(payload: Dict[str, Any] = {}):
    backend = payload.get("backend", "mock")
    scenario = payload.get("scenario", "razorpay_payment_capture")
    incident = generate_mock_spans_and_incident(receiver, scenario=scenario)

    # Broadcast telemetry update showing breach
    await broadcast_ws({
        "type": "TELEMETRY_UPDATE",
        "data": {
            "p99_ms": incident.observed_p99_ms,
            "error_rate": incident.observed_error_rate_pct,
            "status": "BREACH"
        }
    })

    # Run triage in background task
    asyncio.create_task(run_triage_flow(incident, backend=backend))
    return {"status": "TRIGGERED", "incident_id": incident.incident_id, "scenario": scenario}


def generate_mock_spans_and_incident(rcv: OTelReceiver, scenario: str = "razorpay_payment_capture") -> IncidentPayload:
    """Populates realistic distributed traces with a failing payment-service or webhook service."""
    trace_id = f"trc-{int(time.time())}"
    now_ns = int(time.time() * 1e9)

    if scenario == "razorpay_webhook_hmac":
        s1 = SpanData(
            trace_id=trace_id,
            span_id="span-fe-01",
            service_name="api-gateway",
            operation_name="POST /v1/webhooks/razorpay",
            start_time_ns=now_ns,
            duration_ms=950.0,
            status_code="ERROR",
            http_status_code=500,
            attributes={"http.route": "/v1/webhooks/razorpay", "provider": "razorpay"}
        )
        rcv.record_span(s1)

        s2 = SpanData(
            trace_id=trace_id,
            span_id="span-wh-02",
            parent_span_id="span-fe-01",
            service_name="webhook-service",
            operation_name="verify_and_dispatch",
            start_time_ns=now_ns + 10_000_000,
            duration_ms=920.0,
            status_code="ERROR",
            http_status_code=500,
            error_message="TypeError: hmac.new() argument 1 must be bytes or bytearray, not NoneType",
            attributes={"razorpay.event": "payment.authorized", "x-razorpay-signature": None},
            events=[{
                "name": "exception",
                "attributes": {
                    "exception.type": "TypeError",
                    "exception.message": "hmac.new() argument 1 must be bytes or bytearray, not NoneType",
                    "exception.stacktrace": "File 'webhook_service/verifier.py', line 12, in verify_signature\n    computed = hmac.new(secret, payload, hashlib.sha256).hexdigest()\nTypeError: hmac.new() argument 1 must be bytes"
                }
            }]
        )
        rcv.record_span(s2)

        return IncidentPayload(
            incident_id=f"INC-{int(time.time())}-razorpay-webhook",
            service_name="webhook-service",
            trigger_reason="Webhook 5xx error rate 12.8% > 2.0% SLO & p99 920ms > 800ms",
            observed_p99_ms=920.0,
            observed_error_rate_pct=12.8,
            failing_trace_ids=[trace_id],
            sample_spans=[s1, s2],
            metadata={"cause": "Razorpay webhook HMAC secret missing or null byte validation"}
        )

    # Default: Razorpay Payment Capture Scenario
    s1 = SpanData(
        trace_id=trace_id,
        span_id="span-fe-01",
        service_name="frontend-gateway",
        operation_name="POST /v1/checkout/razorpay",
        start_time_ns=now_ns,
        duration_ms=1250.0,
        status_code="ERROR",
        http_status_code=500,
        attributes={"http.route": "/v1/checkout/razorpay", "user.tier": "enterprise", "gateway": "razorpay"}
    )
    rcv.record_span(s1)

    s2 = SpanData(
        trace_id=trace_id,
        span_id="span-co-02",
        parent_span_id="span-fe-01",
        service_name="checkout-service",
        operation_name="process_order",
        start_time_ns=now_ns + 10_000_000,
        duration_ms=1200.0,
        status_code="ERROR",
        http_status_code=500,
        attributes={"order.id": "order_rzp_99882", "currency": None}
    )
    rcv.record_span(s2)

    s3 = SpanData(
        trace_id=trace_id,
        span_id="span-pm-03",
        parent_span_id="span-co-02",
        service_name="payment-service",
        operation_name="charge_payment",
        start_time_ns=now_ns + 20_000_000,
        duration_ms=1150.0,
        status_code="ERROR",
        http_status_code=500,
        error_message="AttributeError: 'NoneType' object has no attribute 'upper' at app.py:18",
        attributes={"http.target": "/charge", "currency": None, "amount": 100.0, "provider": "razorpay"},
        events=[{
            "name": "exception",
            "attributes": {
                "exception.type": "AttributeError",
                "exception.message": "'NoneType' object has no attribute 'upper'",
                "exception.stacktrace": "File 'payment_service/app.py', line 18, in charge_payment\n    curr = req.currency.upper()\nAttributeError: 'NoneType' object has no attribute 'upper'"
            }
        }]
    )
    rcv.record_span(s3)

    return IncidentPayload(
        incident_id=f"INC-{int(time.time())}-razorpay-payment",
        service_name="payment-service",
        trigger_reason="Razorpay Payment 5xx error rate 15.4% > 2.0% SLO & p99 1150ms > 800ms",
        observed_p99_ms=1150.0,
        observed_error_rate_pct=15.4,
        failing_trace_ids=[trace_id],
        sample_spans=[s1, s2, s3],
        metadata={"cause": "Razorpay unhandled null currency (default INR missing)"}
    )


async def run_triage_flow(incident: IncidentPayload, backend: str = "mock") -> TriageState:
    console.print(Panel(f"[bold red][ALERT] DETECTED SLO ANOMALY on {incident.service_name}[/bold red]\n{incident.trigger_reason}", title="ZERO-NOISE SRE CORE"))

    llm_client = LLMClient(backend=backend, ws_browser_queue=browser_inference_queue)
    fixtures_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../tests/fixtures"))
    coordinator = SRECoordinator(llm_client=llm_client, service_repo_base=fixtures_dir)

    await broadcast_ws({"type": "PIPELINE_UPDATE", "stage": "STAGE_1_TOPOLOGY_ISOLATION", "logs": ["[STAGE 1] Isolating culprit in topology DAG..."]})
    await asyncio.sleep(0.5)

    await broadcast_ws({"type": "PIPELINE_UPDATE", "stage": "STAGE_2_CAUSAL_CORRELATION", "logs": ["[STAGE 2] Distilling context for Gemma reasoning..."]})
    await asyncio.sleep(0.5)

    await broadcast_ws({"type": "PIPELINE_UPDATE", "stage": "STAGE_3_SANDBOX_SYNTHESIS", "logs": ["[STAGE 3] Synthesizing patch and running sandbox verification..."]})

    state = await coordinator.execute_triage(incident)

    await broadcast_ws({"type": "PIPELINE_UPDATE", "stage": "RESOLVED", "logs": state.logs})

    if state.pr_result and state.rca:
        await broadcast_ws({
            "type": "PR_DISPATCHED",
            "pr_url": state.pr_result.pr_url,
            "pr_title": state.pr_result.pr_title,
            "branch_name": state.pr_result.branch_name,
            "rca_markdown": state.rca.markdown_report,
            "diff_text": state.unified_patch.diff_text if state.unified_patch else "",
            "test_code": state.reproduction_test or ""
        })

    console.print(Panel(f"[bold green][SUCCESS] INCIDENT RESOLVED & VERIFIED[/bold green]\nPR: {state.pr_result.pr_url if state.pr_result else 'N/A'}", title="RCA Post-Mortem Dispatched"))
    return state


async def main_cli():
    parser = argparse.ArgumentParser(description="Zero-Noise SRE Daemon")
    parser.add_argument("--mock-incident", action="store_true", help="Trigger a mock incident immediately")
    parser.add_argument("--model-backend", type=str, default="mock", choices=["mock", "ollama", "browser_webgpu", "openai_compatible"], help="LLM inference backend")
    parser.add_argument("--port", type=int, default=8000, help="Web Cockpit port")
    args = parser.parse_args()

    if args.mock_incident:
        incident = generate_mock_spans_and_incident(receiver)
        await run_triage_flow(incident, backend=args.model_backend)
    else:
        port = int(os.environ.get("PORT", args.port))
        config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
        server = uvicorn.Server(config)
        console.print(f"[bold cyan]Zero-Noise SRE Cockpit online at http://localhost:{port}[/bold cyan]")
        await server.serve()


if __name__ == "__main__":
    asyncio.run(main_cli())
