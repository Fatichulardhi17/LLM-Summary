Terminal-Based Text Summarizer
This project teaches you the absolute basics of interacting with an LLM API and handling standard input/output. You will build a Python command-line interface (CLI) tool where a user can pass a large text file, and the LLM returns a concise, formatted summary.

Tools and Technologies Used

Python argparse: For building the command-line interface.
OpenAI API or Google Gemini API: For text generation and summarization.
dotenv: To securely load and manage your private API keys.
How to Make It

Set up a Python script that uses argparse to accept a file path as an execution argument (e.g., python summarize.py document.txt).
Use Python's built-in file handling to read the contents of the target text file into a string variable.
Construct a system prompt instructing the LLM to act as an expert editor, summarizing the provided text into exactly three bullet points.
Send the prompt and the file content to the LLM API, wait for the response, and print the generated summary cleanly to the terminal.

Project Files

 summarize.py: the CLI tool. Parses arguments, reads the file, prints the summary.
 summarizer_core.py: the shared logic (system prompt, provider/key resolution, API call with retry). Both the CLI and the web app run on it.
 app.py: a Flask web app. Serves the pages and a real /api/summarize endpoint that reads .env server-side, so the key never reaches the browser.
 app.html: the web tool page: paste text or load a .txt, get three bullets in the browser.
 index.html: the landing page, including a clearly-labeled simulated terminal demo.
 requirements.txt: the dependencies. Install with pip install -r requirements.txt.
 .env.example: template for your API key. Copy it to .env and fill in one key.
 .gitignore: keeps .env, __pycache__, and virtualenvs out of version control.

Web App

Run it:

 python app.py

Then open http://127.0.0.1:8777 for the landing page and http://127.0.0.1:8777/app for the real tool.

How it stays safe:

 the API key lives in .env on the server and is never sent to the browser.
 input is capped at 50,000 characters and requests at 1 MB.
 each IP gets 5 summaries per hour, so a public deployment cannot burn the key's quota.
 the dev server binds to 127.0.0.1 only. For public use, run it behind a production WSGI server (gunicorn, waitress).

The endpoint:

 POST /api/summarize with {"text": "..."} JSON. Returns {"bullets": [...], "provider": "...", "model": "..."}.

Usage

 1. Install dependencies: pip install -r requirements.txt
 2. Copy .env.example to .env and set one key:
    - OpenAI: OPENAI_API_KEY=your-key-here
    - Google Gemini: GEMINI_API_KEY=your-key-here and LLM_PROVIDER=gemini
 3. Run it: python summarize.py document.txt

Options

 --provider openai|gemini: choose the API. Defaults to the LLM_PROVIDER env var, or openai.
 --model NAME: choose the model. Defaults to the SUMMARIZER_MODEL env var, or a per-provider default (gpt-4o-mini, gemini-3.5-flash).

Error Meaning

 file not found: the path is wrong. Check it and run again.
 contains no text: the file is empty, so there is nothing to summarize.
 no API key set: create a .env file with the missing key.
 request failed: the API rejected the call (invalid key, quota, or network). The message shows the cause.

Status

Verified on Python 3.14: argument parsing, file validation (missing, empty, UTF-16 BOM encoding), missing key handling, and the API error path were all tested. A successful end-to-end summary requires one real API key in .env.