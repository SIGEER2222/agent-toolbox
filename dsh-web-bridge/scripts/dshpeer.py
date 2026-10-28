#!/usr/bin/env python3
"""DSH web session bridge: drive the user's real browser tab via tabbit-cli.

Why the browser: the dsh web host holds a kernel named-semaphore write lock on
mounted sessions (ACP session/resume and headless --session-id are both refused).
Reads are lock-free on session.v4.jsonl.zstd; writes must go through the host's
own channel — the typert connection held by the open browser tab.

Usage (Windows python, e.g. wpy):
  dshpeer.py tabs                                   # list tabs on 127.0.0.1:3080
  dshpeer.py resolve <ref>                          # ref -> session id + transcript
  dshpeer.py send <ref> -m "text" | -f msg.txt      # send (URL assert + busy wait)
  dshpeer.py wait <ref> [--timeout 300]             # wait for turn/end completed
  dshpeer.py read <ref> [--json]                    # last assistant text
  dshpeer.py ask <ref> -m "text" [--timeout 600]    # send+wait+read roundtrip
  dshpeer.py new --ws <workspace> -m "text"         # new session -> url/id

<ref> = full URL / session-<uuid> / 8-hex handle.
Send-safety lessons baked in (all observed in real runs):
  - assert page.url() still holds the session id before typing AND before the
    send click — tabs get navigated between calls and drafts can land in the
    wrong composer (happened for real, nearly sent);
  - Enter does NOT send: click the aria-label="send" button; while a turn or
    sub-agents run, composer goes contenteditable=false — wait for idle;
  - ?s=<sid> deep links open a NEW page inside the SPA — after goto, scan
    pages() and usePage() onto the spawned page;
  - each invocation runs `finish` on the task first, else spawned pages pile
    up across calls and the next bind dies on "N owned Playwright Pages";
  - verify the send by transcript user/message match (text prefix), not just
    composer-empty — the EPERM receipt race can skip JS entirely.
"""

from __future__ import annotations

import argparse
import glob
import io
import json
import os
import re
import subprocess
import sys
import time

TASK_NAME = "dsh-peer"
DSH_BASE = "http://127.0.0.1:3080"
DSH_ROOT = os.path.join(os.path.expanduser("~"), ".dsh")
LOCK_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".dshpeer.lock")
LOCK_STALE_S = 900
POLL_S = 3.0

COMPOSER_SEL = 'div[data-composer-input]'
STOP_SEL = 'button[aria-label="停止生成"], button:has-text("停止生成")'
SEND_SEL = 'button[aria-label="发送消息"], button:has-text("发送消息")'


# ---------- tabbit plumbing ----------

def tabbit_bin() -> str:
    path = os.environ.get("TABBIT_CLI") or os.path.expandvars(
        r"%LOCALAPPDATA%\Tabbit\LocalAgent\bin\tabbit-cli.exe")
    if not os.path.exists(path):
        raise SystemExit("tabbit-cli not found: %s (override with TABBIT_CLI)" % path)
    return path


NOFOCUS = os.environ.get("NOFOCUS_PY") or os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..", "..", "..", "deliverables", "nofocus", "nofocus.py")


def _guard(cmd: list) -> list:
    """Automation must not steal focus: guard restores foreground in ~40ms.
    NOFOCUS_OFF=1 disables."""
    if os.environ.get("NOFOCUS_OFF") or not os.path.exists(NOFOCUS):
        return cmd
    return [sys.executable, NOFOCUS, "guard", "--watch-exe", "Tabbit Browser", "--"] + cmd


