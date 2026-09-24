#!/usr/bin/env python3
"""Parse lto/<N>/lto-<N>_<job>.{out,err} into results.csv using the marker lines.

PIC and C++ BS-SOLCTRA report on stdout; Rust BS-SOLCTRA logs on stderr. Both
streams carry the same markers, so each stream is walked independently and a
metric line is attributed to the most recent marker in that stream.
"""
import csv, glob, os, re, sys

MARKER = re.compile(r"^### code=(\w+) lang=(\w+) lto=(\d) scaling=(\w+) style=(\w+) rep=(\d+)")
METRICS = {
    "pic": re.compile(r"Rate \(Mparticles_moved/s\): ([0-9.]+)"),
    "solctra-c": re.compile(r"Total execution time=\[([0-9.]+)\]"),
    "solctra-rust": re.compile(r"Simulation time: ([0-9.]+)"),
}
VALIDATES = "Solution validates"

root = sys.argv[1] if len(sys.argv) > 1 else "."
rows, problems = [], []
for nodes in ("1", "2", "4"):
    files = sorted(glob.glob(os.path.join(root, nodes, f"lto-{nodes}_*.out")))
    for out in files:
        for path in (out, out[:-4] + ".err"):
            if not os.path.exists(path):
                continue
            cur, validated, got = None, False, False
            def flush():
                if cur and cur["code"] == "pic" and got and not validated:
                    problems.append(f"{path}: {cur} ran but did not validate")
            for line in open(path, errors="replace"):
                m = MARKER.match(line)
                if m:
                    flush()
                    code, lang, lto, scaling, style, rep = m.groups()
                    cur = dict(code=code, lang=lang, lto=int(lto), nodes=int(nodes),
                               ranks=20 * int(nodes), scaling=scaling, style=style, rep=int(rep))
                    validated = got = False
                    continue
                if cur is None:
                    continue
                if VALIDATES in line:
                    validated = True
                key = cur["code"] if cur["code"] == "pic" else f"solctra-{cur['lang']}"
                mm = METRICS[key].search(line)
                if mm:
                    got = True
                    rows.append(dict(cur, metric=float(mm.group(1))))
            flush()

rows.sort(key=lambda r: (r["code"], r["nodes"], r["scaling"], r["style"], r["rep"], r["lang"], r["lto"]))
with open(os.path.join(root, "results.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["code", "lang", "lto", "nodes", "ranks", "scaling", "style", "rep", "metric"])
    w.writeheader(); w.writerows(rows)
print(f"{len(rows)} rows written to results.csv")
for p in problems:
    print("PROBLEM:", p)
