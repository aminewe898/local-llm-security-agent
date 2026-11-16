"""Build a local full-text index (SQLite FTS5) over security reference data.
Sources in ./data: MITRE ATT&CK (enterprise), CWE, CAPEC, CISA KEV, OWASP Cheat Sheets.
Usage: python -I build_index.py   -> writes seckb.db next to this file
"""
import glob, json, os, re, sqlite3, xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
DB = os.path.join(HERE, "seckb.db")


def text(el):
    return re.sub(r"\s+", " ", " ".join(el.itertext())).strip() if el is not None else ""


def local(tag):
    return tag.rsplit("}", 1)[-1]


def kids(el, name):
    return [c for c in el if local(c.tag) == name]


def kid(el, name):
    k = kids(el, name)
    return k[0] if k else None


def attack(rows):
    objs = json.load(open(os.path.join(DATA, "enterprise-attack.json"), encoding="utf-8"))["objects"]
    live = [o for o in objs if not o.get("revoked") and not o.get("x_mitre_deprecated")]
    byid = {o["id"]: o for o in live}
    ext = lambda o: next((r.get("external_id") for r in o.get("external_references", []) if r.get("source_name") == "mitre-attack"), None)
    mitig = {}
    for r in live:
        if r.get("type") == "relationship" and r.get("relationship_type") == "mitigates" and r.get("source_ref") in byid:
            m = byid[r["source_ref"]]
            mitig.setdefault(r["target_ref"], []).append(f"{ext(m)} {m.get('name')}: {(r.get('description') or '')[:300]}")
    for o in live:
        t, eid = o.get("type"), ext(o)
        if not eid:
            continue
        if t == "attack-pattern":
            tactics = ", ".join(p["phase_name"] for p in o.get("kill_chain_phases", []))
            body = (f"Tactics: {tactics}. Platforms: {', '.join(o.get('x_mitre_platforms', []))}.\n{o.get('description', '')}\n"
                    f"Detection: {o.get('x_mitre_detection', '')}\nMitigations:\n" + "\n".join(mitig.get(o["id"], [])))
            rows.append((eid, "attack", o["name"], body, f"https://attack.mitre.org/techniques/{eid.replace('.', '/')}/"))
        elif t in ("course-of-action", "intrusion-set", "malware", "tool"):
            kind = {"course-of-action": "mitigation", "intrusion-set": "group"}.get(t, t)
            rows.append((eid, "attack", f"[{kind}] {o['name']}", o.get("description", ""), f"https://attack.mitre.org/"))


def cwe(rows):
    path = glob.glob(os.path.join(DATA, "cwe", "*.xml"))[0]
    for w in ET.parse(path).getroot().iter():
        if local(w.tag) != "Weakness" or w.get("Status") == "Deprecated":
            continue
        cid = f"CWE-{w.get('ID')}"
        mn = kid(w, "Mapping_Notes")
        usage = text(kid(mn, "Usage")) if mn is not None else ""
        rw = kid(w, "Related_Weaknesses")
        rel = ", ".join(f"{x.get('Nature')} CWE-{x.get('CWE_ID')}" for x in kids(rw, "Related_Weakness")) if rw is not None else ""
        parts = [f"Abstraction: {w.get('Abstraction')}. Mapping usage for vulnerabilities: {usage or 'n/a'}"
                 + (f" ({text(kid(mn, 'Rationale'))[:300]})" if mn is not None and usage.lower() in ('discouraged', 'prohibited') else ""),
                 f"Related: {rel}" if rel else "",
                 text(kid(w, "Description")), text(kid(w, "Extended_Description"))]
        mit = kid(w, "Potential_Mitigations")
        if mit is not None:
            parts.append("Mitigations: " + " | ".join(text(m) for m in kids(mit, "Mitigation"))[:3000])
        cons = kid(w, "Common_Consequences")
        if cons is not None:
            parts.append("Consequences: " + text(cons)[:800])
        rows.append((cid, "cwe", w.get("Name"), "\n".join(p for p in parts if p),
                     f"https://cwe.mitre.org/data/definitions/{w.get('ID')}.html"))


def capec(rows):
    for a in ET.parse(os.path.join(DATA, "capec_latest.xml")).getroot().iter():
        if local(a.tag) != "Attack_Pattern" or a.get("Status") == "Deprecated":
            continue
        rw = kid(a, "Related_Weaknesses")
        weak = ", ".join(f"CWE-{x.get('CWE_ID')}" for x in kids(rw, "Related_Weakness")) if rw is not None else ""
        rap = kid(a, "Related_Attack_Patterns")
        rel = ", ".join(f"{x.get('Nature')} CAPEC-{x.get('CAPEC_ID')}" for x in kids(rap, "Related_Attack_Pattern")) if rap is not None else ""
        body = "\n".join(filter(None, [f"Abstraction: {a.get('Abstraction')}." + (f" Related patterns: {rel}" if rel else ""),
                                       text(kid(a, "Description")), f"Related weaknesses: {weak}" if weak else "",
                                       "Mitigations: " + text(kid(a, "Mitigations"))[:2000] if kid(a, "Mitigations") is not None else ""]))
        rows.append((f"CAPEC-{a.get('ID')}", "capec", a.get("Name"), body,
                     f"https://capec.mitre.org/data/definitions/{a.get('ID')}.html"))


def kev(rows):
    for v in json.load(open(os.path.join(DATA, "kev.json"), encoding="utf-8"))["vulnerabilities"]:
        body = (f"{v['vendorProject']} {v['product']}. {v['shortDescription']}\nAdded to KEV: {v['dateAdded']}. "
                f"Due: {v.get('dueDate')}. Ransomware use: {v.get('knownRansomwareCampaignUse')}. "
                f"CWEs: {', '.join(v.get('cwes', []))}\nRequired action: {v['requiredAction']}")
        rows.append((v["cveID"], "kev", v["vulnerabilityName"], body, f"https://nvd.nist.gov/vuln/detail/{v['cveID']}"))


def owasp(rows):
    for f in sorted(glob.glob(os.path.join(DATA, "owasp", "cheatsheets", "*.md"))):
        name = os.path.basename(f)[:-3]
        md = open(f, encoding="utf-8").read()
        for i, sec in enumerate(re.split(r"\n(?=## )", md)):
            title = sec.splitlines()[0].lstrip("# ").strip() if sec.strip() else name
            rows.append((f"OWASP:{name}#{i}", "owasp", f"{name.replace('_', ' ')}: {title}", sec[:8000],
                         f"https://cheatsheetseries.owasp.org/cheatsheets/{name}.html"))


if __name__ == "__main__":
    rows = []
    for fn in (attack, cwe, capec, kev, owasp):
        n = len(rows)
        fn(rows)
        print(f"{fn.__name__}: {len(rows) - n} entries")
    tmp = DB + ".new"
    if os.path.exists(tmp):
        os.remove(tmp)
    db = sqlite3.connect(tmp)
    db.execute("create virtual table docs using fts5(id, source, title, body, url, tokenize='porter unicode61')")
    db.executemany("insert into docs values (?,?,?,?,?)", rows)
    db.commit()
    db.close()
    try:
        os.replace(tmp, DB)
    except PermissionError:
        raise SystemExit("seckb.db is open (Hermes running). Run `hermes gateway stop --yes`, then rerun this script.")
    print("total", len(rows), "->", DB)
