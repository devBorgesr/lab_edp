import json, re
from pathlib import Path
base = Path(r"C:\edp_data_fase0\sessions\default_cognitive")
def norm(t): return re.sub(r"\s+", " ", (t or "").strip().casefold())
padroes = ("nada. esta é a primeira", "q: sim")
def load(p):
    with open(p, encoding="utf-8") as f:
        raw = json.load(f)
    return raw.get("entries") if isinstance(raw, dict) else raw
for nome in ("episodic.json", "semantic.json"):
    p = base / nome
    if not p.exists():
        print(f"{nome}: NAO EXISTE neste caminho"); continue
    entries = load(p)
    print(f"\n{nome}: {len(entries)} entries")
    for e in entries:
        t = norm(e.get("text", ""))
        if any(pd in t[:120] for pd in padroes):
            print(f"  id={str(e.get('id','?'))[:8]} len={len(t)} :: {t[:78]}")