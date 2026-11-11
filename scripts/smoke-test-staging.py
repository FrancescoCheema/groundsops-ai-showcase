#!/usr/bin/env python3
"""Run unauthenticated smoke tests against a deployed GroundsOps environment."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass
from email.message import Message
from typing import Any
from uuid import uuid4


@dataclass
class CheckResult:
    name: str
    status: str
    latency_ms: float
    detail: str


def request(base_url: str, path: str, timeout: float, request_id: str | None = None):
    curl = shutil.which("curl.exe") if os.name == "nt" else shutil.which("curl")
    if not curl:
        raise OSError("curl is required but was not found on PATH")

    request_headers = {"Accept": "application/json, text/html;q=0.9"}
    if request_id:
        request_headers["X-Request-ID"] = request_id

    started = time.perf_counter()
    with tempfile.TemporaryDirectory() as directory:
        header_path = os.path.join(directory, "headers.txt")
        body_path = os.path.join(directory, "body.bin")
        command = [
            curl,
            "--silent",
            "--show-error",
            "--location",
            "--max-time",
            str(timeout),
            "--dump-header",
            header_path,
            "--output",
            body_path,
            "--write-out",
            "%{http_code}",
        ]
        for name, value in request_headers.items():
            command.extend(["--header", f"{name}: {value}"])
        command.append(f"{base_url.rstrip('/')}{path}")

        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout + 5,
        )
        if completed.returncode != 0:
            raise OSError(completed.stderr.strip() or f"curl exited {completed.returncode}")

        status = int(completed.stdout.strip())
        with open(body_path, "rb") as body_file:
            body = body_file.read()
        with open(header_path, encoding="iso-8859-1") as header_file:
            headers = parse_final_headers(header_file.read())
        return status, headers, body, elapsed_ms(started)


def parse_final_headers(raw_headers: str) -> Message:
    blocks = raw_headers.replace("\r\n", "\n").strip().split("\n\n")
    final_block = next(
        (block for block in reversed(blocks) if block.startswith("HTTP/")),
        "",
    )
    if not final_block:
        raise ValueError("curl returned no HTTP response headers")
    lines = final_block.splitlines()
    headers = Message()
    for line in lines[1:]:
        if ":" in line:
            name, value = line.split(":", 1)
            headers[name.strip()] = value.strip()
    return headers


def elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


def decode_json(body: bytes) -> dict[str, Any]:
    value = json.loads(body.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("response is not a JSON object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.getenv("STAGING_URL", ""))
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--max-latency-ms", type=float, default=5000)
    args = parser.parse_args()
    if not args.base_url:
        parser.error("--base-url or STAGING_URL is required")

    results: list[CheckResult] = []

    def record(name: str, ok: bool, latency: float, detail: str) -> None:
        if latency > args.max_latency_ms:
            ok = False
            detail = f"{detail}; latency exceeded {args.max_latency_ms:.0f} ms"
        results.append(CheckResult(name, "pass" if ok else "fail", latency, detail))

    try:
        status, headers, body, latency = request(args.base_url, "/", args.timeout)
        html = body.decode("utf-8", errors="replace").lower()
        record("frontend", status == 200 and "<html" in html, latency, f"HTTP {status}")

        expected_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=(self), geolocation=(self)",
        }
        missing = [
            name
            for name, expected in expected_headers.items()
            if headers.get(name, "").strip() != expected
        ]
        record(
            "security_headers",
            not missing,
            latency,
            "all required headers present" if not missing else f"missing/invalid: {missing}",
        )

        request_id = f"smoke-{uuid4()}"
        status, headers, body, latency = request(
            args.base_url, "/health", args.timeout, request_id
        )
        payload = decode_json(body)
        record(
            "health",
            status == 200 and payload.get("status") == "healthy",
            latency,
            f"HTTP {status}; status={payload.get('status')}",
        )
        returned_id = headers.get("X-Request-ID", "")
        record(
            "request_id",
            returned_id == request_id,
            latency,
            (
                "request ID preserved"
                if returned_id == request_id
                else "request ID missing/mismatched"
            ),
        )

        status, _, body, latency = request(args.base_url, "/ready", args.timeout)
        payload = decode_json(body)
        record(
            "readiness",
            status == 200 and payload.get("status") == "ready",
            latency,
            f"HTTP {status}; status={payload.get('status')}",
        )

        status, _, _, latency = request(
            args.base_url, "/api/v1/customers", args.timeout
        )
        record(
            "authentication_boundary",
            status == 401,
            latency,
            f"HTTP {status}; expected 401 without a bearer token",
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        results.append(CheckResult("runner", "fail", 0, str(exc)))

    report = {"base_url": args.base_url, "checks": [asdict(result) for result in results]}
    print(json.dumps(report, indent=2))
    return 1 if any(result.status == "fail" for result in results) else 0


if __name__ == "__main__":
    sys.exit(main())
