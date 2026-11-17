# Security review and regression register

Reviewed on 12 November 2026 against the current working tree. Scope: the active
FastAPI application, MongoDB storage, RSS collector, React rendering, and email
service. This is a source review with isolated regression reproductions. It is
not a penetration test, a dependency/CVE audit, a Git-history secret scan, or
proof of browser security. No real provider, private-network host, or SMTP
recipient is contacted by the regression tests.

Severity indicates potential impact and exposure in this application; it is not
a CVSS score. The application may be used locally, but its supplied Compose file
publishes the backend and frontend ports. Internet-facing deployment needs its own
review. Local source links below refer to the reviewed version; line numbers may
move after later edits.

## Open findings

| ID | Severity | Finding and evidence | Recommended correction and verification |
|---|---|---|---|
| SEC-01 | High | **A deleted account's token can authenticate a replacement account with the same email.** Login places the email in JWT `sub` ([main.py:249](../../backend/app/main.py#L249)); authentication looks up the current account using that email ([main.py:185](../../backend/app/main.py#L185), [main.py:191](../../backend/app/main.py#L191)). Deletion removes the user, but does not prevent email reuse. | Use immutable account ID as the subject and resolve that ID. Reject old email-subject tokens during migration, or use an explicit token version/revocation scheme. Register, log in, delete, register the same email, then assert the original token still returns 401. A strict expected-failure regression is in [test_api_contracts.py](../../backend/tests/test_api_contracts.py). |
| SEC-02 | Medium, conditional on upstream control | **RSS image discovery can request internal destinations.** Feed article links are passed to image discovery ([news_fetcher.py:178](../../backend/app/services/news_fetcher.py#L178)), which performs a GET without destination or redirect restrictions ([news_fetcher.py:251](../../backend/app/services/news_fetcher.py#L251)). The later worker scheme check ([worker.py:123](../../backend/app/worker.py#L123)) does not protect this earlier request. A compromised configured feed could supply a loopback/private address or redirect to one. There is no public API accepting an arbitrary feed URL. | Validate permitted destinations before requests, handle redirects explicitly, and validate every redirect destination and resolved address. Consider a publisher-host allowlist and network egress restrictions. Enforce response-size limits as well. The regression intercepts every GET and proves the loopback request is attempted; private IPv4/IPv6, link-local, DNS changes and redirects need further tests after the fetch policy is implemented. |
| SEC-03 | Medium; requires configured SMTP | **Unverified accounts can trigger email to addresses they do not own.** Registration validates email syntax but has no ownership verification ([main.py:212](../../backend/app/main.py#L212)). The authenticated test endpoint sends immediately ([main.py:457](../../backend/app/main.py#L457)), including custom plaintext ([main.py:510](../../backend/app/main.py#L510)), to the registered address ([main.py:521](../../backend/app/main.py#L521)). There is no send cooldown. This permits repeated messages to another person's address after registering it. | Require verified email ownership before on-demand or scheduled sends; add per-account and global rate limits and message-size limits. Consider removing custom text if unnecessary. The isolated regression mocks SMTP and expects an unverified account's send to be rejected before the SMTP function is invoked. Rate-limit and scheduled-send enforcement require additional tests when implemented. |
| SEC-04 | Medium, inactive provider path | **Provider failure logs may expose API keys.** NewsAPI and GNews place credentials in query parameters ([news_fetcher.py:81](../../backend/app/services/news_fetcher.py#L81), [news_fetcher.py:117](../../backend/app/services/news_fetcher.py#L117)). Retry logging interpolates exception text ([news_fetcher.py:69](../../backend/app/services/news_fetcher.py#L69), [news_fetcher.py:72](../../backend/app/services/news_fetcher.py#L72)); an HTTP error can include its full request URL. Current collection calls RSS only ([news_fetcher.py:272](../../backend/app/services/news_fetcher.py#L272)), so exposure depends on invoking these helpers. No real secret was read or leaked during this review. | Log a sanitized host, status and error category; redact credentials from URL and exception text. Verify both retry and terminal failures using fake secrets. The regression uses a synthetic `requests.Response` with a fake query credential and confirms that the current logs contain it. |
| SEC-05 | Medium | **Login lacks throttling and performs password verification on the async event loop.** The route directly calls synchronous bcrypt verification ([main.py:244](../../backend/app/main.py#L244), [security.py:9](../../backend/app/core/security.py#L9)). No login rate limiter is present in the inspected application or supplied nginx configuration. | Apply account/IP-aware throttling and execute expensive password verification outside the event loop. Measure concurrent login separately from feed reads; verify feed latency remains acceptable during a bounded local login test. No traffic-based denial-of-service test was run. |

## Regression execution and interpretation

From `backend`, with the test requirements installed:

```powershell
python -m pytest tests/test_security_regressions.py -q -rx
python -m pytest tests/test_api_contracts.py -q -rx
```

[test_security_regressions.py](../../backend/tests/test_security_regressions.py)
contains three strict expected-failure (`xfail`) checks for SEC-02, SEC-03 and
SEC-04. Database access uses the existing in-memory fixture; HTTP and SMTP are
mocked, and the ASGI client does not run startup jobs. Only assertion failures
qualify as the expected failures; import and runtime exceptions still fail.

An `XFAIL` records an **open defect**, not a pass or a completed security fix.
`strict=True` makes an unexpected pass fail the suite, prompting review and
removal of the marker when the fix is ready. Keep expected-failure counts separate
from passing-test totals in the FYP report. These tests demonstrate narrow cases;
they are not exhaustive proofs of either vulnerability or remediation.

## Additional boundaries and follow-up checks

- **Database integrity:** index creation errors are logged and suppressed
  ([storage.py:22](../../backend/app/services/storage.py#L22)). If unique indexes
  cannot be created, continued startup does not guarantee duplicate prevention.
  Add a real-MongoDB startup/index-failure check and consider failing readiness
  when required indexes are unavailable. Mock database tests do not verify query
  plans, durable writes or production concurrency behavior.
- **Session lifecycle:** logout clears the browser token
  ([AuthContext.js:13](../../frontend/src/context/AuthContext.js#L13)); tokens
  otherwise last 30 days ([config.py:32](../../backend/app/core/config.py#L32)).
  Server-side logout revocation is not implemented. Local storage makes tokens
  accessible to same-origin script, but this review did not demonstrate an XSS
  route or token theft.
- **Injection:** the active database uses structured MongoDB queries, not SQL.
  Operator-shaped JSON should fail typed request validation; SQL-like strings
  should remain literal. Active React article text uses normal text interpolation,
  and email HTML has escaping coverage. Neither observation replaces real-browser
  testing of malicious text, legacy stored URL values, image links, or redirects.
- **Deployment:** the supplied MongoDB host port binds to loopback, while
  application ports are published ([docker-compose.yml](../../docker-compose.yml)).
  TLS termination, access controls, security headers and production secret setup
  must be checked in the actual hosting environment. The development Compose file
  alone is not evidence that a deployed service is exposed or protected.
- **Secrets and dependencies:** this review did not inspect credential values,
  scan repository history, or query advisory databases. Do not describe it as a
  complete secret scan or claim pinned dependencies have no known vulnerabilities.

## Load-test implications

Use a separate seeded database and local/stubbed providers. Measure feed/detail
latency, login latency, refresh acceptance, and refresh completion separately.
The worker serializes collection through a lock
([worker.py:227](../../backend/app/worker.py#L227)); refresh jobs are process-local
and bounded to 100 ([main.py:366](../../backend/app/main.py#L366)). One hundred
pending jobs therefore do not represent one hundred parallel collection runs.
Multiple server processes do not share this job state or lock.

Never include real SMTP or repeated publisher fetches in an automated load
scenario. Document p50/p95/p99 latency, error rate, data volume, concurrency,
hardware and test duration. Proposed response-time targets and concurrency levels
are acceptance criteria until measurements are recorded; they are not results of
this review.
