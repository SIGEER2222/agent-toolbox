#!/usr/bin/env python3
"""Minimal Experiential Labs gateway caller.

- Base: https://api.experientiallabs.ai/v1 (OpenAI-compatible)
- Key: EXPLABS_API_KEY env var, or ~/.explabs_api_key file (xpl_ + 40 hex, shown once at creation)
- Models: GET /v1/models (keyed); public catalog GET /api/models (keyless)

Usage:
  python expl_call.py --model deepseek-v4.1-flash --prompt "Say OK"
  python expl_call.py --list | head
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

BASE = "https://api.experientiallabs.ai/v1"


def key() -> str:
    k = os.environ.get("EXPLABS_API_KEY")
    if not k:
        kf = os.path.expanduser("~/.explabs_api_key")
        if os.path.exists(kf):
            k = open(kf, encoding="utf-8").read().strip()
    if not k:
        sys.exit("EXPLABS_API_KEY not set (env or ~/.explabs_api_key)")
    return k


def req(path: str, body: dict | None = None) -> dict:
    r = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {key()}", "Content-Type": "application/json"},
        method="POST" if body else "GET",
    )
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode(errors="replace")}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="deepseek-v4.1-flash")
    ap.add_argument("--prompt", default="Say OK")
    ap.add_argument("--list", action="store_true", help="list callable model slugs")
    ap.add_argument("--stream", action="store_true")
    args = ap.parse_args()

    if args.list:
        r = req("/models")
        ids = [m["id"] for m in r.get("data", [])]
        print(f"{len(ids)} models")
        print("\n".join(ids))
        return

    r = req("/chat/completions", {
        "model": args.model,
        "messages": [{"role": "user", "content": args.prompt}],
        "stream": args.stream,
    })
    if "choices" in r:
        print(r["choices"][0]["message"].get("content", ""))
        print("---meta---", file=sys.stderr)
        print(json.dumps({"model": r.get("model"), "provider": r.get("provider"),
                          "usage": r.get("usage")}, ensure_ascii=False), file=sys.stderr)
    else:
        print(json.dumps(r, ensure_ascii=False, indent=2)[:4000])


if __name__ == "__main__":
    main()
