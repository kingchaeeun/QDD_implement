"""
Small helper to inspect the raw /api/find-origin JSON response.

Run:
    cd C:\\08_QDD3\\quote-origin-pipeline
    set PYTHONPATH=C:\\08_QDD3\\quote-origin-pipeline  (Windows CMD)
    $env:PYTHONPATH=\"C:\\08_QDD3\\quote-origin-pipeline\"  (PowerShell)
    python scripts\\debug_api_raw.py
"""

import json

import requests


def main() -> None:
    url = "http://localhost:8000/api/find-origin"
    payload = {
        "quote_id": "debug-europe-1",
        "quote_content": "유럽은 약한 지도자들이 이끌어…쇠퇴하는 집단",
        "article_text": "유럽은 약한 지도자들이 이끌어…쇠퇴하는 집단",
        "article_date": "2025-12-10",
        "top_matches": 3,
        "debug": True,
    }

    print("POST", url)
    resp = requests.post(url, json=payload, timeout=300)
    print("status:", resp.status_code)
    print("body:")
    data = resp.json()
    print(json.dumps(data, ensure_ascii=False, indent=2))

    print("\nCandidates (keys only):")
    for i, cand in enumerate(data.get("candidates") or []):
        print(i, sorted(cand.keys()))


if __name__ == "__main__":
  main()


