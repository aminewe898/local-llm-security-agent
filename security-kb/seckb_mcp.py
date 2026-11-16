"""seckb: local security knowledge MCP server (stdio).
Tools: sec_search (offline FTS over ATT&CK, CWE, CAPEC, CISA KEV, OWASP), sec_get (full entry),
cve_lookup (live NVD API, keyless, plus local KEV flag)."""
import json, os, re, sqlite3, urllib.request

from mcp.server.fastmcp import FastMCP

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seckb.db")
mcp = FastMCP("seckb")


def _db():
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)


def _fts(query: str, source: str | None, limit: int, mode: str):
    toks = [t for t in re.findall(r"[\w.-]+", query.lower()) if len(t) > 1][:12]
    if not toks:
        return []
    q = f" {mode} ".join(f'"{t}"' for t in toks)
    sql = "select id, source, title, snippet(docs, 3, '[', ']', ' … ', 24), url from docs where docs match ?"
    args = [q]
    if source:
        sql += " and source = ?"
        args.append(source)
    sql += " order by bm25(docs, 10.0, 1.0, 5.0, 1.0, 0.0) limit ?"
    args.append(limit)
    with _db() as db:
        return db.execute(sql, args).fetchall()


@mcp.tool()
def sec_search(query: str, source: str = "", limit: int = 8) -> str:
    """Search the offline security knowledge base. Sources: attack (MITRE ATT&CK techniques/groups/
    mitigations), cwe (weaknesses), capec (attack patterns), kev (CISA Known Exploited Vulnerabilities),
    owasp (OWASP Cheat Sheets). Exact IDs work too: T1059, CWE-79, CAPEC-66, CVE-2024-3400.
    Leave source empty to search everything. Returns id, title, snippet and URL per hit."""
    limit = max(1, min(int(limit or 8), 20))
    src = source.strip().lower() or None
    with _db() as db:
        exact = db.execute("select id, source, title, substr(body,1,240), url from docs where id = ? collate nocase",
                           [query.strip().upper() if not query.lower().startswith("owasp") else query.strip()]).fetchall()
    rows = exact or _fts(query, src, limit, "AND") or _fts(query, src, limit, "OR")
    if not rows:
        return "No matches. Try fewer or different words, or another source."
    return "\n\n".join(f"{r[0]} [{r[1]}] {r[2]}\n  {r[3]}\n  {r[4]}" for r in rows)


@mcp.tool()
def sec_get(id: str) -> str:
    """Full text of one entry by its id (e.g. T1566.001, CWE-89, CAPEC-66, CVE-2023-4966, OWASP:SQL_Injection_Prevention_Cheat_Sheet#2)."""
    with _db() as db:
        r = db.execute("select id, source, title, body, url from docs where id = ? collate nocase", [id.strip()]).fetchone()
    if not r:
        return f"No entry {id}. Use sec_search first."
    return f"{r[0]} [{r[1]}] {r[2]}\nSource: {r[4]}\n\n{r[3][:7000]}"


@mcp.tool()
def cve_lookup(cve_id: str) -> str:
    """Live details for one CVE from NVD (description, CVSS, CWE, dates, references) plus whether CISA lists it
    as actively exploited. Needs internet; keyless NVD access is rate-limited, so look up one CVE at a time."""
    cid = cve_id.strip().upper()
    if not re.fullmatch(r"CVE-\d{4}-\d{4,}", cid):
        return "Give an id like CVE-2024-3400."
    with _db() as db:
        kev = db.execute("select body from docs where id = ? and source='kev'", [cid]).fetchone()
    try:
        req = urllib.request.Request(f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cid}",
                                     headers={"User-Agent": "seckb-local/1.0"})
        data = json.load(urllib.request.urlopen(req, timeout=30))
    except Exception as e:
        return f"NVD lookup failed ({e}). Local KEV entry: {kev[0] if kev else 'not in KEV'}"
    if not data.get("vulnerabilities"):
        return f"{cid} not found in NVD. KEV: {kev[0] if kev else 'not listed'}"
    c = data["vulnerabilities"][0]["cve"]
    desc = next((d["value"] for d in c.get("descriptions", []) if d["lang"] == "en"), "")
    metrics = []
    for key in ("cvssMetricV40", "cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
        for m in c.get("metrics", {}).get(key, [])[:1]:
            d = m["cvssData"]
            metrics.append(f"{key[10:]}: {d.get('baseScore')} {d.get('baseSeverity', m.get('baseSeverity', ''))} {d.get('vectorString', '')}")
    cwes = sorted({d["value"] for w in c.get("weaknesses", []) for d in w.get("description", [])})
    refs = [r["url"] for r in c.get("references", [])][:6]
    return (f"{cid}  published {c.get('published', '')[:10]}, modified {c.get('lastModified', '')[:10]}, status {c.get('vulnStatus')}\n"
            f"{desc}\nCVSS: {'; '.join(metrics) or 'none yet'}\nWeaknesses: {', '.join(cwes) or 'n/a'}\n"
            f"Actively exploited (CISA KEV): {'YES - ' + kev[0] if kev else 'not listed'}\n"
            f"References:\n" + "\n".join(refs) + f"\nSource: https://nvd.nist.gov/vuln/detail/{cid}")


if __name__ == "__main__":
    mcp.run()
