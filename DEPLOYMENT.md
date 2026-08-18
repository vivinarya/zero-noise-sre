# 1-Click Cloud Deployment Guide for Razorpay Showcase

This guide allows you to deploy **Zero-Noise SRE Core** to free cloud hosting in under 2 minutes, giving you a working public URL (e.g. `https://zero-noise-sre.onrender.com` or `https://zero-noise-sre.up.railway.app`) ready to share with Razorpay engineers and hiring teams.

---

## Option 1: Render.com (Recommended Free Hosting)

1. Push this repository to GitHub (or use your existing repository).
2. Go to [dashboard.render.com](https://dashboard.render.com/) and click **New +** -> **Web Service**.
3. Connect your GitHub repository.
4. Render will automatically detect [`render.yaml`](file:///c:/ai/zero-noise-sre/render.yaml) or you can set:
   - **Environment**: `Python`
   - **Build Command**: `pip install -e .`
   - **Start Command**: `python cmd/daemon/main.py --port $PORT`
   - **Plan**: `Free`
5. Click **Deploy Web Service**.
6. In ~60 seconds, Render will provide a public link like `https://zero-noise-sre-xxxx.onrender.com`.

---

## Option 2: Railway.app (Fast 1-Click Deploy)

1. Go to [railway.app](https://railway.app/) and click **New Project** -> **Deploy from GitHub repo**.
2. Select your repository.
3. Railway will automatically build using the included [`Dockerfile`](file:///c:/ai/zero-noise-sre/Dockerfile).
4. Under **Settings** -> **Networking**, click **Generate Domain**.
5. You will get a live URL: `https://zero-noise-sre-production.up.railway.app`.

---

## Option 3: Hugging Face Spaces (Free Cloud GPU/CPU Web App)

1. Go to [huggingface.co/spaces](https://huggingface.co/spaces) and click **Create new Space**.
2. Select **Space SDK** -> **Docker** (Blank).
3. Clone the Space repo or push this codebase to the Space repository.
4. Hugging Face will build the Docker container and host it publicly with WebGPU hardware support for in-browser Gemma models!

---

## Option 4: Run Locally with ngrok / Localtunnel (Instant Link in 10s)

If you want an instant live public link directly from your laptop without deploying to the cloud:

```bash
# Terminal 1: Start Zero-Noise SRE Daemon
python cmd/daemon/main.py --port 8000

# Terminal 2: Expose to a secure public HTTPS link via ngrok or localtunnel
npx localtunnel --port 8000
# OR
ngrok http 8000
```
This generates an instant public URL: `https://your-sre-demo.loca.lt` that anyone at Razorpay can immediately open in their browser!

---

## Razorpay Showcase Highlights

When sharing the link with Razorpay reviewers, point them to:
1. **Interactive In-Browser Gemma 2B Inference**: Select **Browser WebGPU (Gemma 2B In-Window)** to demonstrate client-side LLM inference with 0 server GPU cost.
2. **FinTech Scenarios**: Choose **Razorpay Payment Capture (Null Currency)** or **Razorpay Webhook (HMAC Signature Error)** to simulate real-world payment reliability failures.
3. **Automated 4-Stage SRE Loop**: Click **Simulate Production Incident** to watch real-time DAG topology traversal, context distillation, sandbox pytest reproduction, unified git diff synthesis, and production-grade RCA generation.
