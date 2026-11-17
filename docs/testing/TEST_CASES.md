# Test case matrix

Cases below specify expected behavior and the verification method. `Automated` refers to executable coverage, not a promised result; see [RESULTS.md](RESULTS.md). `Open defect` cases have strict expected-failure probes. `Manual/pending` requires evidence before acceptance. Tests use synthetic records and isolated dependencies unless explicitly stated otherwise.

## Collection, processing and summary

| ID | Input or scenario | Expected result | Evidence / method |
|---|---|---|---|
| COL-01 | Empty active RSS collection | Zero fetched/saved; completed stats; no crash | Automated: `test_news_modules.py` |
| COL-02 | Optional NewsAPI empty articles | Empty list | Automated: module tests; adapter is inactive in worker |
| COL-03 | Missing optional provider API key | Empty list without outbound request | Automated: module tests |
| COL-04 | Invalid RSS URL, timeout or HTTP failure | Error handled; empty collection for that feed | Automated: mocked module tests |
| COL-05 | Temporary provider error then recovery | Bounded retries, backoff and eventual result | Automated: module tests |
| COL-06 | Repeated provider errors | Stop after retry budget, return safely | Automated: module tests |
| COL-07 | RSS metadata/content contains HTML entities | Normalize text and preserve readable content | Automated: module tests |
| COL-08 | RSS image in media, enclosure, HTML or OG fallback | Deterministic usable image selection; fallback errors handled | Automated: module tests |
| COL-09 | Identical URL appears twice | Keep one stored article, original unchanged | Automated: database/module tests |
| COL-10 | Same story from different publishers | Preserve separate reports for comparison | Automated: module + existing active-feature tests |
| COL-11 | Missing or malformed publication date | Mark inferred date; no date-completeness reward | Automated: existing active-feature tests |
| COL-12 | One malformed IPv6-style URL in batch | Skip bad item and continue valid items | Open defect: module strict xfail |
| COL-13 | Selected RSS platforms | Fetch matching configured sources and filter result publishers | Automated: module tests |
| COL-14 | Real publisher changes format or rate limits | Clear failure/stats; remaining publishers continue where possible | Manual/pending live integration |
| COL-15 | Non-English content or ambiguous language | Apply documented English filter; record false inclusions/exclusions | Manual/pending labelled language sample |
| SUM-01 | Empty/whitespace/punctuation-only input | Empty summary; helper returns fallback when no source text exists | Automated: module tests |
| SUM-02 | More than 5,000 words in normal sentences | Generate first four segments; worker saves summary and bounded excerpt | Automated: module tests |
| SUM-03 | Description absent, content present | Helper uses excerpt/content; worker uses content then description/title | Automated: module/worker tests; helper and worker precedence differ |
| SUM-04 | Abbreviation and decimal amount | Preserve names and numeric meaning | Open defect: module strict xfail |
| SUM-05 | 5,001 words with no sentence punctuation | Assess whether output meets agreed length requirement | Known limitation: no word cap; manual acceptance decision |
| SUM-06 | Main fact occurs late, multiple topics, quotation or negation | Human rates factual consistency, coverage and readability | Manual/pending 30-article review |

## Sentiment and trust

