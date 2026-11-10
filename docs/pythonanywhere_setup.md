# PythonAnywhere free deployment

Use the **Beginner ($0)** account. This is the plan's no-card fallback after Render required payment information. Its current limits include one web app/worker, 512 MiB disk, restricted outbound access, and a monthly web-app expiry that must be extended in the dashboard. PythonAnywhere's allowlist includes `.googleapis.com`; verify the real Gemini call from the host after adding the key.

## Account step

Open <https://www.pythonanywhere.com/pricing/>, choose **Create a Beginner account** under **Explore with a limited account**, complete signup and email verification, then sign in. Keep account passwords and API keys private.

## Install the app in a Bash console

The console and Web app must use the same supported Python version. The official Flask instructions currently demonstrate Python 3.13; the exact sequence below uses 3.13. The pinned requirements, test suite, and production Gunicorn startup have passed on Python 3.13 in [Linux CI](https://github.com/renegade-x/project-cost-analysis/actions/runs/42855824036).

```bash
git clone https://github.com/renegade-x/project-cost-analysis.git
cd ~/project-cost-analysis
mkvirtualenv --python=/usr/bin/python3.13 cost-analysis
python -m pip install --no-cache-dir -r requirements.txt
python -m scripts.prepare_pythonanywhere
python -m pip check
```

If this directory or virtualenv already exists, inspect and reuse it; do not clone over an existing app. The preparation helper creates the ignored `.env`, enables production settings, generates a signing secret only if missing, and preserves existing secrets. It prints no secret values. Do not run it against your local development `.env`.

## Configure the Web tab

1. **Web → Add a new web app → Next → Manual configuration**.
2. Choose the same Python version as the virtualenv, e.g. **Python 3.13**.
3. Set **Source code** and **Working directory** to `/home/YOUR_USERNAME/project-cost-analysis`.
4. Set **Virtualenv** to `/home/YOUR_USERNAME/.virtualenvs/cost-analysis`.
5. Open the linked **WSGI configuration file**. Replace its starter contents with the contents of `deployment/pythonanywhere_wsgi.py` from this repository, then save. This template derives your home path automatically.
6. Leave additional static-file mappings empty so Flask continues to attach its security headers to static responses too.
7. Enable **Force HTTPS** if the Web tab offers it, then use **Reload**.
8. Open `https://YOUR_USERNAME.pythonanywhere.com/healthz`. It must return `{"status":"ok"}`.

PythonAnywhere supplies the production WSGI hosting; do not start Flask's development server as the hosted website. The separate GitHub Actions check already verifies Gunicorn on Linux.

## Add Gemini privately

In **Files**, open `/home/YOUR_USERNAME/project-cost-analysis/.env`. Paste the key after `GEMINI_API_KEY=` and save. Keep `APP_ENV=production`. Choose a `GEMINI_MODEL` available to your key and free-tier project. Never place the key in a tracked source file or WSGI template.

For a new Google API account, use `GEMINI_MODEL=gemini-3.5-flash-lite` for the initial live check. Google's current documentation limits the original `gemini-2.5-flash` model to prior users and recommends 3.5 Flash-Lite as its replacement. The replacement has a standard free tier; eligibility and quota still depend on the project. The application's default from the original development plan remains overridable through this environment variable. See [Google's deprecation notice](https://ai.google.dev/gemini-api/docs/deprecations) and [pricing](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.5-flash-lite).

In the existing activated Bash console:

```bash
cd ~/project-cost-analysis
workon cost-analysis
python -m scripts.verify_live_gemini
```

Only `Summary source: gemini` and the explicit PASS line prove a live response. A template fallback is not a passing live check. After editing `.env`, **Reload** the web app so the web worker loads the new configuration.

## Verify and maintain

Use the README's post-deployment checklist: registration/login, manual entry, sample import, two charts, unusual expenses, real/template summaries, PDF/CSV, ownership, logout, HTTPS, cookies, and headers. Use synthetic cost data.

Extend the free web app's expiry from the Web tab before the displayed expiry date. The local SQLite database lives under `instance/` in this account's filesystem. Keep backups if the demo data matters; this prototype has no application-level backup or recovery feature.

Official references: [free account limits](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/), [Flask setup](https://help.pythonanywhere.com/pages/Flask/), [pricing](https://www.pythonanywhere.com/pricing/), [outbound allowlist](https://www.pythonanywhere.com/whitelist/).
