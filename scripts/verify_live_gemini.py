"""Run from the repo: python -m scripts.verify_live_gemini.

Makes one real summary request using synthetic category aggregates. Reads secrets
from the environment/.env and never prints them or accesses the project's database.
"""
import os
from types import SimpleNamespace

from dotenv import load_dotenv
from flask import Flask

from app.ai_summary import generate_summary


def main() -> int:
    load_dotenv()
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        print("GEMINI_API_KEY is missing. Add it privately to .env, then rerun this command.")
        return 2
    application = Flask(__name__)
    application.config.update(
        GEMINI_API_KEY=key,
        GEMINI_MODEL=os.getenv("GEMINI_MODEL") or "gemini-2.5-flash",
    )
    project = SimpleNamespace(items=[
        dict(category="Materials", estimated=100, actual=120),
        dict(category="Labour", estimated=200, actual=180),
        dict(category="Transport", estimated=50, actual=90),
    ])
    with application.app_context():
        summary, source = generate_summary(project)
    print(f"Summary source: {source}")
    if source != "gemini":
        print("Live verification did not pass: the app used its safe template fallback.")
        print("Check the key, the selected model, and the project's free-tier quota in Google AI Studio.")
        return 1
    print("PASS: a real Gemini response was accepted using synthetic aggregates only.")
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
