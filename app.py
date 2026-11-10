"""app.py: the summarizer as a real web app.

GET / serves the project landing (index.html).
GET /app serves the actual tool (app.html).
POST /api/summarize is the real endpoint: it reads .env server-side
(the key never reaches the browser), rate-limits per IP, caps input
size, and returns three bullets.
"""

import time
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

import summarizer_core as core

BASE_DIR = Path(__file__).parent
MAX_CHARS = 50_000
RATE_LIMIT_REQUESTS = 5
RATE_LIMIT_WINDOW = 3600  # one hour, per IP

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1_048_576  # 1 MB request cap

_request_log: dict[str, list[float]] = {}


def rate_limited(ip: str) -> bool:
    now = time.time()
    recent = [t for t in _request_log.get(ip, []) if now - t < RATE_LIMIT_WINDOW]
    _request_log[ip] = recent
    if len(recent) >= RATE_LIMIT_REQUESTS:
        return True
    _request_log[ip].append(now)
    return False


def load_key_and_config():
    core.load_dotenv()
    provider = core.resolve_provider()
    api_key = core.resolve_api_key(provider)
    return provider, api_key


@app.get("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/app")
def tool():
    return send_from_directory(BASE_DIR, "app.html")


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.errorhandler(413)
def too_large(_exc):
    return jsonify(error="request too large (max 1 MB)."), 413


@app.post("/api/summarize")
def api_summarize():
    ip = request.remote_addr or "unknown"
    if rate_limited(ip):
        return jsonify(
            error=f"rate limit: {RATE_LIMIT_REQUESTS} summaries per hour per user. "
            "Try again later."
        ), 429

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify(error="no text provided. Paste or upload something first."), 400
    if len(text) > MAX_CHARS:
        return jsonify(
            error=f"text too long: {len(text)} characters. The limit is {MAX_CHARS:,}."
        ), 413

    try:
        provider, api_key = load_key_and_config()
    except core.SummarizerError as exc:
        return jsonify(error=str(exc)), 503

    try:
        summary = core.summarize_text(text, provider, api_key)
    except core.SummarizerError as exc:
        return jsonify(error=str(exc)), 502

    bullets = core.to_bullets(summary)
    if not bullets:
        return jsonify(error="the model returned an empty response. Try again."), 502
    return jsonify(
        bullets=bullets,
        provider=provider,
        model=core.os.environ.get("SUMMARIZER_MODEL") or core.DEFAULT_MODELS[provider],
    )


if __name__ == "__main__":
    # Local development: bound to localhost only. For a public deployment,
    # run behind a proper server (e.g. waitress/gunicorn) and set rate
    # limits appropriate to your API quota.
    app.run(host="127.0.0.1", port=8777, debug=False)
