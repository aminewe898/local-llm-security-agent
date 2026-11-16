import json, os

p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tune_results.jsonl")
print(f"{'trial':<18}{'ctx':>6}{'gen':>7}{'prompt':>8}{'TTFT13k':>9}{'longgen':>9}{'vram':>7}{'freeRAM':>9}")
for line in open(p, encoding="utf-8"):
    r = json.loads(line)
    g = lambda k: r.get(k, "-")
    print(f"{r['trial']:<18}{r['ctx']:>6}{g('gen_tps'):>7}{g('prompt_tps'):>8}{g('long_ttft_s'):>9}{g('long_gen_tps'):>9}{g('vram_after_mib'):>7}{g('free_ram_gb'):>9}  {str(r.get('error', ''))[:70]}")
