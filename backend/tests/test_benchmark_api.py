"""Deterministic benchmark validation; no service or real sockets are used."""
import asyncio
from types import SimpleNamespace

import httpx
import pytest

from scripts import benchmark_api


def arguments(**updates):
    values = dict(base_url="http://127.0.0.1:8000", users=1, seconds=5., rate=1.,
                  limit=50, timeout=10., p95_target_ms=5000., max_error_rate=.01)
    values.update(updates)
    return SimpleNamespace(**values)


class FakeClock:
    def __init__(self):
        self.now = 10.

    def perf_counter(self):
        return self.now

    async def sleep(self, seconds):
        self.now += seconds


@pytest.fixture
def clock(monkeypatch):
    clock = FakeClock()
    monkeypatch.setattr(benchmark_api, "time", clock)
    monkeypatch.setattr(benchmark_api, "asyncio", SimpleNamespace(sleep=clock.sleep, gather=asyncio.gather))
    return clock


def mock_transport(monkeypatch, handler):
    original_client = httpx.AsyncClient
    options = {}

    def make_client(**kwargs):
        options.update(kwargs)
        return original_client(transport=httpx.MockTransport(handler), **kwargs)

    monkeypatch.setattr(benchmark_api.httpx, "AsyncClient", make_client)
    return options


@pytest.mark.parametrize("option,value", [
    ("--base-url", "https://example.test"),
    ("--base-url", "http://192.168.1.10:8000"),
    ("--base-url", "http://localhost:8000/path"),
    ("--base-url", "http://user:password@localhost:8000"),
    ("--base-url", "http://localhost:99999"),
    ("--users", "0"), ("--limit", "1001"),
    ("--seconds", "nan"), ("--rate", "inf"), ("--timeout", "61"),
    ("--p95-target-ms", "0"), ("--max-error-rate", "1.1"),
])
def test_benchmark_rejects_invalid_or_remote_arguments(monkeypatch, option, value):
    monkeypatch.setenv("NEWS_TEST_TOKEN", "synthetic-token")
    monkeypatch.setattr("sys.argv", ["benchmark_api.py", option, value])
    with pytest.raises(SystemExit) as error:
        benchmark_api.parse_args()
    assert error.value.code == 2


@pytest.mark.parametrize("base_url", ["http://localhost:8000", "http://127.0.0.1:8000", "http://[::1]:8000"])
def test_benchmark_accepts_loopback_origins(monkeypatch, base_url):
    monkeypatch.setenv("NEWS_TEST_TOKEN", " synthetic-token ")
    monkeypatch.setattr("sys.argv", ["benchmark_api.py", "--base-url", base_url])
    args, token = benchmark_api.parse_args()
    assert args.base_url == base_url
    assert token == "synthetic-token"


def test_benchmark_requires_explicit_test_account_token(monkeypatch):
    monkeypatch.delenv("NEWS_TEST_TOKEN", raising=False)
    monkeypatch.setattr("sys.argv", ["benchmark_api.py"])
    with pytest.raises(SystemExit) as error:
        benchmark_api.parse_args()
    assert error.value.code == 2


async def test_benchmark_honors_duration_and_reports_successful_latency(monkeypatch, clock):
    starts = []

    def handler(request):
        starts.append(clock.now)
        clock.now += .01
        assert request.url.path == "/api/articles/feed"
        assert request.url.params["limit"] == "50"
        assert request.headers["Authorization"] == "Bearer synthetic-token"
        return httpx.Response(200, json={"articles": []})

    options = mock_transport(monkeypatch, handler)
    report = await benchmark_api.benchmark(arguments(), "synthetic-token")
    assert starts == pytest.approx([10, 11, 12, 13, 14])
    assert report["elapsed_seconds"] == 5.
    assert report["requests"] == report["successful_requests"] == 5
    assert report["achieved_rps"] == 1.
    assert report["successful_requests_ms"]["p95"] == pytest.approx(10.)
    assert report["error_rate"] == 0.
    assert report["targets_met"] is True
    assert options["trust_env"] is False and options["follow_redirects"] is False


async def test_benchmark_separates_http_contract_json_and_transport_failures(monkeypatch, clock):
    responses = iter([
        httpx.Response(200, json={"articles": []}),
        httpx.Response(401, json={"detail": "Unauthorized"}),
        httpx.Response(200, json={"articles": {}}),
        httpx.Response(200, content=b"not JSON"),
        httpx.ReadTimeout("sensitive upstream diagnostic"),
    ])

    def handler(request):
        clock.now += .02
        result = next(responses)
        if isinstance(result, Exception):
            raise result
        return result

    mock_transport(monkeypatch, handler)
    report = await benchmark_api.benchmark(arguments(), "synthetic-token")
    assert report["requests"] == 5 and report["successful_requests"] == 1
    assert report["status_counts"] == {"200": 3, "401": 1}
    assert report["failure_counts"] == {
        "http_status": 1, "response_contract": 1, "invalid_json": 1, "ReadTimeout": 1}
    assert report["error_rate"] == .8
    assert report["targets_met"] is False
    assert "sensitive upstream diagnostic" not in str(report)
    assert "synthetic-token" not in str(report)


async def test_benchmark_does_not_burst_to_catch_up_after_slow_response(monkeypatch, clock):
    starts = []

    def handler(request):
        starts.append(clock.now)
        clock.now += 1.5 if len(starts) == 1 else .01
        return httpx.Response(200, json={"articles": []})

    mock_transport(monkeypatch, handler)
    report = await benchmark_api.benchmark(arguments(seconds=3.), "synthetic-token")
    assert starts == pytest.approx([10, 11.5, 12.5])
    assert report["elapsed_seconds"] == 3.
    assert report["successful_requests_ms"]["p95"] == pytest.approx(1500.)


async def test_all_failed_requests_cannot_meet_latency_target(monkeypatch, clock):
    def handler(request):
        clock.now += .01
        return httpx.Response(503, json={"detail": "Offline"})

    mock_transport(monkeypatch, handler)
    report = await benchmark_api.benchmark(arguments(seconds=1., max_error_rate=1.), "synthetic-token")
    assert report["successful_requests_ms"]["p95"] is None
    assert report["error_rate"] == 1.
    assert report["targets_met"] is False


def test_percentiles_use_nearest_rank_and_handle_no_results():
    assert benchmark_api.percentile([], .95) is None
    assert benchmark_api.percentile([40, 10, 30, 20], .5) == 20
    assert benchmark_api.percentile([40, 10, 30, 20], .95) == 40
