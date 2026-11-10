"""Shared core for the summarizer: used by summarize.py (CLI) and app.py (web).

One source of truth for the system prompt, provider/key resolution,
and the API call with retry on transient errors.
"""

import os
import time

try:
    from dotenv import load_dotenv
except ImportError:
    raise SystemExit("Missing dependency: run 'pip install python-dotenv openai'")

SYSTEM_PROMPT = (
    "You are an expert editor. Summarize the provided text into exactly "
    "three bullet points. Each bullet is one short, complete sentence "
    "starting with '- '. Output only the three bullets, nothing else."
)

DEFAULT_MODELS = {"openai": "gpt-4o-mini", "gemini": "gemini-3.5-flash"}
KEY_NAMES = {"openai": "OPENAI_API_KEY", "gemini": "GEMINI_API_KEY"}


class SummarizerError(Exception):
    """An error worth showing to the user as-is (no stack, no secret)."""


def resolve_provider(provider_arg=None) -> str:
    provider = (provider_arg or os.environ.get("LLM_PROVIDER", "openai")).lower()
    if provider not in ("openai", "gemini"):
        raise SummarizerError(
            f"unknown provider '{provider}'. Use 'openai' or 'gemini'."
        )
    return provider


def resolve_api_key(provider: str) -> str:
    key = os.environ.get(KEY_NAMES[provider], "").strip()
    if not key:
        raise SummarizerError(
            f"no API key set. Create a .env file with "
            f"{KEY_NAMES[provider]}=your-key-here (dotenv loads it automatically)."
        )
    return key


def request_summary_openai(text: str, model: str, api_key: str) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        raise SummarizerError("Missing dependency: run 'pip install openai'")
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        temperature=0.3,
    )
    return (response.choices[0].message.content or "").strip()


def request_summary_gemini(text: str, model: str, api_key: str) -> str:
    try:
        from google import genai
    except ImportError:
        raise SummarizerError("Missing dependency: run 'pip install google-genai'")
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=model,
        contents=f"{SYSTEM_PROMPT}\n\nText to summarize:\n{text}",
    )
    return (response.text or "").strip()


def summarize_text(
    text: str,
    provider: str,
    api_key: str,
    model: str = None,
    attempts: int = None,
) -> str:
    """Send text to the provider and return the raw summary.

    Retries transient errors (503 overloaded, 429 rate limit): those are
    usually gone seconds later, and a retry is cheaper than a failed run.
    Raises SummarizerError with a user-facing message otherwise.
    """
    if model is None:
        model = os.environ.get("SUMMARIZER_MODEL", DEFAULT_MODELS[provider])
    if attempts is None:
        attempts = int(os.environ.get("SUMMARIZER_RETRIES", "3"))

    request = (
        (lambda: request_summary_openai(text, model, api_key))
        if provider == "openai"
        else (lambda: request_summary_gemini(text, model, api_key))
    )

    for attempt in range(1, attempts + 1):
        try:
            summary = request()
            break
        except KeyboardInterrupt:
            raise SummarizerError("cancelled.")
        except SummarizerError:
            raise
        except Exception as exc:
            message = str(exc)
            transient = any(
                s in message
                for s in ("503", "429", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "overloaded")
            )
            if not transient or attempt == attempts:
                raise SummarizerError(f"{provider} request failed: {message}")
            if attempt < attempts:
                time.sleep(2 ** attempt)

    try:
        return summary  # type: ignore[name-defined]
    except UnboundLocalError:
        raise SummarizerError("the request never completed. Try again later.")


def to_bullets(summary: str) -> list[str]:
    """Split a summary into bullet lines, normalizing the leading marker."""
    lines = [line.strip() for line in summary.splitlines() if line.strip()]
    return [
        line if line.startswith(("-", "*", "\u2022")) else f"- {line}"
        for line in lines
    ]
