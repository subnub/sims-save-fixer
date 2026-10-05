"""Index every game + mod package; record instance IDs of career-related tuning types."""
import os, sys, json, struct
from scan_mods import package_instances

TYPES = {0x73996BEB: 'career', 0x48C75CE3: 'track', 0x2C01BC15: 'level'}
roots = [r"C:\Program Files\EA Games\The Sims 4", r"C:\Users\YourName\Documents\Electronic Arts\The Sims 4\Mods"]
out = {v: {} for v in TYPES.values()}
allinst = {}
n = 0
for root in roots:
    for dp, _, files in os.walk(root):
        for fn in files:
            if not fn.lower().endswith('.package'):
                continue
            full = os.path.join(dp, fn)
            if 'EA Games' in full and not fn.startswith('Simulation'):
                continue
            n += 1
            try:
                for t, inst in package_instances(full):
                    if t in TYPES:
                        out[TYPES[t]].setdefault(str(inst), []).append(full)
            except Exception as e:
                print('ERR', full, e)
print('scanned', n, {k: len(v) for k, v in out.items()})
json.dump(out, open('tuning_index.json', 'w'))
