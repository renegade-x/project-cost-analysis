# Cost Analyzer

A small Flask application for a Software Quality Engineering assignment. Create private projects, enter costs manually or import a CSV/XLSX spreadsheet, compare estimated and actual spending, and download a PDF report or CSV results.

## Features

- Accounts with hashed passwords and private, owned projects.
- Validated manual entry and all-or-nothing, in-memory spreadsheet imports.
- Estimated/actual totals, signed variance, percentage variance, and zero-estimate handling.
- Two locally served Chart.js charts, grouped by category.
- Statistical unusual-expense detection and a Gemini summary with a built-in offline fallback.
- Multipage PDF reports with a chart, full results, unusual expenses, and analysis.
- CSRF protection, request limits, formula neutralization, escaped output, strict security headers, and safe error pages.

This prototype uses one consistent, unspecified currency per project. It does not convert currencies.

## Stack

Python 3.11+ (tested on 3.14.5), Flask, SQLite/Flask-SQLAlchemy, Flask-Login, Flask-WTF, Flask-Limiter, openpyxl, Chart.js 4.4.9, ReportLab, and google-genai. Dependencies are pinned in `requirements.txt`, including transitive packages. pandas is included as required by the development plan; the calculations use Python's decimal and statistics modules.

## Local setup: Windows PowerShell

Run from the repository directory. Activation is optional; these commands use the environment directly.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Paste the generated value into `SECRET_KEY` in `.env`. Leave `GEMINI_API_KEY` empty for the offline demo, or supply your own Google Gemini API key. Then:

```powershell
.\.venv\Scripts\python.exe sample_data\make_sample_data.py
.\.venv\Scripts\python.exe -m flask --app wsgi run
```

