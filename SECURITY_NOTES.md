# Security notes

This is a university prototype. Controls and their test evidence are documented here; the final verification record will be added after the full security demonstrations.

## Implemented controls

The application uses password hashing, owned project lookups, bounded in-memory uploads, CSRF-protected forms, Jinja escaping, formula-safe text, request limits, strict response headers, production cookie flags, and aggregate-only AI requests. See `tests/` for automated evidence.

## Known limitations and future work

SQLite and the in-memory limiter are intended for a single-process prototype. Render free hosting has ephemeral storage. No email verification, password reset, MFA, malware scanning, or audit log is implemented. PDF font coverage is limited to the built-in ReportLab fonts. Dependency auditing is manual rather than continuous.

## Data sent to third parties

When a Gemini key is configured and a user requests a summary, Google receives overall totals, up to 20 category aggregates ranked by absolute variance, flags for those categories, and the count of unusual expenses. Category names are truncated to 50 characters. Project names, usernames, filenames, and raw rows are excluded. Category labels can themselves contain sensitive information; users should choose non-sensitive labels. Without a key, summaries are generated locally.
