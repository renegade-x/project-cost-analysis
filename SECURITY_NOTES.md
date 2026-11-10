# Security notes

This is a university Software Quality Engineering prototype. The controls below exist in the code and are exercised by safe automated tests. Run `python -m pytest -v -s tests/test_security.py` for the three required demonstrations and additional evidence. These tests use isolated databases and never call external AI services.

## Implemented controls

| Control | Code location | Test evidence |
| --- | --- | --- |
| Password hashing | `models.User.set_password`, `check_password` use Werkzeug scrypt | `test_models.test_password_is_hashed`; `test_security.test_password_hash_and_generic_login_errors` |
| Registration and login validation | `auth.RegisterForm`, `LoginForm`; username constraints and password length | `test_auth.test_registration_validation`, `test_register_success`, `test_duplicate_username_is_generic` |
| Generic login errors; similar password-check work for unknown users | `auth.login` and `_DUMMY_HASH` | `test_auth.test_login_failure_is_generic`; security password demonstration |
| Session authentication and POST-only logout | `auth.login`, `logout`; Flask-Login on all owned-data routes | `test_auth.test_login_and_logout`, `test_anonymous_and_home_redirect` |
| Ownership / IDOR prevention | `security.get_owned_project_or_403`; every project route calls it; item deletion also filters `project_id` | Parametrized `test_access_control.test_other_user_cannot_access_project` and `test_anonymous_project_access_redirects`; `test_items.test_item_cannot_be_deleted_through_another_project`; IDOR demonstration |
| ORM SQL parameterization | All queries use SQLAlchemy ORM expressions; no concatenated SQL | `test_security.test_sql_injection_strings_cannot_bypass_login_or_break_entry` |
| File extension and content checks | `uploads.parse_upload`; `.csv`/`.xlsx` whitelist, UTF-8/null checks, ZIP signature and workbook parsing | `test_uploads.test_invalid_upload_is_atomic`; invalid-file demonstration |
| Request size and row limits | `config.Config.MAX_CONTENT_LENGTH` = 2 MB; `MAX_UPLOAD_ROWS` = 1,000; bounded stream read | `test_uploads.test_missing_file_and_size`, parametrized invalid import tests; invalid-file demonstration |
| No multipart disk spooling | `uploads.InMemoryUploadRequest._get_file_stream` returns `BytesIO`; configured on the app request class | `test_uploads.test_multipart_uploads_remain_in_memory_above_spooling_threshold` tests a valid file above 500 KB |
| ZIP expansion and safe XLSX parsing | `uploads.parse_upload`: expanded size under 20 MB, read-only/data-only, external links disabled; defusedxml installed | `test_uploads.test_zip_bomb_guard`, `test_errors_capped_and_xlsx_formula_rejected` |
| All-or-nothing import with capped row diagnostics | `uploads._validated_rows`, `projects.upload`; commit only after every row validates | `test_uploads.test_invalid_upload_is_atomic`, `test_errors_capped_and_xlsx_formula_rejected` |
| Finite bounded amounts and category validation | `security.validate_amount`, `validate_category`; shared by forms/imports | `test_items.test_invalid_item_rejected`; invalid-upload parametrization |
| CSV/formula injection protection | `security.sanitize_cell`; applied at entry/import, CSV export, and PDF text boundary | `test_security.test_formula_injection_neutralized_in_database_html_csv_and_pdf` for `=`, `+`, `-`, `@`, tab, CR |
| HTML/XSS escaping | Jinja autoescape; no user `safe` filters; external JS uses `textContent` | `test_items.test_xss_escaped`; `test_security.test_xss_category_is_escaped` |
| PDF markup escaping | `report.safe_text` uses `xml.sax.saxutils.escape` before `Paragraph`; trusted generated numeric cells are escaped separately | `test_report.test_report_source_escapes_and_neutralizes`, `test_pdf_response`; formula demonstration spies on actual Paragraph source |
| CSRF on every POST | `extensions.csrf` initialized globally; forms use `hidden_tag()` or hidden tokens, including logout and deletion | `test_security.test_csrf_missing_token_rejected_and_valid_token_accepted` |
| Safe `next` redirect handling | `auth.safe_next`; relative same-site paths only, including decoded slash/backslash/control rejection | `test_auth.test_open_redirect_rejected`, `test_local_redirect_allowed` |
| Per-route rate limits | `auth`: login 5/min, registration 10/hour; `projects`: upload 10/min, analysis 5/min | `test_security.test_excessive_login_requests_demonstration`, `test_other_sensitive_route_rate_limits` |
| Global rate limit; health exemption | `config.Config.RATELIMIT_DEFAULT` = 200/hour/IP; decorated limits retain defaults; `healthz` exempt | `test_security.test_global_limit_and_health_exemption` |
| CSP and browser response headers | `create_app.security_headers`: self-only scripts/styles, no objects/frames, nosniff, same-origin referrer, disabled camera/mic/location | `test_hardening.test_headers_on_success_error_and_static`; security header demonstration |
| No-store for private data and downloads | `create_app.security_headers`; also authentication and error pages | `test_hardening.test_no_store_and_session_flags`; internal-error test |
| Secure production configuration | `ProductionConfig`, `configure_environment`; required env secret, HttpOnly/SameSite Lax/Secure cookies, two-hour sessions, HSTS, debug off | `test_hardening.test_production_requires_secret`, `test_production_headers_and_cookies` |
| Safe error pages | Factory handlers for 400/403/404/413/429/500, `templates/errors/error.html`; server logging | `test_security.test_internal_error_does_not_leak_stack_trace`; invalid-upload, ownership, CSRF, and rate-limit tests |
| Minimal third-party data | `ai_summary.build_prompt` allow-lists aggregate fields; at most 20 categories with 50-character names; flagged numeric data also comes from full category aggregates | `test_ai_summary.test_prompt_allowlist_and_limits`, `test_anomaly_payload_uses_full_category_aggregate` |
| Prompt separation and safe response handling | `ai_summary.INSTRUCTIONS` marks labels untrusted; separate SDK system instruction; markup stripped, Jinja escaped | `test_ai_summary.test_mocked_gemini_paths` |
| Bounded AI call and fallback | `ai_summary.generate_summary`: 15,000 ms, one attempt, missing-key/exception/empty/oversized fallback, sanitized warning logs | `test_ai_summary.test_no_key_uses_template`, parametrized mocked paths |
| Stale summary invalidation | `Project.clear_summary` called on add, delete and upload | `test_ai_summary.test_summary_route_and_invalidation`, `test_uploads.test_upload_clears_summary`, `test_items.test_item_change_clears_summary` |
| Secret hygiene | Environment config, `.env.example` placeholders, `.gitignore`; no production default secret | Production configuration tests; repository review |
| Dependency hygiene | Pinned direct/transitive requirements, vendored Chart.js version/license, optional `pip-audit` | `pip check`; `docs/dependency-audit.json`; `test_charts.test_vendored_chart_library` |

