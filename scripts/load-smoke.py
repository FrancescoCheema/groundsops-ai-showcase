import argparse
import concurrent.futures
import statistics
import time
import urllib.request


def request(url: str) -> tuple[bool, float]:
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            ok = 200 <= response.status < 300
    except Exception:
        ok = False
    return ok, (time.perf_counter() - started) * 1000


parser = argparse.ArgumentParser()
parser.add_argument("--url", required=True)
parser.add_argument("--requests", type=int, default=500)
parser.add_argument("--concurrency", type=int, default=25)
parser.add_argument("--p95-ms", type=float, default=750)
parser.add_argument("--max-error-rate", type=float, default=0.01)
args = parser.parse_args()
with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
    results = list(pool.map(lambda _: request(args.url), range(args.requests)))
latencies = sorted(value for _, value in results)
p95 = latencies[max(0, int(len(latencies) * 0.95) - 1)]
errors = sum(1 for ok, _ in results if not ok)
error_rate = errors / len(results)
print(
    f"requests={len(results)} errors={errors} error_rate={error_rate:.4f} "
    f"p95_ms={p95:.2f} median_ms={statistics.median(latencies):.2f}"
)
if error_rate > args.max_error_rate or p95 > args.p95_ms:
    raise SystemExit(1)
