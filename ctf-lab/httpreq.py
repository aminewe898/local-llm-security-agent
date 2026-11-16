"""Runs INSIDE the ctf-attacker sandbox. Structured HTTP with a persistent session
(cookies + bearer token) kept in /work/session.json, so multi-step exploits (login -> use token)
work and injection payloads aren't mangled by shell quoting.
Usage: python3 httpreq.py <method> <path> <body_b64> <headers_b64> <use_session:0|1>"""
import base64, json, os, sys, requests

BASE = "http://ctf-juice:3000"
SF = "/work/session.json"
method, path, body_b64, hdr_b64, use_session = sys.argv[1:6]
use_session = use_session == "1"

sess = {"cookies": {}, "token": ""}
if use_session and os.path.exists(SF):
    try:
        sess = json.load(open(SF))
    except Exception:
        pass

headers = json.loads(base64.b64decode(hdr_b64) or b"{}")
body_raw = base64.b64decode(body_b64).decode() if body_b64 != "-" else None
if use_session and sess.get("token") and "authorization" not in {k.lower() for k in headers}:
    headers["Authorization"] = "Bearer " + sess["token"]

kw = {"headers": headers, "cookies": sess.get("cookies", {}), "timeout": 30, "allow_redirects": False}
if body_raw is not None:
    # send as JSON if it parses, else raw
    try:
        kw["json"] = json.loads(body_raw)
    except Exception:
        kw["data"] = body_raw
        headers.setdefault("Content-Type", "application/x-www-form-urlencoded")

url = BASE + (path if path.startswith("/") else "/" + path)
try:
    r = requests.request(method.upper(), url, **kw)
except Exception as e:
    print(f"[request error] {e}")
    sys.exit(0)

# capture auth token + cookies for later steps
if use_session:
    sess.setdefault("cookies", {}).update(r.cookies.get_dict())
    try:
        j = r.json()
        tok = (j.get("authentication") or {}).get("token") or j.get("token")
        if tok:
            sess["token"] = tok
    except Exception:
        pass
    json.dump(sess, open(SF, "w"))

ct = r.headers.get("Content-Type", "")
print(f"HTTP {r.status_code}  ({len(r.content)} bytes, {ct})")
show = {k: r.headers[k] for k in ("Location", "Set-Cookie", "WWW-Authenticate") if k in r.headers}
if show:
    print("headers:", json.dumps(show))
if use_session and sess.get("token"):
    print(f"[session: authenticated, token captured ...{sess['token'][-12:]}]")
body = r.text
if "application/json" in ct:
    try:
        body = json.dumps(r.json(), indent=1)
    except Exception:
        pass
print("---")
print(body[:4000])
