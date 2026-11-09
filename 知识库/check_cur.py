#!/usr/bin/env python
"""知识点库自检：id 唯一、单元周次递增、字段完整。"""
import json, os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(HERE, "curriculum.json"), encoding="utf-8"))
k = d["知识点"]
errs = []

dup = [i for i, n in Counter(x["id"] for x in k).items() if n > 1]
if dup:
    errs.append("id 重复：%s" % dup)

for x in k:
    for f in ("id", "sub", "book", "unit", "unitName", "name", "week"):
        if x.get(f) in (None, ""):
            errs.append("%s 缺字段 %s" % (x.get("id"), f))
    if x["book"] not in d["学期起点"]:
        errs.append("%s 的册次 %s 没有学期起点" % (x["id"], x["book"]))

# 同科同册，单元号与周次都要递增
by = defaultdict(list)
for x in k:
    by[(x["sub"], x["book"])].append(x)
for key, rows in by.items():
    seen = {}
    for x in rows:
        seen.setdefault(x["unit"], x["week"])
    units = sorted(seen)
    weeks = [seen[u] for u in units]
    if weeks != sorted(weeks):
        errs.append("%s %s 单元周次不是递增：%s" % (key[0], key[1], list(zip(units, weeks))))
    if units != list(range(1, len(units) + 1)):
        errs.append("%s %s 单元号不连续：%s" % (key[0], key[1], units))

print("知识点 %d 个，%d 个科目册次组合" % (len(k), len(by)))
print("按科：", dict(Counter(x["sub"] for x in k)))
print("按册：", dict(sorted(Counter(x["book"] for x in k).items())))
if errs:
    print("\n%d 个问题：" % len(errs))
    for e in errs:
        print("  ✗", e)
else:
    print("\n结构检查通过")
