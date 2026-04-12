#!/usr/bin/env python3
"""
Smoke-test a deployed Space (or local server) for hackathon-style checks:
  GET /health  -> 200
  POST /reset  -> 200 with empty body (no Content-Type / no JSON)
  POST /reset  -> 200 with {}

Usage:
  python scripts/verify_hackathon_endpoints.py https://YOUR-SPACE.hf.space
  python scripts/verify_hackathon_endpoints.py http://127.0.0.1:7860
"""
from __future__ import annotations

import sys
from urllib.parse import urlparse

import requests


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__.strip())
        return 2
    base = sys.argv[1].rstrip("/")
    p = urlparse(base)
    if not p.scheme or not p.netloc:
        print("Invalid URL", file=sys.stderr)
        return 2

    s = requests.Session()
    r = s.get(f"{base}/health", timeout=15)
    print("GET /health", r.status_code, r.text[:300])
    if r.status_code != 200:
        return 1
    try:
        j = r.json()
        print("  reset_handler:", j.get("reset_handler", "(missing — old image?)"))
    except Exception:
        pass

    r = s.post(f"{base}/reset", data=None, timeout=30)
    print("POST /reset (no body)", r.status_code, r.text[:200])
    if r.status_code != 200:
        return 1

    r = s.post(f"{base}/reset", json={}, timeout=30)
    print("POST /reset {}", r.status_code, r.text[:120])
    if r.status_code != 200:
        return 1

    print("OK — reset accepts empty body and {}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
