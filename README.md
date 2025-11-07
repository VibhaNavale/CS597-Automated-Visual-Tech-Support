# Automated Visual Tech Support

This project ingests short mobile tutorials from YouTube, runs OS-Atlas Pro 7B to extract step-by-step actions, and serves an accessible React interface that helps users generate visual guides and verify bounding boxes. The goal is to automate mobile tech support while preserving manual review hooks for research metrics.

## Requirements

- Python 3.10 or newer
- Node.js 18+
- CUDA-capable GPU (tested with NVIDIA V100 32 GB)
- `ffmpeg`, `yt-dlp`, and other tools listed in `requirements.txt` and `frontend/package.json`

## Quick Start

```bash
# Backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 4000 --reload

# Frontend
cd frontend
npm install
npm run dev
```

Adjust `.env` files for API keys (YouTube Data API) or remote endpoints as needed. By default the backend listens on `http://localhost:4000` and the frontend dev server on `http://localhost:3000`.

## Metrics and Testing

- Generated performance JSON files: `Metrics/Performance/`
- Manual accuracy JSON files: `Metrics/Accuracy/`
- Full methodology, results, and report figures: `Report.txt`

In the frontend, enable **Test Mode** to label step quality, verify bounding boxes, and persist metrics for analysis.

