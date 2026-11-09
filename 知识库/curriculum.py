#!/usr/bin/env python
"""小学知识点库：按学期起点和单元起始周，实时算出每个知识点「已学 / 进行中 / 未学」。

不把状态写进文件——每天的进度都会变，存下来就会过期。

用法：
  python 知识库/curriculum.py                 # 按今天算
  python 知识库/curriculum.py --date 2026-12-20
  python 知识库/curriculum.py --book 五上     # 只看某一册
"""
import argparse
import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "curriculum.json")

SEM_WEEKS = 20          # 一学期按 20 个教学周算


def load():
    return json.load(open(PATH, encoding="utf-8"))


def plan(d, book, today, sub=None):
    """返回某科某册每个单元的时间区间与状态。
    必须带 sub——「五上第 5 单元」三科各有一个，混在一起会串。"""
    base = datetime.date.fromisoformat(d["学期起点"][book])
    kps = [x for x in d["知识点"]
           if x["book"] == book and (sub is None or x["sub"] == sub)]
    if not kps:
        return []
    units = []
    seen = set()
    for kp in kps:
        if kp["unit"] in seen:
            continue
        seen.add(kp["unit"])
        units.append({"unit": kp["unit"], "name": kp["unitName"], "week": kp["week"]})
    units.sort(key=lambda u: u["week"])

    out = []
    for i, u in enumerate(units):
        start = base + datetime.timedelta(days=(u["week"] - 1) * 7)
        nxt = units[i + 1]["week"] if i + 1 < len(units) else SEM_WEEKS + 1
        end = base + datetime.timedelta(days=(nxt - 1) * 7)
        if today < start:
            st = "未学"
        elif today < end:
            st = "进行中"
        else:
            st = "已学"
        out.append(dict(u, start=start, end=end, status=st))
    return out


def annotate(d, today):
    """给每个知识点打上状态，返回新列表。"""
    cache = {}
    out = []
    for kp in d["知识点"]:
        key = (kp["sub"], kp["book"])
        if key not in cache:
            cache[key] = {u["unit"]: u for u in plan(d, kp["book"], today, kp["sub"])}
        u = cache[key].get(kp["unit"], {})
        out.append(dict(kp, status=u.get("status", "未学"),
                        unitStart=u.get("start", "").isoformat() if u else None,
                        unitEnd=u.get("end", "").isoformat() if u else None))
    return out


def summary(rows):
    from collections import Counter, defaultdict
    by_status = Counter(x["status"] for x in rows)
    by_book = defaultdict(Counter)
    for x in rows:
        by_book[x["book"]][x["status"]] += 1
    return by_status, by_book


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="")
    ap.add_argument("--book", default="")
    a = ap.parse_args()

    d = load()
    today = datetime.date.fromisoformat(a.date) if a.date else datetime.date.today()
    rows = annotate(d, today)
    if a.book:
        rows = [x for x in rows if x["book"] == a.book]

    by_status, by_book = summary(rows)
    print("%s　共 %d 个知识点" % (today.isoformat(), len(rows)))
    print("  " + "　".join("%s %d" % (k, v) for k, v in by_status.items()))

    for book in sorted(by_book, key=lambda b: d["学期起点"][b]):
        c = by_book[book]
        print("  %-4s 已学 %-3d 进行中 %-2d 未学 %-3d" % (
            book, c["已学"], c["进行中"], c["未学"]))

    cur = [x for x in rows if x["status"] == "进行中"]
    if cur:
        print("\n【本周在学】")
        keys = sorted({(x["sub"], x["book"], x["unit"], x["unitName"]) for x in cur})
        for sub, book, unit, uname in keys:
            names = [x["name"] for x in cur
                     if x["sub"] == sub and x["book"] == book and x["unit"] == unit]
            print("  %s %s 第 %d 单元 %s：%s" % (sub, book, unit, uname, "、".join(names)))


if __name__ == "__main__":
    main()
