# News aggregator testing package

Prepared 12 November 2026 for the current Candor News working tree. This package applies the proposed FYP testing strategy to the implementation that exists: **FastAPI, MongoDB, React, RSS collection, VADER sentiment, leading-sentence summaries, and a heuristic trust indicator**.

The feed is `GET /api/articles/feed`, with a bearer token. There is no Flask `/news` endpoint or SQL database. NewsAPI/GNews adapters exist and receive isolated unit tests, but the active collection pipeline uses RSS. Search operates in the browser. Bookmarks and reading history use account-scoped browser storage. A trust score is an indicator, not a probability that an article is true.

## Files and evidence

| Artifact | Purpose |
|---|---|
| [Test case matrix](TEST_CASES.md) | Module, API, database, integration, security and manual scenarios with expected outcomes |
| [Security review](SECURITY_REVIEW.md) | Code-evidenced findings, regression probes and proposed remedies |
| [Usability and UAT forms](USABILITY_UAT.md) | Participant tasks, five-point ratings, acceptance and analysis templates |
| [Execution results](RESULTS.md) | Actual executed outcomes and remaining evaluation work |
| [Sentiment dataset](../../backend/tests/fixtures/sentiment_headlines.json) | 100 positive, 100 negative and 100 neutral fictional headlines |
| [Sentiment evaluation](sentiment_evaluation.json) | Measured confusion matrix, per-class metrics and disagreements |
| [API benchmark](../../backend/scripts/benchmark_api.py) | Opt-in local read-only feed traffic with latency, throughput and error reporting |

The older root `TESTING_GUIDE.md` concerns a previous timestamp UI enhancement. Use this package for current FYP scope; historical checkmarks or deployment statements are not current test evidence.

## Reproduce automated checks

Run from the repository root in PowerShell with Python 3.12 available:

```powershell
python -m venv .venv
& '.\.venv\Scripts\python.exe' -X utf8 -m pip install -r backend/requirements-test.txt
Push-Location backend
& '..\.venv\Scripts\python.exe' -X utf8 -m pytest -q -rx --junitxml=../docs/testing/backend-results.xml
Pop-Location
Push-Location frontend
npm ci
$env:CI='true'
npm test -- --watchAll=false --runInBand
Pop-Location
```

If `.venv` already exists, reuse it. Windows sandbox environments may require running the test command with local socket permission: asyncio creates an internal loopback socket pair even when all application I/O is mocked.

Run pytest from `backend`, where `pytest.ini` limits discovery to `tests`. Root-level legacy scripts such as `test_smtp.py` are outside this isolated suite. The shared fixture replaces MongoDB with `mongomock-motor`; ASGI clients do not start the application lifespan, RSS worker or email scheduler. HTTP collection and email-send tests mock external calls. The suite does not prove real MongoDB persistence, publisher availability, SMTP delivery or actual browser compatibility.

Tests marked `xfail(strict=True)` describe **open defects**, not successful acceptance tests. They execute and reproduce the problem. An unexpected pass makes the suite fail so the marker and defect documentation can be reviewed after a fix. Do not present a green pytest exit code as proof that all requirements pass.

New automated coverage is in `test_api_contracts.py`, `test_database_contracts.py`, `test_news_modules.py`, `test_security_regressions.py`, `test_sentiment_fixture.py` and `test_benchmark_api.py`. Existing `test_active_features.py`, model/topic tests and frontend tests remain part of regression verification. `test_usability.py` contains service checks; it is not evidence of a participant study.

## Sentiment and summary evaluation

```powershell
& '.\.venv\Scripts\python.exe' -X utf8 backend/scripts/evaluate_sentiment.py --output docs/testing/sentiment_evaluation.json
```

The JSON fixture has 300 distinct fictional headlines and exactly 100 intended labels per class. Its labels were authored with AI assistance, independently of classifier predictions. They are provisional, not a human-validated gold standard. The output-contract tests check allowed labels and score bounds; they intentionally do not require 300 correct predictions.

For defensible evaluation, have two reviewers independently label a separate representative sample of real articles, record disagreements, agree on a final label, and keep that sample separate from tuning data. Report sample selection, class balance, confusion matrix, per-class precision/recall/F1, macro F1 and accuracy. Distinguish polarity toward an event from the neutrality of journalistic wording. Review sarcasm, negation, mixed sentiment and local vocabulary separately.

For summaries, independently rate at least 30 articles across topics and lengths. Compare the summary with the supplied text for factual consistency, key-point coverage, readability and compression. Record whether full article text or only an RSS excerpt was available. This implementation selects the first four punctuation-separated segments; passing a long-input test does not demonstrate abstractive quality. Abbreviations/decimals can be split incorrectly, and a punctuation-free 5,001-word input is not shortened.

