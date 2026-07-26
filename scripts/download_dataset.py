from __future__ import annotations

import argparse
import hashlib
import urllib.request
from pathlib import Path

URL = (
    "https://huggingface.co/datasets/samaya-ai/FrontierFinance/resolve/"
    "21da0514a15c51774ff836c46f290681c0ad91ee/frontier_finance_public.jsonl"
)
EXPECTED_SHA256 = "a82874d7a587baf6f1ebe79b95fa1c3090260d3661c544f4496056d338e313c4"


def main() -> int:
    parser = argparse.ArgumentParser(description="Download and verify the public dataset.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/original/frontier_finance_public.jsonl"),
    )
    args = parser.parse_args()
    request = urllib.request.Request(URL, headers={"User-Agent": "frontier-finance-repro/0.1"})
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"SHA-256 mismatch: expected {EXPECTED_SHA256}, got {digest}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    print(f"verified={args.output} sha256={digest} bytes={len(payload)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
