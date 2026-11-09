#!/usr/bin/env python
"""按遗忘曲线算出「今天该复测哪几题」。

错题排期：发现日（首次记录）+ D+1 / D+7 / D+21 三次复测。
每完成一次复测，里程碑推进一格；三次都过 → 标 mastered。

用法：
  python 题库/lifecycle.py          # 今天该练什么
  python 题库/lifecycle.py --all    # 全部在库题的排期
"""
import argparse
import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ATTEMPTS = os.path.join(HERE, "attempts.json")
INDEX = os.path.join(HERE, "index.json")

MILESTONES = [1, 7, 21]  # 天


def load():
    att = json.load(open(ATTEMPTS, encoding="utf-8"))["记录"]
    idx = json.load(open(INDEX, encoding="utf-8"))["题目"]
    return att, {i["id"]: i for i in idx}


def today():
    return datetime.date.today()


def analyze(att, items):
    # 变式的作答归到它派生自的原题上，否则变式练了等于没练
    by_item = {}
    for a in att:
        it = items.get(a["item_id"], {})
        key = it.get("from") if it.get("kind") == "variant" and it.get("from") else a["item_id"]
        by_item.setdefault(key, []).append(a)

    rows = []
    for iid, recs in by_item.items():
        # 只排错题库里的题。大纲题（Q-*）没有「复测」概念，进来会把在库数撑大
        if iid not in items:
            continue
        recs.sort(key=lambda r: r["at"])
        start = datetime.date.fromisoformat(recs[0]["at"])
        reviews = len(recs) - 1              # 首次是「发现」，之后才算复测
        ok_streak = 0
        for r in reversed(recs[1:]):
            if r["ok"]:
                ok_streak += 1
            else:
                break

        if reviews >= 3 and ok_streak >= 3:
            status, due = "已巩固", None
        elif reviews >= len(MILESTONES):
            status, due = "待判定", start + datetime.timedelta(days=MILESTONES[-1])
        else:
            status = "复测中" if reviews else "待复测"
            due = start + datetime.timedelta(days=MILESTONES[reviews])

        rows.append({
            "id": iid,
            "kp": "、".join(items.get(iid, {}).get("kps", [])) or "—",
            "start": start,
            "reviews": reviews,
            "ok_streak": ok_streak,
            "due": due,
            "status": status,
            "last": recs[-1]["at"],
            "note": recs[-1].get("note", ""),
        })
    rows.sort(key=lambda r: (r["due"] or datetime.date.max))
    return rows


def fmt(d):
    return d.strftime("%m-%d") if d else "—"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()

    att, items = load()
    rows = analyze(att, items)
    t = today()

    due = [r for r in rows if r["due"] and r["due"] <= t]
    soon = [r for r in rows if r["due"] and t < r["due"] <= t + datetime.timedelta(days=7)]
    done = [r for r in rows if r["status"] == "已巩固"]

    print("今天 %s　在库错题 %d 道｜已巩固 %d 道\n" % (t.isoformat(), len(rows), len(done)))

    print("【该练了】共 %d 道" % len(due))
    if due:
        print("  %-10s %-6s %-4s %-24s %s" % ("编号", "到期", "逾期", "知识点", "上次情况"))
        for r in due:
            late = (t - r["due"]).days
            print("  %-10s %-6s %-4s %-24s %s" % (
                r["id"], fmt(r["due"]), ("%d天" % late) if late > 0 else "今天",
                r["kp"][:22], r["note"][:30]))
    else:
        print("  （无）")

    if soon:
        print("\n【7 天内到期】共 %d 道" % len(soon))
        for r in soon:
            print("  %-10s %-6s %-24s" % (r["id"], fmt(r["due"]), r["kp"][:22]))

    if a.all:
        print("\n【全部】")
        print("  %-10s %-6s %-4s %-6s %-24s" % ("编号", "发现", "复测", "状态", "知识点"))
        for r in rows:
            print("  %-10s %-6s %-4s %-6s %-24s" % (
                r["id"], fmt(r["start"]), r["reviews"], r["status"], r["kp"][:20]))

    json.dump({"date": t.isoformat(),
               "due": [r["id"] for r in due],
               "soon": [r["id"] for r in soon],
               "mastered": [r["id"] for r in done]},
              open(os.path.join(HERE, "due.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    retired = [r for r in rows if r["status"] == "已巩固"]
    if retired:
        print("\n【可移出刷题池】%d 道：%s" % (len(retired), "、".join(r["id"] for r in retired)))


if __name__ == "__main__":
    main()
