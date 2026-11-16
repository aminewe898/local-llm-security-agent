"""lab (v2): sandboxed offensive tooling for the CTF agent. All execution runs inside the
isolated ctf-attacker container (no internet, no host). Adds endpoint discovery and a
structured, session-persistent HTTP client on top of raw shell. NO challenge solutions here —
these are the same affordances a human pentester gets from a proxy like Burp/ZAP."""
import base64, json, subprocess
from mcp.server.fastmcp import FastMCP

CONTAINER = "ctf-attacker"
TARGET = "http://ctf-juice:3000"
mcp = FastMCP("lab")


def _exec(argv, timeout=60):
    try:
        p = subprocess.run(["docker", "exec", CONTAINER, *argv],
                           capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
        return ((p.stdout or "") + (("\n[stderr] " + p.stderr) if p.stderr.strip() else "")).strip()
    except subprocess.TimeoutExpired:
        return f"[timed out after {timeout}s]"
    except Exception as e:
        return f"[lab error: {e}]"


@mcp.tool()
def lab_target() -> str:
    """The authorized target. OWASP Juice Shop at http://ctf-juice:3000 — an Angular single-page app
    with a REST API. IMPORTANT: its real API routes live in the app's JavaScript bundles, not in the
    HTML. Call http_map first to discover them instead of guessing paths."""
    return (f"Target: OWASP Juice Shop at {TARGET} (sandbox-only, you are authorized to test it). "
            "Angular SPA + REST API. Start with http_map to enumerate real endpoints.")


@mcp.tool()
def http_map() -> str:
    """Discover the target's REAL API endpoints by downloading its JavaScript bundles and extracting
    the route strings (e.g. /rest/user/login, /rest/basket, /api/Products). Use this FIRST — the SPA's
    endpoints are not in the HTML, so guessing /api/<Name> will usually fail. Returns a deduplicated list."""
    script = (
        "set -e; "
        "html=$(curl -s " + TARGET + "/); "
        "js=$(echo \"$html\" | grep -oE '[a-zA-Z0-9_.-]+\\.js' | sort -u); "
        "for f in $js; do curl -s " + TARGET + "/$f; done "
        "| grep -oE '\"/(rest|api)/[a-zA-Z0-9_{}:/.-]*\"' "
        "| tr -d '\"' | sort -u")
    out = _exec(["bash", "-lc", script], timeout=90)
    lines = [l for l in out.splitlines() if l.startswith("/")]
    if not lines:
        return "No endpoints extracted. Fallback: fetch the bundle yourself with lab_shell and grep it.\n" + out[:1500]
    return f"Discovered {len(lines)} endpoint patterns on {TARGET}:\n" + "\n".join(lines)


@mcp.tool()
def http_req(method: str, path: str, json_body: str = "", headers_json: str = "", use_session: bool = True) -> str:
    """Send one HTTP request to the target and get status + key headers + body. Keeps a PERSISTENT
    session (cookies and any captured auth token) across calls when use_session=true, so you can log in
    once and stay authenticated for later steps (IDOR, privileged actions). Payloads are sent exactly as
    given — no shell quoting to mangle SQL/JSON.
    - method: GET/POST/PUT/DELETE. path: e.g. /rest/user/login.
    - json_body: a JSON object string for the request body, e.g. {"email":"' OR 1=1--","password":"x"}.
    - headers_json: optional extra headers as a JSON object.
    A login response's token is captured automatically and reused as 'Authorization: Bearer ...'."""
    body_arg = base64.b64encode(json_body.encode()).decode() if json_body else "-"
    hdr_arg = base64.b64encode((headers_json or "{}").encode()).decode()
    return _exec(["python3", "/work/httpreq.py", method, path, body_arg, hdr_arg, "1" if use_session else "0"], timeout=45)


@mcp.tool()
def http_session_reset() -> str:
    """Clear the persistent HTTP session (forget cookies and captured token) to start as an anonymous user."""
    return _exec(["bash", "-lc", "rm -f /work/session.json && echo 'session cleared'"])


@mcp.tool()
def lab_shell(command: str, timeout_s: int = 60) -> str:
    """Run an arbitrary bash command in the sandbox (curl, python3, jq, openssl). Use for things the
    structured tools don't cover. Prefer http_req for API calls so sessions and payloads are handled cleanly."""
    return _exec(["bash", "-lc", command], timeout=max(1, min(int(timeout_s or 60), 180)))


if __name__ == "__main__":
    mcp.run()
