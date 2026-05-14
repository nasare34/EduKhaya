# Deploying EduAI Ghana to Render (Free Tier)

## What gets deployed
Two free web services — no database purchase needed:
- **eduai-api** — FastAPI AI backend (port auto-assigned by Render)
- **eduai-app** — Flask frontend (port auto-assigned by Render)

SQLite and ChromaDB use `/tmp` (free, resets on redeploy).

---

## Step 1 — Push to GitHub
```bash
cd eduai
git init
git add .
git commit -m "Initial EduAI Ghana"
# Create a repo on github.com then:
git remote add origin https://github.com/YOUR_USERNAME/eduai-ghana.git
git push -u origin main
```

## Step 2 — Deploy on Render

1. Go to **https://render.com** → New → **Blueprint**
2. Connect your GitHub repo
3. Render detects `render.yaml` automatically and creates both services

## Step 3 — Set environment variables

In Render dashboard → **eduai-api** → Environment, add:

| Key | Value |
|-----|-------|
| `GROQ_API_KEY` | `gsk_...` |
| `KHAYA_TRANSLATE_KEY` | your key |
| `KHAYA_TTS_KEY` | your key |
| `ANTHROPIC_API_KEY` | (optional) |
| `OPENAI_API_KEY` | (optional) |
| `GEMINI_API_KEY` | (optional) |

In Render dashboard → **eduai-app** → Environment, update:

| Key | Value |
|-----|-------|
| `FASTAPI_URL` | `https://eduai-api.onrender.com` ← copy the actual URL from eduai-api service |

## Step 4 — Update FASTAPI_URL

After eduai-api deploys, copy its URL (e.g. `https://eduai-api-xyz.onrender.com`) and:
1. Go to eduai-app → Environment
2. Set `FASTAPI_URL` to that URL
3. Click **Save** → eduai-app redeploys automatically

## Important: Free Tier Limitations

| Limitation | Impact |
|------------|--------|
| Services sleep after 15 min inactivity | First request takes ~30s to wake up |
| `/tmp` is ephemeral | Uploaded documents and DB reset on redeploy |
| 512MB RAM per service | Large PDFs may be slow |
| No persistent disk (free) | Use paid Render disk ($0.25/GB/month) for persistence |

## To add a persistent disk later (optional, $0.25/GB/month)

In `render.yaml`, uncomment under each service:
```yaml
    disk:
      name: eduai-data
      mountPath: /data
      sizeGB: 1
```
Then change env vars:
- `DATABASE_URL`: `sqlite:////data/eduai.db`
- `CHROMA_PERSIST_DIR`: `/data/chroma_db`
- `UPLOAD_FOLDER`: `/data/uploads`
- `AUDIO_FOLDER`: `/data/audio`

## CORS — allow Flask to call FastAPI

Already configured in `fastapi_app/main.py`. When deployed, also add your
Flask URL to the `allow_origins` list in `main.py`:

```python
allow_origins=[
    "http://127.0.0.1:5000",
    "http://localhost:5000",
    "https://eduai-app.onrender.com",   # ← add your Flask Render URL
],
```