def run_js(js: str, request_id: str, timeout_s: int, tab_id=None) -> dict:
    try:
        js.encode("ascii")
    except UnicodeEncodeError as e:
        raise SystemExit("injected JS must be pure ASCII (cp936 stdin): %s" % e)
    ms = min(180000, max(60000, timeout_s * 1000))
    cmd = [tabbit_bin(), "nodejs", "--task", TASK_NAME,
           "--request-id", request_id, "--timeout-ms", str(ms)]
    if tab_id is not None:
        cmd += ["--tab", str(tab_id)]
    cmd = _guard(cmd)
    try:
        proc = subprocess.run(cmd, input=js.encode("utf-8"),
                              capture_output=True, timeout=ms / 1000 + 30)
    except subprocess.TimeoutExpired:
        return {"status": "failed", "error": "tabbit-cli process timeout %ds" % (ms // 1000 + 30)}
    raw = proc.stdout.decode("utf-8", errors="replace")
    res = {}
    for line in reversed(raw.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                res = json.loads(line)
                break
            except json.JSONDecodeError:
                continue
    if not res:
        res = {"status": "failed",
               "error": (raw or proc.stderr.decode("utf-8", "replace"))[-800:].strip()}
    result = res.get("result") or {}
    if res.get("status") != "succeeded" and not res.get("error"):
        # EPERM receipt-rename race: JS may or may not have run — callers must
        # verify side effects (transcript / composer) rather than trust this.
        res["error"] = result.get("error") or result.get("errorName") or "tabbit call failed"
    return res


def value_of(res: dict) -> dict:
    if res.get("status") != "succeeded":
        return {}
    return res.get("result", {}).get("value", {}) or {}


def release_task() -> None:
    """Drop all tab claims under our task name (keep tabs open). Run at the top
    of every command: ?s= navigation spawns pages that accumulate as owned and
    make the next bind die on 'N owned Playwright Pages' timeouts."""
    try:
        subprocess.run(_guard([tabbit_bin(), "finish", "--task", TASK_NAME]),
                       capture_output=True, timeout=30)
    except Exception:
        pass


def list_tabs() -> list:
    proc = subprocess.run(_guard([tabbit_bin(), "create", "--task", TASK_NAME]),
                          capture_output=True, timeout=60)
    d = json.loads(proc.stdout.decode("utf-8", "replace"))
    return d.get("tabs", [])


def session_tab_candidates(sid: str) -> list:
    """Ordered bind candidates: session tabs > other 3080 tabs > blank/newtab."""
    avail = [t for t in list_tabs() if t.get("state") in ("available", "owned")]
    match, domain, blank = [], [], []
    for t in avail:
        u = t.get("url") or ""
        if sid in u:
            match.append(t["tabId"])
        elif u.startswith(DSH_BASE):
            domain.append(t["tabId"])
        elif u.startswith("about:") or "web.tabbit.com/newtab" in u:
            blank.append(t["tabId"])
    return match + domain + blank


# ---------- transcript reads (lock-free session.v4.jsonl.zstd) ----------

def resolve_ref(ref: str) -> tuple:
    """ref -> (session_uuid, transcript_path|None)."""
    m = re.search(r"session-([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", ref)
    if m:
        sid = "session-" + m.group(1)
    elif re.fullmatch(r"[0-9a-f]{8}", ref):
        hits = glob.glob(os.path.join(DSH_ROOT, "sessions", "*", "session-" + ref + "*"))
        if not hits:
            raise SystemExit("no session dir matches handle %s" % ref)
        sid = os.path.basename(hits[0])
    else:
        raise SystemExit("cannot parse session id from ref: %s" % ref)
    hits = glob.glob(os.path.join(DSH_ROOT, "sessions", "*", sid, "session.v4.jsonl.zstd"))
    return sid, (hits[0] if hits else None)


def read_events(path: str) -> list:
    """Fault-tolerant read: the transcript is appended live; drop a truncated
    tail frame and keep what we got."""
    import zstandard
    raw = open(path, "rb").read()
    out = b""
    try:
        r = zstandard.ZstdDecompressor().stream_reader(io.BytesIO(raw))
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            out += chunk
    except Exception:
        pass
    evs = []
    for line in out.split(b"\n"):
        line = line.strip()
        if not line:
            continue
        try:
            evs.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return evs


def event_text(e: dict) -> str:
    data = e.get("data") or {}
    content = (data.get("message") or {}).get("content") or data.get("content") or []
    return " ".join(c.get("text", "") for c in content
                    if isinstance(c, dict) and c.get("type") == "text")


def snapshot(path: str) -> dict:
    evs = read_events(path)
    n_user = 0
    last_assistant = ""
    last_turn_end_seq = -1
    last_seq = -1
    open_turn = False
    for e in evs:
        seq = e.get("seq", last_seq + 1)
        last_seq = seq
        t = e.get("type")
        if t == "user/message" and e.get("data", {}).get("content"):
            n_user += 1
        elif t == "assistant/message":
            txt = event_text(e)
            if txt.strip():
                last_assistant = txt
        elif t == "turn/start":
            open_turn = True
        elif t == "turn/end":
            open_turn = False
            if (e.get("data", {}).get("reason") or {}).get("kind") == "completed":
                last_turn_end_seq = seq
    return {"events": len(evs), "user_msgs": n_user, "last_seq": last_seq,
            "last_assistant": last_assistant, "last_turn_end_seq": last_turn_end_seq,
            "open_turn": open_turn}


def user_msg_seen(path: str, text_head: str, after_seq: int) -> bool:
    """Did a user/message starting with our text land after after_seq?
    (distinguishes real sends from auto-injected 'Time sampled' messages.)"""
    for e in read_events(path):
        if e.get("type") != "user/message" or e.get("seq", 0) <= after_seq:
            continue
        if event_text(e).startswith(text_head):
            return True
    return False


# ---------- JS fragments (pure ASCII; Chinese via \u escapes) ----------

# ensure + busy-wait + insert + click in ONE call — avoids re-acquisition
# between steps and the N-owned-pages timeout.
JS_SEND = r"""
const sid = %(sid)s;
const ws = %(ws)s;
const busyWaitMs = %(busyWait)d;
const ceEditable = async () => {
  const c = page.locator(%(composerSel)s).first();
  if (!(await c.count())) return null;
  return await c.getAttribute('contenteditable').catch(e => null);
};
if (!page.url().includes(sid)) {
  for (const p of pages()) if (p.url().includes(sid)) { await usePage(p); break; }
}
if (!page.url().includes(sid)) {
  await page.goto(%(home)s + '/', {waitUntil: 'commit', timeout: 30000}).catch(e => null);
  await page.waitForTimeout(4000);
  const sel = page.locator('button:has-text("\u9009\u62e9\u5de5\u4f5c\u533a")').first();
  if (ws && await sel.count()) {
    await sel.click(); await page.waitForTimeout(800);
    const opt = page.locator('button:has-text("' + ws + '")').first();
    if (await opt.count()) { await opt.click(); await page.waitForTimeout(2500); }
  }
  const more = page.locator('button.bhn1Oq_sessionOverflowButton').first();
  if (await more.count()) { await more.click().catch(e => null); await page.waitForTimeout(1200); }
  const n = await page.locator('div.YDXeBa_sessionRow').count();
  for (let i = 0; i < n && !page.url().includes(sid); i++) {
    try {
      await page.locator('div.YDXeBa_sessionRow').nth(i).click({timeout: 6000});
      await page.waitForTimeout(2200);
      for (const p of pages()) if (p.url().includes(sid)) { await usePage(p); break; }
      if (page.url().includes(sid)) break;
      const back = page.locator('button[aria-label="\u8fd4\u56de"], a[href="/"], button:has-text("\u4f1a\u8bdd")').first();
      await page.goto(%(home)s + '/', {waitUntil: 'commit', timeout: 20000}).catch(e => null);
      await page.waitForTimeout(2500);
    } catch (e) {}
  }
}
if (!page.url().includes(sid)) return {ok: false, reason: 'not-on-session', url: page.url()};
const isBusy = async () => {
  const ce = await page.locator(%(composerSel)s).first()
    .getAttribute('contenteditable').catch(e => null);
  const stop = await page.locator(%(stopSel)s).count() > 0;
  return ce !== 'true' || stop;
};
const deadline = Date.now() + busyWaitMs;
let busy = await isBusy();
while (busy && Date.now() < deadline) {
  await page.waitForTimeout(2000);
  busy = await isBusy();
}
if (busy) return {ok: false, reason: 'busy-timeout', url: page.url()};
const composer = page.locator(%(composerSel)s).first();
try { await composer.waitFor({state: 'visible', timeout: 20000}); }
catch (e) { return {ok: false, reason: 'no-composer', url: page.url()}; }
await composer.click({timeout: 10000});
await page.keyboard.press('Control+A');
await page.keyboard.press('Delete');
await page.keyboard.insertText(%(msg)s);
await page.waitForTimeout(400);
if (!page.url().includes(sid)) {
  await page.keyboard.press('Control+A'); await page.keyboard.press('Delete');
  return {ok: false, reason: 'wrong-url-before-send', url: page.url(), cleared: true};
}
const btn = page.locator(%(sendSel)s).first();
if (!(await btn.count()) || await btn.isDisabled()) {
  return {ok: false, reason: 'send-disabled', url: page.url()};
}
await btn.click({timeout: 10000});
await page.waitForTimeout(800);
const remaining = ((await composer.innerText()) || '').trim();
return {ok: true, composerEmpty: remaining.length === 0, url: page.url(),
        remaining: remaining.slice(0, 80)};
"""

JS_NEW = r"""
const ws = %(ws)s;
await page.goto(%(home)s + '/', {waitUntil: 'commit', timeout: 30000}).catch(e => null);
await page.waitForTimeout(4000);
const sel = page.locator('button:has-text("\u9009\u62e9\u5de5\u4f5c\u533a")').first();
if (await sel.count()) {
  await sel.click(); await page.waitForTimeout(800);
  const opt = page.locator('button:has-text("' + ws + '")').first();
  if (!(await opt.count())) return {ok: false, reason: 'ws-not-found', url: page.url()};
  await opt.click(); await page.waitForTimeout(2500);
}
let nb = page.locator('button[aria-label*="\u65b0\u5efa\u4f1a\u8bdd"], button:has-text("\u65b0\u4f1a\u8bdd")').first();
let nbFound = await nb.count();
const nbDeadline = Date.now() + 20000;
while (!nbFound && Date.now() < nbDeadline) {
  await page.waitForTimeout(1000);
  nbFound = await nb.count();
}
if (!nbFound) {
  await page.keyboard.press('Control+Alt+n').catch(e => null);
  await page.waitForTimeout(1500);
} else {
  await nb.click();
}
await page.waitForTimeout(4000);
let target = null;
for (const p of pages()) if (/s=session-/.test(p.url())) target = p;
if (target && target !== page) await usePage(target);
const composer = page.locator(%(composerSel)s).first();
try { await composer.waitFor({state: 'visible', timeout: 20000}); }
catch (e) { return {ok: false, reason: 'no-composer', url: page.url()}; }
await composer.click({timeout: 10000});
await page.keyboard.insertText(%(msg)s);
const btn = page.locator(%(sendSel)s).first();
let enabled = false;
const enDeadline = Date.now() + 5000;
while (Date.now() < enDeadline) {
  if (await btn.count() && !(await btn.isDisabled())) { enabled = true; break; }
  await page.waitForTimeout(400);
}
if (!enabled) {
  const draft = ((await composer.innerText()) || '').trim().slice(0, 60);
  return {ok: false, reason: 'send-disabled', url: page.url(), draft};
}
await btn.click({timeout: 10000});
let sid = null;
const deadline = Date.now() + 45000;
while (Date.now() < deadline) {
  const m = page.url().match(/s=(session-[0-9a-f-]+)/);
  if (m) { sid = m[1]; break; }
  await page.waitForTimeout(1000);
}
return {ok: !!sid, sid, url: page.url()};
"""


# ---------- business logic ----------

def acquire_lock(force: bool) -> None:
    if os.path.exists(LOCK_PATH):
        age = time.time() - os.path.getmtime(LOCK_PATH)
        if age > LOCK_STALE_S or force:
            os.remove(LOCK_PATH)
        else:
            print("another dsh-peer call holds the lock (%.0fs old)" % age,
                  file=sys.stderr)
            raise SystemExit(4)
    with open(LOCK_PATH, "w", encoding="utf-8") as f:
        f.write(str(os.getpid()))


def release_lock() -> None:
    if os.path.exists(LOCK_PATH):
        os.remove(LOCK_PATH)


def do_send(sid: str, path, msg: str, tab_id, busy_wait: int, ws=None) -> dict:
    snap0 = snapshot(path) if path else {"last_seq": 0}
    res = run_js(JS_SEND % {
        "sid": json.dumps(sid), "msg": json.dumps(msg), "ws": json.dumps(ws),
        "url": json.dumps("%s/?s=%s" % (DSH_BASE, sid)),
        "home": json.dumps(DSH_BASE),
        "composerSel": json.dumps(COMPOSER_SEL), "sendSel": json.dumps(SEND_SEL),
        "stopSel": json.dumps(STOP_SEL), "busyWait": busy_wait * 1000,
    }, "send-%d" % int(time.time()), busy_wait + 60, tab_id=tab_id)
    v = value_of(res)
    out = {"sent": False}
    if res.get("status") != "succeeded" or not v.get("ok"):
        out["error"] = res.get("error") or v.get("reason")
        out["v"] = v
    if v.get("ok"):
        out["sent"] = True
        out["composerEmpty"] = v.get("composerEmpty")
    if path:
        head = msg[:24]
        base_seq = snap0.get("last_seq", 0)
        deadline = time.time() + 15
        while time.time() < deadline:
            if user_msg_seen(path, head, base_seq):
                out["sent"] = True
                out["transcriptConfirmed"] = True
                return out
            time.sleep(1.5)
        out["transcriptConfirmed"] = False
    return out


def do_wait(path: str, base_seq: int, timeout: int) -> dict:
    """Wait for turn/end(completed) after base_seq."""
    deadline = time.time() + timeout
    last_mtime = 0
    while time.time() < deadline:
        try:
            mt = os.path.getmtime(path)
        except OSError:
            mt = 0
        if mt != last_mtime:
            last_mtime = mt
            snap = snapshot(path)
            if snap["last_turn_end_seq"] > base_seq:
                return {"done": True, "snap": snap}
        time.sleep(POLL_S)
    return {"done": False}


def send_round(sid: str, path, msg: str, args) -> dict:
    """Try bind candidates in order; a wedged page times acquisition out —
    skip to the next."""
    cands = [args.tab] if getattr(args, "tab", None) else session_tab_candidates(sid)
    if not cands:
        cands = [None]
    out = {"sent": False, "error": "no-candidate"}
    for cand in cands:
        out = do_send(sid, path, msg, cand, args.busy_wait, ws=getattr(args, "ws", None))
        if out.get("sent") or out.get("transcriptConfirmed"):
            return out
        reason = str((out.get("v") or {}).get("reason") or out.get("error") or "")
        if "Timeout" in reason or "owned Playwright" in reason or "EPERM" in reason:
            continue
        return out
    return out


def read_msg(args) -> str:
    if args.file:
        with open(args.file, encoding="utf-8") as f:
            return f.read().strip()
    if not args.message:
        raise SystemExit("missing message: -m or -f (use -f for non-ASCII)")
    return args.message.strip()


# ---------- subcommands ----------

def cmd_tabs(_args) -> int:
    for t in list_tabs():
        if DSH_BASE in (t.get("url") or ""):
            print("%s\t%s\t%s | %s" % (t["tabId"], t["state"],
                                       (t.get("title") or "")[:50], t["url"]))
    return 0


def cmd_resolve(args) -> int:
    sid, path = resolve_ref(args.ref)
    print(json.dumps({"sid": sid, "transcript": path}, ensure_ascii=False))
    return 0


def cmd_send(args) -> int:
    sid, path = resolve_ref(args.ref)
    msg = read_msg(args)
    acquire_lock(args.force)
    try:
        release_task()
        out = send_round(sid, path, msg, args)
    finally:
        release_lock()
    out["sid"] = sid
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if out.get("sent") else 2


def cmd_wait(args) -> int:
    _sid, path = resolve_ref(args.ref)
    if not path:
        raise SystemExit("no transcript: " + args.ref)
    base = snapshot(path)["last_seq"] if args.from_now else args.from_seq
    r = do_wait(path, base, args.timeout)
    out = {"done": r.get("done")}
    if r.get("snap"):
        out["snap"] = {k: r["snap"].get(k) for k in ("last_seq", "user_msgs")}
    print(json.dumps(out, ensure_ascii=False))
    return 0 if r.get("done") else 3


def cmd_read(args) -> int:
    _sid, path = resolve_ref(args.ref)
    if not path:
        raise SystemExit("no transcript: " + args.ref)
    txt = snapshot(path)["last_assistant"]
    if args.json:
        print(json.dumps({"text": txt}, ensure_ascii=False))
    else:
        print(txt)
    return 0


def cmd_ask(args) -> int:
    sid, path = resolve_ref(args.ref)
    msg = read_msg(args)
    acquire_lock(args.force)
    try:
        release_task()
        base_seq = snapshot(path)["last_seq"] if path else 0
        out = send_round(sid, path, msg, args)
        if not out.get("sent"):
            print(json.dumps(out, ensure_ascii=False), file=sys.stderr)
            return 2
        r = do_wait(path, base_seq, args.timeout)
        if not r.get("done"):
            print(json.dumps({"sent": True, "done": False,
                              "hint": "timed out; keep polling with wait/read"},
                             ensure_ascii=False), file=sys.stderr)
            return 3
        print(snapshot(path)["last_assistant"])
    finally:
        release_lock()
    return 0


def cmd_new(args) -> int:
    msg = read_msg(args)
    acquire_lock(args.force)
    try:
        release_task()
        res = run_js(JS_NEW % {
            "ws": json.dumps(args.ws), "home": json.dumps(DSH_BASE),
            "msg": json.dumps(msg), "composerSel": json.dumps(COMPOSER_SEL),
            "sendSel": json.dumps(SEND_SEL),
        }, "new-%d" % int(time.time()), 170, tab_id=args.tab)
        v = value_of(res)
        if res.get("status") != "succeeded":
            v = {"ok": False, "error": res.get("error")}
        if v.get("ok") and args.wait:
            _sid, path = resolve_ref(v["sid"])
            if path:
                r = do_wait(path, 0, args.wait)
                v["reply"] = snapshot(path)["last_assistant"] if r.get("done") else None
                v["waited"] = r.get("done")
    finally:
        release_lock()
    if args.wait and v.get("reply"):
        print(v["reply"])
    else:
        print(json.dumps(v, ensure_ascii=False, indent=2))
    return 0 if v.get("ok") else 2


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="DSH web session bridge (tabbit drives the real browser tab)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("tabs").set_defaults(func=cmd_tabs)
    rs = sub.add_parser("resolve")
    rs.add_argument("ref")
    rs.set_defaults(func=cmd_resolve)

    def common(p):
        p.add_argument("ref")
        p.add_argument("-m", "--message")
        p.add_argument("-f", "--file")
        p.add_argument("--ws", help="workspace display name for fallback navigation")
        p.add_argument("--tab", type=int, help="force-bind this tabId")
        p.add_argument("--busy-wait", type=int, default=120)
        p.add_argument("--force", action="store_true")

    sd = sub.add_parser("send")
    common(sd)
    sd.set_defaults(func=cmd_send)

    wt = sub.add_parser("wait")
    wt.add_argument("ref")
    wt.add_argument("--timeout", type=int, default=300)
    wt.add_argument("--from-seq", type=int, default=0)
    wt.add_argument("--from-now", action="store_true")
    wt.set_defaults(func=cmd_wait)

    rd = sub.add_parser("read")
    rd.add_argument("ref")
    rd.add_argument("--json", action="store_true")
    rd.set_defaults(func=cmd_read)

    ak = sub.add_parser("ask")
    common(ak)
    ak.add_argument("--timeout", type=int, default=600)
    ak.set_defaults(func=cmd_ask)

    nw = sub.add_parser("new")
    nw.add_argument("--ws", required=True)
    nw.add_argument("-m", "--message")
    nw.add_argument("-f", "--file")
    nw.add_argument("--tab", type=int)
    nw.add_argument("--wait", type=int, default=0,
                    help="wait this many seconds for the first reply and print it")
    nw.add_argument("--force", action="store_true")
    nw.set_defaults(func=cmd_new)
    return ap


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
