"""Opt-in local read-only feed benchmark; never starts the app or sends email.

Run from backend: python scripts/benchmark_api.py --help
Set NEWS_TEST_TOKEN to a disposable test account's bearer token.
"""
import argparse
import asyncio
from collections import Counter
import ipaddress
import json
import math
import os
from pathlib import Path
import time
from urllib.parse import urlsplit

import httpx


def percentile(values, percent):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(percent * len(ordered)) - 1)] if ordered else None


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--users", type=int, default=1, help="Maximum concurrent clients (1-1000)")
    parser.add_argument("--seconds", type=float, default=30)
    parser.add_argument("--rate", type=float, default=5, help="Aggregate pacing ceiling in requests/second; actual throughput may be lower")
    parser.add_argument("--limit", type=int, default=50, help="Feed page size (1-1000)")
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--p95-target-ms", type=float, default=5000)
    parser.add_argument("--max-error-rate", type=float, default=.01)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        url = urlsplit(args.base_url)
        loopback = url.hostname == "localhost" or ipaddress.ip_address(url.hostname or "").is_loopback
        valid_port = url.port  # Validate malformed ports before starting clients.
    except ValueError:
        parser.error("base-url must use localhost or a numeric loopback address")
    if not loopback or url.scheme not in {"http", "https"} or url.username or url.password or url.query or url.fragment or url.path not in {"", "/"}:
        parser.error("base-url must be a local HTTP(S) origin without credentials, path, or query")
    if not 1 <= args.users <= 1000 or not 1 <= args.limit <= 1000:
        parser.error("users and limit must be between 1 and 1000")
    for name in ("seconds", "rate", "timeout", "p95_target_ms"):
        if not math.isfinite(getattr(args, name)) or getattr(args, name) <= 0:
            parser.error(f"{name} must be positive and finite")
    if args.seconds > 600 or args.rate > 1000 or args.timeout > 60:
        parser.error("Maximums: 600 seconds, 1000 requests/second, 60-second timeout")
    if not math.isfinite(args.max_error_rate) or not 0 <= args.max_error_rate <= 1:
        parser.error("max-error-rate must be between 0 and 1")
    token = os.environ.get("NEWS_TEST_TOKEN", "").strip()
    if not token:
        parser.error("Set NEWS_TEST_TOKEN to a disposable local test account token")
    return args, token


async def benchmark(args, token):
    latencies, successful_latencies = [], []
    failures, statuses = Counter(), Counter()
    start = time.perf_counter()
    end = start + args.seconds
    interval = args.users / args.rate
    async with httpx.AsyncClient(
        base_url=args.base_url, headers={"Authorization": f"Bearer {token}"},
        timeout=args.timeout, follow_redirects=False, trust_env=False,
        limits=httpx.Limits(max_connections=args.users, max_keepalive_connections=args.users),
    ) as client:
        async def reader(index):
            next_start = start + index / args.rate
            while next_start < end:
                await asyncio.sleep(max(0, next_start - time.perf_counter()))
                request_start = time.perf_counter()
                if request_start >= end:
                    break
                failure = None
                try:
                    response = await client.get("/api/articles/feed", params={"limit": args.limit})
                    statuses[str(response.status_code)] += 1
                    if response.status_code != 200:
                        failure = "http_status"
                    else:
                        try:
                            body = response.json()
                            if not isinstance(body, dict) or not isinstance(body.get("articles"), list):
                                failure = "response_contract"
                        except ValueError:
                            failure = "invalid_json"
                except httpx.RequestError as exc:
                    # Record type only: request/response text may contain sensitive data.
                    failure = type(exc).__name__
                elapsed_ms = (time.perf_counter() - request_start) * 1000
                latencies.append(elapsed_ms)
                if failure:
                    failures[failure] += 1
                else:
                    successful_latencies.append(elapsed_ms)
                # Closed-loop pacing: do not burst to catch up when a request is slow.
                next_start = max(request_start + interval, time.perf_counter())

        await asyncio.gather(*(reader(index) for index in range(args.users)))
        # Include the final idle part of the requested observation window.
        # Otherwise fast responses inflate throughput by omitting the last
        # pacing interval (especially noticeable at one request per second).
        await asyncio.sleep(max(0, end - time.perf_counter()))
    elapsed = time.perf_counter() - start
    error_rate = sum(failures.values()) / len(latencies) if latencies else 1.0
    success_p95 = percentile(successful_latencies, .95)
    return {
        "scope": "local HTTP feed; real service/database only if configured by operator",
        "users": args.users, "requested_seconds": args.seconds, "elapsed_seconds": round(elapsed, 3),
        "pacing_ceiling_rps": args.rate, "feed_limit": args.limit,
        "requests": len(latencies), "successful_requests": len(successful_latencies),
        "achieved_rps": round(len(latencies) / elapsed, 3), "error_rate": error_rate,
        "status_counts": dict(statuses), "failure_counts": dict(failures),
        "all_requests_ms": {f"p{p}": percentile(latencies, p / 100) for p in (50, 95, 99)},
        "successful_requests_ms": {f"p{p}": percentile(successful_latencies, p / 100) for p in (50, 95, 99)},
        "targets": {"p95_ms": args.p95_target_ms, "max_error_rate": args.max_error_rate},
        "targets_met": success_p95 is not None and success_p95 < args.p95_target_ms and error_rate <= args.max_error_rate,
        "limitations": "Closed-loop feed traffic only; excludes login, ingestion, browser rendering, and SMTP. Slow responses reduce offered load.",
    }


def main():
    args, token = parse_args()
    report = asyncio.run(benchmark(args, token))
    output = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0 if report["targets_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
