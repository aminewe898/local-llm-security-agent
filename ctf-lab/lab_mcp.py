"""lab: the ONLY execution path for the CTF agent. Runs a shell command inside the
isolated 'ctf-attacker' container (no internet, no host mounts). Target = http://ctf-juice:3000.
Nothing here touches the host: the agent controls only the command string run in the sandbox."""
import subprocess
from mcp.server.fastmcp import FastMCP

CONTAINER = "ctf-attacker"
TARGET = "http://ctf-juice:3000"
MAX_OUT = 14000

mcp = FastMCP("lab")


@mcp.tool()
def lab_shell(command: str, timeout_s: int = 60) -> str:
    """Run a bash command inside the sandboxed attacker container and return its combined
    stdout+stderr. The lab target (OWASP Juice Shop) is at http://ctf-juice:3000. You have
    curl, python3 (with requests), jq, openssl. No internet, no host access — only the target.
    Example: lab_shell("curl -s -i http://ctf-juice:3000/rest/products/search?q=test")."""
    timeout_s = max(1, min(int(timeout_s or 60), 180))
    try:
        p = subprocess.run(["docker", "exec", CONTAINER, "bash", "-lc", command],
                           capture_output=True, text=True, timeout=timeout_s, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return f"[timed out after {timeout_s}s]"
    except Exception as e:
        return f"[lab error: {e}]"
    out = (p.stdout or "") + (("\n[stderr]\n" + p.stderr) if p.stderr.strip() else "")
    if len(out) > MAX_OUT:
        out = out[:MAX_OUT] + f"\n[...truncated, {len(out)} chars total]"
    return out.strip() or f"[no output, exit {p.returncode}]"


@mcp.tool()
def lab_target() -> str:
    """Return the base URL of the lab target you are assessing."""
    return (f"Target: OWASP Juice Shop at {TARGET} (reachable only from your sandbox). "
            "It is a deliberately vulnerable web app. Explore its REST API under /rest and /api, "
            "its Angular SPA, and files under /ftp. You are authorized to test ONLY this target.")


if __name__ == "__main__":
    mcp.run()
