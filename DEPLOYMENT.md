# 100% Free Deployment Guide (No Credit Card Required)

Your repository is live at [https://github.com/vivinarya/zero-noise-sre](https://github.com/vivinarya/zero-noise-sre). Here are the top **100% free** platforms to host your Zero-Noise SRE live demo with a public link to share with Razorpay.

---

## 1. Render.com (Recommended Free Cloud Host)
*No credit card required. Free tier includes 750 free hours/month.*

1. Go to **[dashboard.render.com](https://dashboard.render.com/)** and sign in with your GitHub account.
2. Click **New +** -> **Web Service**.
3. Select your repository: `vivinarya/zero-noise-sre`.
4. Configure:
   - **Name**: `zero-noise-sre`
   - **Language**: `Python`
   - **Build Command**: `pip install -e .`
   - **Start Command**: `python cmd/daemon/main.py --port $PORT`
   - **Instance Type**: `Free`
5. Click **Create Web Service**.
6. In ~60 seconds, you get a live public link:  
   `https://zero-noise-sre.onrender.com`

---

## 2. Hugging Face Spaces (Free Cloud Hosting + WebGPU Support)
*No credit card required. Free CPU container, perfect for AI / WebGPU demos.*

1. Go to **[huggingface.co/spaces](https://huggingface.co/spaces)** and click **Create new Space**.
2. Space Name: `zero-noise-sre`
3. License: `mit`
4. Space SDK: Select **Docker** -> **Blank**.
5. Hardware: **CPU Basic (Free)**.
6. Click **Create Space**.
7. In the Space settings, connect your GitHub repository `vivinarya/zero-noise-sre` or push your code.
8. It will automatically build from the `Dockerfile` and give you:  
   `https://huggingface.co/spaces/YOUR_USERNAME/zero-noise-sre`

---

## 3. Koyeb (100% Free Nano Service)
*No credit card required for standard free hobby tier.*

1. Sign up at **[koyeb.com](https://www.koyeb.com/)** with GitHub.
2. Click **Create App** -> Select **GitHub**.
3. Choose `vivinarya/zero-noise-sre`.
4. Koyeb will automatically detect the `Dockerfile`.
5. Select the **Free** instance type.
6. Click **Deploy** to get a public URL like:  
   `https://zero-noise-sre-YOUR_NAME.koyeb.app`

---

## 4. Cloudflare Tunnel / Localtunnel (Instant Live Link in 5 Seconds)
*Free, zero cloud accounts required, runs directly from your laptop.*

### Using Cloudflare (Ultra-fast, high reliability):
```bash
# Terminal 1: Run SRE Core
python cmd/daemon/main.py --port 8000

# Terminal 2: Start Cloudflare Tunnel (free, no sign-up)
npx cloudflared tunnel --url http://localhost:8000
```
It gives you an instant HTTPS link like `https://random-subdomain.trycloudflare.com` that you can immediately send to Razorpay!

### Using Localtunnel:
```bash
npx localtunnel --port 8000
```

---

## Razorpay Showcase Checklist

When sharing the link:
1. **In-Browser WebGPU**: Point out that selecting *Browser WebGPU (Gemma 2B In-Window)* executes edge AI reasoning directly in the visitor's browser tab.
2. **FinTech Scenarios**: Highlight the *Razorpay Payment Capture* and *Razorpay Webhook* options demonstrating real-world payment incident resolution.
3. **Automated RCA**: Trigger the simulation to show the autonomous 4-stage pipeline producing a verified fix and Post-Mortem.
