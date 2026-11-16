"""Runs INSIDE the ctf-attacker sandbox (V4). Structured HTTP with:
 - persistent session (cookies + bearer token) in /work/session.json
 - a LOOP GUARD: counts identical (method,path,body) requests in /work/reqlog.json; warns on repeat,
   blocks after 3 so the agent is forced to change approach instead of looping.
Usage: python3 httpreq4.py <method> <path> <body_b64> <headers_b64> <use_session:0|1>"""
import base64, hashlib, json, os, sys, requests

BASE = "http://ctf-juice:3000"
SF, RL = "/work/session.json", "/work/reqlog.json"
method, path, body_b64, hdr_b64, use_session = sys.argv[1:6]
use_session = use_session == "1"
body_raw = base64.b64decode(body_b64).decode() if body_b64 != "-" else None
headers = json.loads(base64.b64decode(hdr_b64) or b"{}")

# --- loop guard -------------------------------------------------------------
sig = hashlib.sha1(f"{method} {path} {body_raw}".encode()).hexdigest()[:16]
log = {}
if os.path.exists(RL):
    try: log = json.load(open(RL))
    except Exception: log = {}
log[sig] = log.get(sig, 0) + 1
json.dump(log, open(RL, "w"))
n = log[sig]
if n >= 3:
    print(f"BLOCKED by loop guard: you have sent this EXACT request {n} times and the result will not "
          f"change. Do NOT repeat it. Change the path, the parameter name, or the payload — or call `note` "
          f"to record what you have learned and form a new hypothesis.")
    sys.exit(0)

sess = {"cookies": {}, "token": ""}
if use_session and os.path.exists(SF):
    try: sess = json.load(open(SF))
    except Exception: pass
if use_session and sess.get("token") and "authorization" not in {k.lower() for k in headers}:
    headers["Authorization"] = "Bearer " + sess["token"]

kw = {"headers": headers, "cookies": sess.get("cookies", {}), "timeout": 30, "allow_redirects": False}
if body_raw is not None:
    try: kw["json"] = json.loads(body_raw)
    except Exception:
        kw["data"] = body_raw; headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

try:
    r = requests.request(method.upper(), BASE + (path if path.startswith("/") else "/" + path), **kw)
except Exception as e:
    print(f"[request error] {e}"); sys.exit(0)

if use_session:
    sess.setdefault("cookies", {}).update(r.cookies.get_dict())
    try:
        tok = (r.json().get("authentication") or {}).get("token") or r.json().get("token")
        if tok: sess["token"] = tok
    except Exception: pass
    json.dump(sess, open(SF, "w"))

ct = r.headers.get("Content-Type", "")
out = [f"HTTP {r.status_code}  ({len(r.content)} bytes, {ct})"]
if n == 2:
    out.append("[loop guard: you already sent this identical request once; the result is unchanged. "
               "Next identical repeat will be blocked — change your approach.]")
show = {k: r.headers[k] for k in ("Location", "Set-Cookie", "WWW-Authenticate") if k in r.headers}
if show: out.append("headers: " + json.dumps(show))
if use_session and sess.get("token"):
    out.append(f"[session: authenticated, token ...{sess['token'][-10:]}]")
body = r.text
if "application/json" in ct:
    try: body = json.dumps(r.json(), indent=1)
    except Exception: pass
out.append("---"); out.append(body[:4000])
print("\n".join(out))