Dependency audit on **10 November 2026**: `pip check` reported no broken requirements. `pip-audit -r requirements.txt --disable-pip --no-deps` checked **60 pinned packages** and reported **no known vulnerabilities**. The JSON result is retained in `docs/dependency-audit.json`. This is a point-in-time result, not a guarantee against future advisories. Re-run it before deployment.

Code review found no string-built SQL, `|safe` on user data, `innerHTML`, `eval`, subprocess use, hardcoded production secrets, or uploaded files written to disk in `app/`. Generated PDFs/CSVs are built in memory. Source/test examples contain only synthetic credentials and harmless payloads.

## Known limitations and future work

- No email verification, password reset, MFA, or audit log.
- No account lockout beyond per-IP rate limiting; attacks distributed across IPs are outside this prototype's protection.
- In-memory limiter state resets on restart and is not shared between workers. Run one Gunicorn worker. Requests behind a reverse proxy may share its origin IP; only add proxy-header trust after verifying the actual proxy chain. Arbitrary forwarded IP headers are not trusted by this app.
- Render free hosting uses ephemeral storage; SQLite data can reset on restart or redeploy. Move to hosted Postgres and a shared limiter store for durable, multi-worker use.
- No malware/virus scanning. File type, decoding, expansion, row, and value checks reduce parsing risk but do not constitute malware scanning.
- Uploads append to existing data. There is no undo/version history, per-project overall row cap, or background report worker; very large projects are outside the intended small assignment dataset.
- XLSX formula cells without cached values are rejected; formulas are never evaluated. Legacy XLS and password-protected workbooks are unsupported.
- PDF font coverage is limited to ReportLab's built-in fonts; some non-Latin text may require future embedded fonts and shaping support.
- Dependency auditing is manual rather than continuous. Chart.js updates also require deliberate vendoring and review.
- The application removes a `Server` header when present in the Flask response, but the WSGI server or hosting proxy may add its own header after Flask; stripping that requires server/proxy configuration.
- Statistical anomalies are review signals, not proof of error or fraud. Large uniform overruns use the fallback threshold when there is no statistical spread.
- Gemini output can be inaccurate even with aggregate inputs. Review summaries against the actual data. The configured model and free-tier availability depend on Google and the account.
- Live Gemini verification, Linux Gunicorn startup, Render hosting, and HTTPS smoke checks remain deployment-time checks; see `docs/verification.md` for the local evidence and limits.

## Data sent to third parties

When a Gemini key is configured and a user requests a summary, Google receives overall totals, up to 20 category aggregates ranked by absolute variance, flags for those categories, and the count of unusual expenses. Category names are truncated to 50 characters. Project names, usernames, filenames, and raw rows are excluded. Category labels can themselves contain sensitive information; users should choose non-sensitive labels. Without a key, summaries are generated locally.

No browser chart data is sent to a chart service: Chart.js is served locally. The Gemini SDK sends the API key to Google to authenticate the requested analysis; it is never sent to the browser or included in logs. Google and the hosting provider handle requests under their own policies. There is no email, analytics, or advertising integration in the app.
