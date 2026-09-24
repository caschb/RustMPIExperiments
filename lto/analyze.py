#!/usr/bin/env python3
"""Summarise results.csv: mean/sd per variant, Rust-vs-C MAPE for the no-LTO and
LTO pairs, and the within-language LTO speedup. PIC metric is a rate (higher is
better); BS-SOLCTRA metric is a time (lower is better)."""
import csv, statistics as st, sys
from collections import defaultdict

path = sys.argv[1] if len(sys.argv) > 1 else "results.csv"
data = defaultdict(lambda: defaultdict(dict))   # group -> (lang,lto) -> rep -> metric
for r in csv.DictReader(open(path)):
    g = (r["code"], int(r["nodes"]), r["scaling"], r["style"])
    data[g][(r["lang"], int(r["lto"]))][int(r["rep"])] = float(r["metric"])

def msd(v):
    return (st.mean(v), st.stdev(v) if len(v) > 1 else 0.0, len(v))

def mape(rust, c):
    reps = sorted(set(rust) & set(c))
    if not reps:
        return float("nan")
    return 100 * st.mean(abs(rust[k] - c[k]) / c[k] for k in reps)

hdr = ["code", "nodes", "scaling", "style", "C", "C+LTO", "Rust", "Rust+LTO",
       "MAPE R/C noLTO %", "MAPE R/C LTO %", "C LTO speedup", "Rust LTO speedup"]
print("| " + " | ".join(hdr) + " |")
print("|" + "---|" * len(hdr))
for g in sorted(data):
    d = data[g]
    cells = list(map(str, g))
    for key in (("c", 0), ("c", 1), ("rust", 0), ("rust", 1)):
        v = list(d.get(key, {}).values())
        cells.append("%.2f +/- %.2f (n=%d)" % msd(v) if v else "-")
    cells.append("%.1f" % mape(d.get(("rust", 0), {}), d.get(("c", 0), {})))
    cells.append("%.1f" % mape(d.get(("rust", 1), {}), d.get(("c", 1), {})))
    higher_better = g[0] == "pic"
    for lang in ("c", "rust"):
        a, b = d.get((lang, 0), {}), d.get((lang, 1), {})
        if a and b:
            ma, mb = st.mean(a.values()), st.mean(b.values())
            cells.append("%.3f" % ((mb / ma) if higher_better else (ma / mb)))
        else:
            cells.append("-")
    print("| " + " | ".join(cells) + " |")