| ID | Input or scenario | Expected result | Evidence / method |
|---|---|---|---|
| SEN-01 | Compound score at -0.05, 0.05 and adjacent values | Negative/positive inclusive thresholds; neutral between | Automated: module tests |
| SEN-02 | Empty article | Neutral, score 0, neutral/objective tone | Automated: module tests |
| SEN-03 | Positive phrase versus its negation | Polarity changes for controlled example | Automated: module tests |
| SEN-04 | Neutral title and negative body | Analyze combined supplied text | Automated: module tests |
| SEN-05 | Tone thresholds and conflicting cues | Require the combined emotional-cue conditions | Automated: module tests |
| SEN-06 | 300 fictional headlines | 100/class, unique IDs/headlines; valid result labels and bounded scores | Automated: fixture tests |
| SEN-07 | Classifier versus intended fixture labels | Report confusion matrix and mismatches without forcing perfect agreement | Measured: sentiment evaluation JSON; labels provisional |
| SEN-08 | Sarcasm, mixed sentiment, local vocabulary | Independent human labels and per-class performance analysis | Manual/pending representative held-out sample |
| TRU-01 | Missing author only | Metadata component falls 1.00 to 0.75; overall score falls 1.25 points when uncapped | Automated: module tests |
| TRU-02 | Unknown source / out-of-range configured source prior | Default 0.5; bound prior to 0..1 | Automated: module tests |
| TRU-03 | Own publisher aliases/repeated same-publisher links | No self-corroboration; one report per other publisher | Automated: existing active-feature tests |
| TRU-04 | Similar versus unrelated headlines | Require token overlap and minimum shared-token count | Automated: module tests |
| TRU-05 | Same evidence in a different order | Identical selected evidence and score | Automated: module tests |
| TRU-06 | All maximum components | Weights sum to 1; score cap is 95 | Automated: existing active-feature tests |
| TRU-07 | Legacy unversioned score | Feed withholds score until rescoring | Automated: existing active-feature tests |
| TRU-08 | Second publisher added after first article | Rescore first article and expose linked evidence | Automated: existing worker/API tests |
| TRU-09 | Copied syndicated reports or disagreeing claims | Document heuristic limits; human reviews evidence relevance | Manual/pending; domain count does not prove independence or truth |

## API, integration, database and regression

| ID | Input or scenario | Expected result | Evidence / method |
|---|---|---|---|
| API-01 | Authenticated empty feed | 200 JSON, `articles: []`, count 0 | Automated: API contracts; UI wording is “No articles found” |
| API-02 | Missing bearer token on protected routes | 401, no collection/settings mutation/email | Automated: API contracts |
| API-03 | Expired, incorrectly signed, subjectless or unknown-user token | 401 | Automated: API contracts |
| API-04 | Invalid, fractional, negative or excessive feed limit | 422 | Automated: API contracts |
| API-05 | Filter matches primary or secondary topic | Newest matching completed records first, honor limit | Automated: API contracts |
| API-06 | Pending/failed article ID | 404; absent from feed | Automated: API contracts |
| API-07 | Invalid or missing valid ObjectId | 404 without internal exception | Automated: API/database contracts |
| API-08 | Direct article URL after reload | Detail matches feed analysis or clear unavailable state | Automated: existing API/frontend detail tests |
| API-09 | Register invalid email, blank name, short/overlong password | Validation failure; no account created | Automated: new and existing API tests |
| API-10 | Successful register/login/profile update | Hash password, persist current account, exclude secrets from response | Automated: new and existing API tests |
| API-11 | Refresh without platforms | 400; no worker task starts | Automated: API contracts |
| API-12 | Duplicate refresh while pending / another user's job | Reuse own pending job; other user gets 404 | Automated: existing active-feature tests |
| API-13 | Worker completes or fails | Job status reflects actual outcome | Automated: existing active-feature tests |
| API-14 | MongoDB health ping fails | `/health` returns 503 | Automated: existing active-feature tests |
| API-15 | SMTP fails | Test-email route returns failure, not successful-send status | Automated: existing mocked email test |
| DB-01 | Save and fetch full article | Preserve text, optional author, categories and analysis; BSON millisecond dates | Automated: database contracts |
| DB-02 | Duplicate URL or email with indexes enabled | URL skip; duplicate email rejected; counts correct | Automated: database contracts |
| DB-03 | Repeated index initialization | Unique indexes remain correct | Automated: database contracts |
| DB-04 | Corroboration candidates include old/self/pending/unrelated data | Exclude those candidates; empty keywords produce no matches | Automated: database contracts |
| DB-05 | Pending article becomes completed | Appears in feed with processed timestamp | Automated: database contracts |
| DB-06 | Update score/version | Preserve article ID, URL and other fields | Automated: database contracts |
| DB-07 | Real MongoDB concurrent duplicate inserts | Exactly one article/email stored; deterministic caller outcome | Manual/pending real-server integration |
| DB-08 | Restart app/database | Articles and preferences survive | Manual/pending real-server integration |
| DB-09 | Index creation denied or conflicting existing records | Detect integrity risk; do not claim duplicate protection | Manual/pending; startup currently logs and continues |
| DB-10 | Representative volume feed/keyword queries | Query-plan and latency targets met | Manual/pending real MongoDB explain/measurement |
| REG-01 | Change scoring, auth, topics or UI | Run full backend and frontend suites; investigate changed outcomes | Automated: full regression command |
| REG-02 | Change account or delete account in browser | Local activity isolated/cleared as specified | Automated: existing account-storage tests; real browser follow-up pending |

