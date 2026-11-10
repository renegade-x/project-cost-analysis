# Screenshot checklist

Use synthetic data only. Start the local app using the README. Create two demo accounts for ownership checks. Never show `.env`, API keys, session cookie values, or real private cost data.

1. Registration form, including password length guidance.
2. Login form and a generic wrong-credentials message.
3. Project list showing only the current user's projects.
4. Empty project with manual-entry and upload forms.
5. Manual cost entry with one overspend and one saving.
6. Results table with estimated, actual, signed variance, percentage, status, and total.
7. Successful upload of the 12-row sample CSV into an otherwise empty project.
8. Both charts: Estimated vs actual and Variance by category.
9. Unusual expenses panel with Emergency repairs flagged exactly once for sample-only data.
10. Built-in template summary with its source and generation time, using no Gemini key.
11. Gemini summary with source and time, when a real key is available. Set the key privately, restart, sign in again, and generate; never screenshot the key. A fallback label means Google did not produce an accepted response.
12. Opened PDF showing totals and the complete results table.
13. PDF chart, unusual expenses, AI summary, and page-number footer.
14. CSV export with a formula-shaped category visibly prefixed by an apostrophe.
15. `python -m pytest -v -s tests/test_security.py` output: invalid-file demonstration PASS line.
16. Same output: unauthorized project-access/IDOR demonstration PASS line.
17. Same output: excessive-login demonstration, first 5 normal failures then 15 HTTP 429 responses.
18. Browser 403 page: sign in as user B and open user A's known project URL.
19. Browser 429 page: trigger the limit using synthetic login attempts; avoid doing this immediately before recording the normal login flow.
20. Rejected fake upload message; also show 413 for the generated oversized file.
21. Browser Network response headers: CSP, nosniff, frame denial, referrer policy, permissions policy, and no-store on private responses. Do not reveal cookie values.
22. Small-screen dashboard, with stacked cards and the results table scrolling inside its container.
23. Deployed site over HTTPS and the browser's secure-connection indicator, once deployment exists.
24. Production HSTS and Secure/HttpOnly/SameSite cookie flags after deployment, with cookie values concealed.

Useful commands (use `.\.venv\Scripts\python.exe` in PowerShell if the environment is not activated):

```text
python sample_data/make_sample_data.py
python -m pytest -q
python -m pytest -v -s tests/test_security.py
python -m pip check
```

The automated tests use temporary in-memory databases and safe payloads. Their PASS lines can be captured independently of browser demo accounts. Do not present mocked Gemini tests or a local HTTP preview as evidence of a real Gemini call or a deployed HTTPS site.