Open [the local app](http://127.0.0.1:5000), register an account, sign in, and create a project. Database tables are created automatically in `instance/cost_analyzer.db`. No seeded credentials or real secrets are committed.

## Local setup: Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
# Paste the generated value into SECRET_KEY in .env.
python sample_data/make_sample_data.py
flask --app wsgi run
```

Without a configured development `SECRET_KEY`, the app generates a random value at startup; restarting then invalidates existing sessions and CSRF tokens. Refresh the page and sign in again. Production refuses to start without a configured key.

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | Set to `production` for secure cookies, HSTS, and required secret. |
| `SECRET_KEY` | Random only in development | Flask session/CSRF signing key. Use a generated secret. |
| `DATABASE_URL` | `sqlite:///cost_analyzer.db` | SQLAlchemy database URL; relative SQLite paths use `instance/`. |
| `GEMINI_API_KEY` | Empty | Optional key for Google's API; empty uses the local template. |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Model identifier, overridable if availability changes. |

Production cookies require HTTPS. Use development mode for the local HTTP demo. Never commit `.env`, database files, or API keys.

## Cost data and calculations

Upload `.csv` or `.xlsx` files smaller than 2 MB, with at most 1,000 data rows. CSV must use UTF-8 (a BOM is allowed). Required column names are case-insensitive and surrounding spaces are ignored:

```csv
Category,Estimated,Actual
Materials,100,120
Labour,200,180
```

Extra columns are ignored. Imports append items to the project; they do not replace existing items. Categories must be nonempty and at most 100 characters after sanitizing. Numbers must be finite, nonnegative, and at most 1,000,000,000. Amounts are rounded to two decimal places using decimal half-up rounding.

The custom request class also keeps multipart upload streams in memory; larger files do not spill to a temporary disk file. The 2 MB request limit bounds memory use for each upload.

`Variance = Actual - Estimated`. `% Variance = Variance / Estimated × 100`; zero estimates show `N/A`. Repeated category names are combined in charts and AI requests. Anomalies use a population z-score with an absolute threshold of 2 when at least five percentage values have nonzero spread; otherwise they use a 25% absolute variance threshold. Positive spending without an estimate is always flagged.

XLSX formulas are never evaluated. The reader uses cached values; a formula with no cached value in a required cell is rejected. Formula-shaped text categories are prefixed with an apostrophe. This protective quote can be visible in the UI and exports.

## Sample data

The project dashboard has a fixed **Download sample CSV** link. Its 12 rows total **70,000.00 estimated**, **75,376.00 actual**, and **+5,376.00 variance (+7.68%)**. Exactly one row, **Emergency repairs**, is flagged.

`sample_data/make_sample_data.py` generates valid CSV/XLSX, binary junk disguised as CSV, formula injection examples, an XSS-shaped category, missing columns, and a file larger than 2 MB. Generated XLSX and oversized CSV files are ignored by Git. Use only safe demonstration data.

## Tests and dependency audit

Windows:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest -v -s tests\test_security.py
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip_audit -r requirements.txt --disable-pip --no-deps
```

Linux/macOS: use `python -m pytest ...`, `python -m pip check`, and `python -m pip_audit ...` from the activated environment. `--no-deps` is appropriate here because the requirements file pins all runtime dependencies. Auditing requires internet access; the test suite does not. Every test runs against isolated in-memory SQLite, and a network guard prevents accidental real API calls.

The three required security demonstrations print clear PASS lines for invalid uploads, unauthorized project access, and excessive login requests. See `SECURITY_NOTES.md` for controls and evidence, and `docs/screenshot_checklist.md` for screenshots to capture.

## Render deployment preparation

1. Push this repository to GitHub, then create a Render Blueprint using `render.yaml`.
2. The blueprint selects a free Python web service, installs pinned requirements, runs one Gunicorn worker, generates `SECRET_KEY`, and checks `/healthz`.
3. Set `GEMINI_API_KEY` in Render's dashboard if desired. An empty value keeps the offline fallback. Set `GEMINI_MODEL` to an available model for your key.
4. Confirm `APP_ENV=production`. `.python-version` pins the tested Python version.
5. Open the HTTPS URL and follow the smoke checklist below.

Manual dashboard equivalents:

```text
Build command: pip install -r requirements.txt
Start command: gunicorn wsgi:app --workers 1 --bind 0.0.0.0:$PORT
Health check: /healthz
APP_ENV=production
SECRET_KEY=<generated secret>
GEMINI_API_KEY=<optional private key>
GEMINI_MODEL=gemini-2.5-flash
```

Render free services use an ephemeral filesystem: SQLite data can disappear on restart or redeploy. This is acceptable for the assignment demo. Hosted Postgres and a shared limiter store are future work. Keep **one worker** because the current limiter uses process-local memory.

Gunicorn runs on Unix. It cannot start natively on Windows (`fcntl` is unavailable). Use the Flask local demo commands on Windows, or Linux/WSL for a Gunicorn smoke test. On Linux:

```bash
export APP_ENV=production
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
gunicorn wsgi:app --workers 1 --bind 127.0.0.1:8000
```

`curl http://127.0.0.1:8000/healthz` checks startup. Browser authentication in production mode needs HTTPS, because its cookies are Secure. No live hosting account or Gemini API key is required for local development.

Official references: [Render Flask deployment](https://render.com/docs/deploy-flask), [Blueprint configuration](https://render.com/docs/blueprint-spec), [free-service limitations](https://render.com/docs/free), [Python version selection](https://render.com/docs/python-version), [Gunicorn installation](https://docs.gunicorn.org/en/stable/install.html), and [Google Gen AI SDK](https://googleapis.github.io/python-genai/). Google SDK `HttpOptions.timeout` uses milliseconds; this app sets 15,000 and one attempt.

### Post-deployment smoke checklist

- Open the HTTPS URL and confirm the browser's secure-connection indicator.
- Register, sign in, create a project, and enter a cost manually.
- Upload the sample CSV. Verify the totals and both charts.
- Confirm Emergency repairs is the sole outlier in a sample-only project.
- Generate a summary with and without a key; confirm the displayed source.
- Download and open the PDF and CSV.
- Use two accounts to confirm cross-user access returns 403.
- Inspect CSP, cookie flags, HSTS, and other response headers in the browser Network tools.
- Delete the demo project and sign out.

### Local demo fallback

If hosting is unavailable, use the Windows or Linux/macOS setup commands above with `.env` and `flask --app wsgi run`. The template summary, uploads, charts, and reports work without an AI key or browser CDN access.

## Project structure

```text
app/                 Factory, config, models, routes, security and service modules
app/templates/       Jinja templates
app/static/          Plain CSS/JS and vendored Chart.js + license
tests/               Unit, integration, access-control and security demonstrations
sample_data/         Generator and small safe demonstration inputs
docs/                Screenshot checklist, dependency audit, verification record
wsgi.py              Development/production entry point
render.yaml          Render Blueprint
requirements.txt     Pinned application and test dependencies
requirements-dev.txt Optional dependency auditor
```