For trust scores, use controlled examples to verify the documented formula and provenance. Separately assess whether linked reports cover the same event and whether their publishers share an original source. Do not interpret software test pass rate as fact-checking accuracy.

## Performance, load and stress protocol

These are **proposed acceptance targets**, not measured results: cached feed p95 below 5 seconds, single-article sentiment p95 below 2 seconds, and dashboard time to usable article list p95 below 3 seconds. Record hardware, OS, browser, dependency versions, build, network, worker count, MongoDB version, data volume and warm/cold cache state. Agree final thresholds with the supervisor before collecting results.

Use a disposable local instance and test account with a representative database, for example 10,000 seeded synthetic articles. Disable scheduled email and use local/stubbed RSS sources in the benchmark instance; starting the normal app also starts ingestion/scheduling. The provided script does not start the app, seed data, refresh articles or send messages. It accepts only loopback origins and reads an existing test token from `NEWS_TEST_TOKEN`; it does not log the token.

From `backend`, set `NEWS_TEST_TOKEN` in the local shell using a disposable test account token, then run:

```powershell
& '..\.venv\Scripts\python.exe' -X utf8 scripts/benchmark_api.py --users 1 --seconds 30 --rate 1 --output ../docs/testing/feed-warmup.json
& '..\.venv\Scripts\python.exe' -X utf8 scripts/benchmark_api.py --users 10 --seconds 60 --rate 10 --output ../docs/testing/feed-10-users.json
& '..\.venv\Scripts\python.exe' -X utf8 scripts/benchmark_api.py --users 100 --seconds 60 --rate 100 --output ../docs/testing/feed-100-users.json
& '..\.venv\Scripts\python.exe' -X utf8 scripts/benchmark_api.py --users 100 --seconds 60 --rate 16.67 --output ../docs/testing/feed-1000-per-minute.json
```

The client count bounds concurrent requests; it is not a claim of 100 simultaneous requests at every instant. This is a closed-loop workload: `--rate` is an aggregate pacing ceiling, and slow responses lower achieved throughput. The 16.67 requests/second example approximates 1,000/minute only when the system keeps up. Record achieved throughput, not just the requested rate. A 1,000/minute scenario is not necessarily a stress test: increase traffic beyond the measured sustainable capacity to find the limit.

Run a warm-up and three recorded repetitions at 1, 10, 50 and 100 clients. Report successful-request and all-request p50/p95/p99, error rate, status codes, CPU, memory and MongoDB connection counts. The harness exits nonzero if successful p95 or error-rate targets fail. Record a minimum useful sample size and extend duration if necessary. It deliberately counts invalid response shapes as errors and separates fast error responses from successful latency.

For stress testing, gradually increase offered traffic on the disposable instance, stop when latency/error thresholds or resource limits are reached, then return to baseline. Verify health, data integrity and recovery within a pre-agreed interval. For memory growth, repeat stable load for 30 minutes while sampling process memory; the short harness runs alone do not establish absence of leaks. Do not send repeated refresh or email traffic to publishers or recipients.

Measure login separately because password verification has different CPU costs. Measure refresh POST acceptance separately from completion time: collection is serialized and job state is process-local. Measure dashboard loading in a real browser, including network and rendering. For sentiment, warm the analyzer once, time individual representative inputs with a monotonic timer, and report length and percentile distribution. None of these measurements is supplied by the feed harness.

## Real database and deployment integration

On a separate MongoDB test database, repeat URL/email uniqueness tests, including concurrent insert attempts. Restart the backend and database, then verify account settings and articles persist. Examine query plans for feed sorting and recent keyword lookup with representative data. Test failed index creation and database unavailability; mock results do not establish MongoDB server concurrency, transaction or query-plan behavior.

Interactions are not an active foreign-key-backed feature. If server-side interaction persistence is introduced, define referential validation and account-deletion cleanup before claiming relationship integrity. Browser-local bookmarks/history need account-switch and account-deletion checks on each browser/device.

Live RSS and SMTP checks are separate integration exercises. Record source, time, response/error and sanitized evidence. Sending a real test email is a deliberate manual action to a consenting test recipient, not part of the default automated suite.

## Chapter 5 structure and AI disclosure

Use sections for test environment/method, functional and unit testing, API/integration/database testing, analytical evaluation, performance/load testing, usability/UAT, security/regression results, and remaining defects. Link requirement IDs to cases and evidence. For each result record input, expected behavior, observed behavior, status, tester, date and artifact. Report pending studies as pending.

Suggested wording, to retain only when it matches work actually completed:

> AI-assisted coding tools were used to propose edge cases, draft automated tests and synthetic evaluation data, and assist code review. Generated tests were checked against the implementation and executed in an isolated environment. Synthetic labels remain provisional until independently reviewed. Known defects and unexecuted human, deployment and performance evaluations are reported separately from passing software checks.

Only add a claim that all generated cases were manually validated after that review has actually taken place.
