"""summarize.py: Terminal-Based Text Summarizer (CLI)

Reads a text file, sends it to an LLM with one strict instruction,
and prints a three-bullet-point summary.

Usage:
    python summarize.py document.txt
    python summarize.py document.txt --provider gemini
    python summarize.py document.txt --model your-model-name

The shared logic lives in summarizer_core.py, so the CLI and the web
app (app.py) always summarize exactly the same way.
"""

import argparse
import sys
from pathlib import Path

from summarizer_core import (
    DEFAULT_MODELS,
    KEY_NAMES,
    SummarizerError,
    resolve_api_key,
    resolve_provider,
    summarize_text,
    to_bullets,
)

try:
    from dotenv import load_dotenv
except ImportError:
    print("Missing dependency: run 'pip install python-dotenv openai'", file=sys.stderr)
    sys.exit(1)


def fail(message: str) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


def read_text_file(path: Path) -> str:
    if not path.exists():
        fail(f"file not found: {path}. Check the path and try again.")
    if not path.is_file():
        fail(f"not a regular file: {path}")
    try:
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            text = raw.decode("utf-8-sig")
        elif raw.startswith((b"\xff\xfe", b"\xfe\xff")):
            try:
                text = raw.decode("utf-16")
            except UnicodeDecodeError as exc:
                fail(f"{path.name} is not valid UTF-16 despite a UTF-16 BOM: {exc}")
        else:
            text = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        fail(
            f"could not read {path} as UTF-8 text: {exc}. "
            "If the file uses another encoding, convert it first (e.g. save as UTF-8)."
        )
    if not text.strip():
        fail(f"{path.name} contains no text. There is nothing to summarize.")
    return text


def print_summary(summary: str) -> None:
    bullets = to_bullets(summary)
    for line in bullets:
        print(line)
    if len(bullets) != 3:
        print(
            f"note: the model returned {len(bullets)} bullet(s), expected 3. "
            "Re-run if you need exactly three.",
            file=sys.stderr,
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="summarize.py",
        description="Summarize a text file into exactly three bullet points using an LLM.",
    )
    parser.add_argument("file", help="path to the text file to summarize")
    parser.add_argument(
        "--provider",
        choices=["openai", "gemini"],
        default=None,
        help="LLM provider. Defaults to the LLM_PROVIDER env var, or 'openai'.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="model name. Defaults to SUMMARIZER_MODEL env var, or a per-provider default.",
    )
    args = parser.parse_args()

    text = read_text_file(Path(args.file))

    try:
        load_dotenv()
        provider = resolve_provider(args.provider)
        api_key = resolve_api_key(provider)
        model = args.model
        print(f"reading done. sending to {provider} ...", file=sys.stderr)
        summary = summarize_text(text, provider, api_key, model)
    except SummarizerError as exc:
        fail(str(exc))

    if not summary:
        fail("the model returned an empty response. Try again.")
    print_summary(summary)


if __name__ == "__main__":
    main()