## Security and quality evaluation

| ID | Input or scenario | Expected result | Evidence / method |
|---|---|---|---|
| SEC-01 | Delete account, re-register same email, reuse old JWT | Old token remains unauthorized | Open defect: API strict xfail; security review |
| SEC-02 | RSS link targets loopback/private IP | Reject before server-side fetch | Open defect: mocked security probes; upstream compromise prerequisite |
| SEC-03 | Fake provider secret in request-error URL | Logs omit/redact secret | Open defect: mocked security probe; inactive adapter |
| SEC-04 | JSON MongoDB operator in login fields | Reject object input with 422 | Automated: API contracts |
| SEC-05 | SQL-style login string / operator-like topic string | Literal values; no authentication bypass or query broadening | Automated: API contracts |
| SEC-06 | Script/image HTML in email title/name/body | Escape text and suppress unsafe links | Automated: existing digest test |
| SEC-07 | Script-like article/title/name in actual UI | Render inert text; no script executes or unsafe link navigation | Manual/pending browser test; no claim of browser XSS certification |
| SEC-08 | Try to target another account through profile body | Update authenticated account only | Automated: API contracts |
| SEC-09 | Repeated login/email-send attempts | Agreed rate limit, cooldown and address-ownership policy | Open design/security gaps; review; do not send real test mail automatically |
| SEC-10 | Secret configuration and dependency review | No tracked secrets, redacted logs; triaged package findings | Partial read-only review; history/dependency audit pending |
| PERF-01 | Cached feed at baseline | Proposed p95 <5 s, error rate <=1% | Pending local benchmark |
| PERF-02 | Representative single-article sentiment | Proposed p95 <2 s after warm-up | Pending timed offline evaluation |
| PERF-03 | Dashboard load in browser | Proposed p95 <3 s to usable list | Pending browser measurement |
| LOAD-01 | 1/10/50/100 clients | Record actual RPS, percentile latency and errors | Pending benchmark; no inferred capacity claim |
| STRESS-01 | Increase offered traffic beyond sustainable capacity | Record failure threshold, resource use and recovery | Pending isolated stress experiment |
| COMP-01 | Chrome, Edge, Firefox, Android Chrome, iOS Safari | Core tasks usable; no clipping or broken interactions | Pending browser/device matrix |
| USE-01 | Ten participants perform search/filter/detail/compare tasks | Record success, time, errors, assistance and feedback | Pending participant study |
| UAT-01 | Supervisor/users review acceptance requirements | Signed/dated accepted, conditional or rejected decisions | Pending UAT; forms provided |

## Result record template

| Case ID | Build / environment | Input / preconditions | Expected | Observed | Status | Evidence | Tester / date |
|---|---|---|---|---|---|---|---|
| Fill during execution | | | | | Not run | | |

Use `Pass`, `Fail`, `Expected failure (open defect)`, `Blocked`, `Not run` or `Not applicable` with a reason. Do not replace observed results with expected results.
