# Verification record

Local verification date: **10 November 2026**. Host: Windows, Python 3.14.5.

## Completed checks

- Application factory and `/healthz` startup.
- Production WSGI factory with an isolated test secret and in-memory database: healthy, production settings active, secure cookies required, debug disabled.
- Fresh virtual environment: installed every pinned requirement successfully, then ran the tests using only those dependencies.
- Full unit/integration suite in that fresh environment: **146 passed**. Tests isolate the developer's environment and `.env`, block external network connections, and mock all Gemini responses. Output is retained in `test-results.txt`.
- Security demonstrations: **19 passed**, including invalid uploads, four cross-user project operations blocked with 403, and 20 failed login attempts with the first 5 normal failures followed by 15 HTTP 429 responses. Output is retained in `security-test-results.txt`.
- `pip check`: no broken requirements.
- Pinned dependency audit: **60 packages**, no known vulnerabilities, JSON retained in `dependency-audit.json`.
- Generated all sample inputs. Valid sample calculations: 70,000.00 estimated; 75,376.00 actual; +5,376.00 variance; +7.68%; exactly one unusual expense, Emergency repairs.
- Browser journey: registration, login, project creation, manual entry, sample CSV upload, results table, two rendered charts, unusual-expense panel, offline summary generation, PDF/CSV downloads, logout.
- Desktop and 390-pixel mobile layout. Fixed chart grid overflow and an absolutely positioned hidden table label; the mobile page's scroll width equals its client width.
- Browser console: no captured warnings or errors in the checked dashboard flow.
- Rendered and visually inspected both pages of a sample ReportLab PDF. Tests also cover long, multipage reports, empty projects, markup-shaped categories, and escaped text.
- Automated project and item deletion, cascade behavior, stale-summary clearing, valid CSV and XLSX, malformed files, row/size/ZIP expansion limits, and all project routes' ownership checks.
- Regression checks preserve an Excel category of `0`, reject control-only categories, accept a literal apostrophe, and verify that a valid multipart upload larger than 500 KB remains in `BytesIO` rather than spooling to disk.
- Production cookie flags were checked on an actual HTTPS test response as well as configuration.
- Git checkpoints recorded in the plan's development sequence. Local `.env` files, databases, virtual environments, large generated samples and QA artifacts are ignored.

Browser verification used a synthetic local account and a 13-item project (one manual entry plus the 12-row sample). Those totals differ appropriately from the sample-only numbers above. Local demo data is ignored by Git and is not a seeded production account.

## Checks requiring another environment or credentials

- **Real Gemini call:** no API key was supplied. Success, exceptions, empty output, oversized output, timeouts/options, privacy bounds, and fallback behavior are covered by mocks; the offline path was verified in the browser. Provide a key and check an available `GEMINI_MODEL` to verify Google end to end.
- **Gunicorn startup:** this native Windows host has no `fcntl`, and WSL is not installed. Gunicorn's Linux startup command and the production factory are prepared; run the README's Gunicorn smoke test on Linux/Render. No operating-system changes were made to enable WSL.
- **Live deployment and HTTPS:** no Render service was created. `render.yaml`, the Python version file, environment instructions, and post-deployment smoke checklist are ready. Confirm HTTPS, HSTS, cookies, persistence expectations, and the full journey after deploying.
- **Course screenshot evidence:** a checklist is included. Local QA screenshots and a PDF were generated in ignored `artifacts/`; deployed/Gemini-key screenshots must be captured when those services are available.
