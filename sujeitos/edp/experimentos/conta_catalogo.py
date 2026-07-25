import json, re, collections
p = r"C:\edp_data_fase0\sessions\default_cognitive\episodic.json"
with open(p, encoding="utf-8") as f:
    raw = json.load(f)
entries = raw.get("entries") if isinstance(raw, dict) else raw
def norm(t): return re.sub(r"\s+", " ", (t or "").strip().casefold())
texts = [norm(e.get("text", "")) for e in entries]
c = collections.Counter(texts)
padroes = ("q: oi a:", "nada. esta", "q: sim a:")
alvo = {t: n for t, n in c.items() if n > 1 and any(p_ in t[:90] for p_ in padroes)}
soma = sum(alvo.values())
print(f"denominador real (cognitive): {len(texts)}")
for t, n in sorted(alvo.items(), key=lambda x: -x[1]):
    print(f"  {n}x  {t[:72]}")
print(f"catalogo verificado: {soma}/{len(texts)} = {soma/len(texts)*100:.1f}%")
