#!/usr/bin/env python3
"""ClinePass OpenAI-compatible API caller.

- Endpoint: https://api.cline.bot/api/v1/chat/completions
- Auth: CLINE_API_KEY env var (create at app.cline.bot Settings > API Keys)
- Model: must use cline-pass/ prefix, otherwise billed as pay-as-you-go credits.
- Upstream pinning (linux.sb trick, unverified locally):
    Vercel/planner pipeline  -> providerOptions.gateway.only
    OpenRouter/direct        -> provider.only
  Wrong field is silently ignored; probe with a bogus value like ["__probe__"]
  and check for "No available providers match" to learn which pipeline a model uses.

Usage:
  python tools/clinepass_call.py --model cline-pass/deepseek-v4.1-flash --prompt "hi"
  python tools/clinepass_call.py --model cline-pass/deepseek-v4.1-flash \
      --pin deepseek --pin-style gateway --prompt "..."
  python tools/clinepass_call.py --probe --model cline-pass/glm-5.3 --prompt "hi"
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

API = "https://api.cline.bot/api/v1/chat/completions"


def call(model: str, prompt: str, pin: str | None, pin_style: str | None,
         max_tokens: int | None = None, stream: bool = False) -> dict:
    key = os.environ.get("CLINE_API_KEY")
    if not key:
        kf = os.path.expanduser("~/.cline_api_key")
        if os.path.exists(kf):
            key = open(kf, encoding="utf-8").read().strip()
    if not key:
        sys.exit("CLINE_API_KEY not set (env or ~/.cline_api_key)")

    body: dict = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": stream,
    }
    if max_tokens:
        body["max_tokens"] = max_tokens
    if pin and pin_style == "gateway":
        body["providerOptions"] = {"gateway": {"only": [pin]}}
    elif pin and pin_style == "provider":
        body["provider"] = {"only": [pin]}

    req = urllib.request.Request(
        API,
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            r = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return {"http_error": e.code, "body": e.read().decode(errors="replace")}
    # API wraps the OpenAI payload in {"data": ..., "success": true}
    if isinstance(r, dict) and isinstance(r.get("data"), dict) and "choices" in r["data"]:
        return r["data"]
    return r


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="cline-pass/deepseek-v4.1-flash")
    ap.add_argument("--prompt", default="Say OK")
    ap.add_argument("--pin", help="upstream slug, e.g. deepseek / zai / z-ai")
    ap.add_argument("--pin-style", choices=["gateway", "provider"])
    ap.add_argument("--probe", action="store_true",
                    help="pin to bogus __probe__ on both styles to detect pipeline")
    ap.add_argument("--max-tokens", type=int, default=None)
    args = ap.parse_args()

    if args.probe:
        for style in ("gateway", "provider"):
            r = call(args.model, args.prompt, "__probe__", style)
            print(f"=== pin_style={style} ===")
            print(json.dumps(r, ensure_ascii=False)[:2000])
        return

    r = call(args.model, args.prompt, args.pin, args.pin_style, args.max_tokens)
    if "choices" in r:
        msg = r["choices"][0].get("message", {})
        print(msg.get("content", ""))
        meta = {
            "model": r.get("model"),
            "provider": r.get("provider"),
            "usage": r.get("usage"),
            "provider_metadata": r.get("provider_metadata"),
        }
        print("---meta---", file=sys.stderr)
        print(json.dumps(meta, ensure_ascii=False), file=sys.stderr)
    else:
        print(json.dumps(r, ensure_ascii=False, indent=2)[:4000])


if __name__ == "__main__":
    main()
