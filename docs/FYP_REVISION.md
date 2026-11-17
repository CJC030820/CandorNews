# Candor News revision handover

Revision date: 15 October 2026. Changes are in the working tree; no commit or deployment was performed. The original supplied Word document was preserved.

## Delivered changes

| Area | Change | Main files |
|---|---|---|
| Visible article analysis | Cards show sentiment polarity; details show polarity, emotional tone, score explanation, weights, component contributions, scoring date and linked related reports. | `frontend/src/components/ArticleAnalysis.js`, `ArticleAnalysis.css`, `ArticleCard.js`, `frontend/src/pages/ArticleDetailPage.js` |
| Stable article links | Authenticated detail retrieval by ID supports direct links. Missing records and request failures are handled. An available saved copy can be used when the API is unavailable. | `backend/app/main.py`, `backend/app/services/storage.py`, `frontend/src/pages/ArticleDetailPage.js` |
| Credibility calculation | Four explicit components replace the misleading extra match-count “fact-check” factor. Related reports count once per other normalized publisher. The current publisher cannot corroborate itself. Results include evidence and a score version. | `backend/app/services/trust_scorer.py`, `backend/app/models/article.py` |
| Collection and rescoring | Normalize publication times to UTC, mark inferred dates, use computed sentiment for scoring, skip malformed/non-HTTP links, retain other-publisher coverage and rescore recent articles after collection. | `backend/app/worker.py`, `backend/app/services/deduplicator.py`, `backend/app/services/storage.py` |
| Feed provenance | Removed client-side story merging that could combine one publisher's summary with another article's score. Cards retain their own API records. | `frontend/src/pages/FeedPage.js` |
| Real refresh status | Refresh returns HTTP 202 and a job ID. The UI polls owner-only status and reports completion/failure instead of simulated progress. Jobs are bounded and tracked in one backend process. | `backend/app/main.py`, `frontend/src/context/AuthContext.js`, `frontend/src/pages/FeedPage.js` |
| Account isolation | Bookmarks, history and followed publishers use shared account-scoped local-storage handling. Switching accounts does not overwrite another account's data. Account deletion clears local activity in the current browser. | `frontend/src/hooks/useAccountStorage.js`, `BookmarkContext.js`, `ReadArticlesContext.js`, `TrustedPlatformsContext.js`, `AuthContext.js` |
| Authentication and validation | API uses bearer headers instead of query tokens. Registration validates email/name and passwords of at least 8 characters and at most 72 UTF-8 bytes. Preferences accept supported topics only; duplicate-email races are handled. | `backend/app/main.py`, `backend/app/core/config.py`, `frontend/src/context/AuthContext.js`, `frontend/src/pages/RegisterPage.js` |
| Topics | Unmatched articles use General. Local Malaysia News uses actual place keywords. Frontend and backend preference lists include General. | `backend/app/services/topic_classifier.py`, `frontend/src/constants/topics.js` |
| Email | Async scheduled jobs use the application event loop and explicit Asia/Kuala_Lumpur time (07:00/19:00). HTML content is escaped and unsafe links suppressed. Digest wording accurately describes prioritization and the heuristic score. | `backend/app/main.py`, `backend/app/services/email_service.py` |
| Persistence and health | Account timestamps persist, invalid IDs return safely, DB connection selection is bounded, `/health` pings MongoDB, and Docker uses that route. MongoDB's exposed host port binds to loopback. | `backend/app/services/storage.py`, `backend/app/models/*.py`, `backend/Dockerfile`, `docker-compose.yml` |
| Dependencies and checks | Removed unused heavyweight ML packages from active runtime requirements, added isolated test dependencies/configuration and the frontend lockfile. Corrected outdated tests and added regression checks for actual routes and UI. | `backend/requirements*.txt`, `backend/pytest.ini`, `backend/tests/`, `frontend/package-lock.json`, frontend test files |

## Score definition and migration

Version: `independent-publishers-v2`.

`score = min(95, 100 × (0.40 R + 0.45 C + 0.05 M + 0.10 N))`

- R: configured source reputation; unknown publisher defaults to 0.5.
- C: zero without related other publishers; otherwise `0.7 × mean reputation + 0.3 × min(publisher count, 4) / 4`.
- M: field completeness; inferred publication dates do not earn the date contribution.
- N: sentiment/tone neutrality cue.

Matching requires at least three shared headline tokens and at least 60% overlap relative to the larger token set after removing selected stopwords. Known configured publisher aliases are normalized. Distinct domains do not guarantee independent editorial sourcing. This score is an uncalibrated indicator, not a professional fact check or a probability of truth.

