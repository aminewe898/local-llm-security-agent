"""Live view of the CTF agent: streams each lab_shell command Gemma runs and the
response it gets, by following its session database. Ctrl-C to stop (harness keeps running)."""
import json, os, sqlite3, time

DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hermes-home", "state.db")
seen = set()
C = {"cmd": "\033[96m", "sec": "\033[93m", "out": "\033[90m", "hdr": "\033[1;92m", "r": "\033[0m"}
print("Watching Gemma work the lab (newest commands appear below)...  Ctrl-C to stop.\n")
while True:
    try:
        db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        rows = db.execute("select id, role, content, tool_calls, tool_name from messages order by rowid").fetchall()
        db.close()
    except Exception:
        time.sleep(2); continue
    for m in rows:
        if m["id"] in seen:
            continue
        seen.add(m["id"])
        if m["tool_calls"]:
            for c in json.loads(m["tool_calls"]):
                f = c.get("function", c)
                name = f.get("name", "")
                try:
                    args = json.loads(f.get("arguments") or "{}")
                except Exception:
                    args = {}
                if "lab_shell" in name:
                    print(f"{C['cmd']}$ {args.get('command','')[:400]}{C['r']}")
                elif "http_req" in name:
                    print(f"{C['cmd']}> {args.get('method','')} {args.get('path','')}  {args.get('json_body','')[:160]}{C['r']}")
                elif "http_map" in name or "lab_target" in name:
                    print(f"{C['cmd']}> {name.split('__')[-1]}(){C['r']}")
                elif "sec_" in name or "cve" in name:
                    print(f"{C['sec']}  [seckb] {name.split('__')[-1]}({json.dumps(args)[:120]}){C['r']}")
        elif m["role"] == "tool" and m["content"]:
            body = m["content"].replace("\n", " ")[:300]
            print(f"{C['out']}  -> {body}{C['r']}")
        elif m["role"] == "assistant" and m["content"] and "RESULT:" in m["content"]:
            print(f"\n{C['hdr']}{m['content'][-600:]}{C['r']}\n{'-'*60}")
    time.sleep(2)