After collection, the worker rescores the latest 500 completed articles. Related-report candidates are bounded to 100 recent records in a 72-hour window. Old unversioned scores are withheld by the API until updated. This is a bounded migration: older historical records may remain pending. No database data was deleted as part of this revision.

## API and configuration changes

- Protected requests now require `Authorization: Bearer <token>`. Update any external scripts that previously sent `?token=...`.
- `GET /api/articles/{article_id}` returns the stored article analysis.
- `POST /api/articles/refresh` returns a job ID; `GET /api/articles/refresh/{job_id}` returns status to the requesting user.
- Refresh jobs and scheduler state are process-local. Run one backend process for this deployment.
- `GET /health` returns 503 when MongoDB cannot be reached.
- Configure `REACT_APP_API_URL` before building the frontend when the API address differs from the local default.
- Backend settings include `MONGODB_URL`, `DATABASE_NAME`, `CORS_ORIGINS`, `EMAIL_TIMEZONE`, `ENVIRONMENT` and `SECRET_KEY`.
- Set `ENVIRONMENT=production` and an explicit secret of at least 32 characters for deployment. Validation rejects missing, short or known development-style secrets; it does not measure entropy. Generate a random secret securely and keep it out of version control.
- Development generates a secret when none is configured, which invalidates existing tokens after restarting. Supply a stable secret when persistent sessions are required.
- The supplied local frontend is served by Nginx; browser API calls go directly to the configured FastAPI URL. Public TLS termination still needs deployment configuration.

## Verification completed

| Check | Result |
|---|---|
| Full backend pytest suite | **101 passed**, 124 warnings |
| Frontend Jest suite | **15 passed in 8 suites** |
| Frontend production build | **Passed** |
| Git whitespace/error check | **Passed**; Git reports ordinary LF/CRLF conversion notices |

Backend tests use `mongomock-motor`, controlled fixtures and mocked SMTP. Frontend tests use a DOM test environment. They cover registration/authentication, persistence contracts, article analysis/detail retrieval, refresh ownership and failure status, publisher independence, dates, malformed URLs, HTML escaping, scheduler registration, account switching and topic rules. These results do not certify real MongoDB, RSS publishers, SMTP providers, browser/device behavior or analytical accuracy.

The existing untracked `backend/tests/test_topic_detection.py` was included in the full run and was not rewritten. Existing personal workspace material was not intentionally modified.

To reproduce in your own development environment:

```powershell
cd backend
python -m pip install -r requirements-test.txt
python -m pytest -q
```

```powershell
cd frontend
npm ci
$env:CI='true'
npm test -- --watchAll=false --runInBand
npm run build
```

The test run used an isolated Python environment and installed frontend dependencies. No live email was sent. Docker was unavailable, so full Compose deployment and restart acceptance were not executed.

## Report changes and scope decisions

The revised Word report covers declarations, abstract, Chapters 1–6, requirements, diagrams, references and appendices. Open Access is selected following the author's preference. Signatures remain blank. The responsible-AI declaration discloses assistance and leaves institutional level selection to the author.

The report describes the active implementation: RSS ingestion, VADER polarity, leading-sentence summaries, keyword topics, MongoDB documents, a versioned heuristic score, topic/platform filtering and browser-local activity. It no longer claims that inactive NewsAPI/GNews adapters, BERT, behavioral recommendation, server-synchronized bookmarks/history or external claim-level fact checking are implemented. These larger subsystems need separate design and evaluation.

The report includes actual executed test evidence and clearly pending empirical evaluation. The earlier 13% similarity screenshot is labelled historical; it does not apply to the new report. Obtain a new similarity report for submission.

## Remaining work before final submission

1. Run the application with real MongoDB and check clean startup, ingestion, persistence across restart, direct article links and account switching.
2. Verify each live RSS source and conduct an authorized SMTP test, including scheduled delivery, opt-out and provider failures.
3. Measure sentiment/topic/matching quality on labelled news examples and assess summary quality. Do not report software pass counts as model accuracy.
4. Complete genuine user tasks and performance measurements with recorded methods and results.
5. Review the code and report with the supervisor; confirm scope, acknowledgements, AI-use level, signatures and final similarity checks.

The revision improves implementation completeness and traceability for a Bachelor of Software Engineering project. A final grade or submission-readiness judgment still depends on the university rubric and the remaining evaluation evidence.
