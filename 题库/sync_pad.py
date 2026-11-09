#!/usr/bin/env python
"""把刷题页上传到云端的记录，同步回本地的 attempts.json。

云端表 drill_submissions 每行是一整场（answers 字段形如
  `D20261108|V-004-01=0@74,V-006-01=1@20|221`，末尾是总用时秒）。

规则：
  1. 同一场（同一天 + 同一标题）做了多遍时，**只取第一遍**——后面的是看过答案重做，
     不计入掌握度，否则会把她的真实水平算高。
  2. 按 (日期, 场次, 题号) 去重，重复执行不会写两遍。
  3. 记录号接着 A0001 往后编，只增不改。

用法：
  python 题库/sync_pad.py --file 导出.json          # 正式写入
  python 题库/sync_pad.py --file 导出.json --dry    # 只看会写什么
"""
import argparse
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ATT = os.path.join(HERE, "attempts.json")
DONE = os.path.join(HERE, "done.json")   # 每天每组的完成情况，供排期与首页使用


def parse_answers(s):
    """D20261108|V-004-01=0@74#C,...|221 → [(题号, 是否对, 秒, 她的作答)]

    # 后面是她选了什么（早期版本没有这一段，pick 为空字符串）。
    """
    parts = str(s).split("|")
    body = parts[1] if len(parts) >= 2 else ""
    out = []
    for seg in body.split(","):
        seg = seg.strip()
        if not seg:
            continue
        left, _, right = seg.partition("@")
        sec_s, _, pick = right.partition("#")
        iid, _, ok = left.partition("=")
        try:
            out.append((iid.strip(), ok.strip() == "1", int(sec_s or 0), pick.strip()))
        except ValueError:
            continue
    return out


def dump_sec(s):
    parts = str(s).split("|")
    try:
        return int(parts[2])
    except (IndexError, ValueError):
        return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True, help="从云端导出的 JSON（数组）")
    ap.add_argument("--dry", action="store_true", help="只打印，不写文件")
    a = ap.parse_args()

    rows = json.load(open(a.file, encoding="utf-8"))
    if isinstance(rows, dict):
        rows = rows.get("rows") or rows.get("data") or []

    # 同一场取最早一条
    first = {}
    for r in rows:
        date = str(r.get("drill_date") or r.get("date") or "")[:10]
        title = str(r.get("drill_title") or r.get("title") or "刷题")
        if not date:
            continue
        key = (date, title)
        ts = str(r.get("created_at") or "")
        if key not in first or ts < str(first[key].get("created_at") or ""):
            first[key] = r

    book = json.load(open(ATT, encoding="utf-8"))
    recs = book["记录"]
    seen = {(r.get("at"), r.get("context"), r.get("item_id")) for r in recs}
    seq = max([int(r["id"][1:]) for r in recs if str(r.get("id", "")).startswith("A")] or [0])

    added, skipped = [], 0
    for (date, title), r in sorted(first.items()):
        items = parse_answers(r.get("answers", ""))
        sec_all = dump_sec(r.get("answers", "")) or int(r.get("duration_sec") or 0)
        if not items:
            continue
        n_ok = sum(1 for _, ok, _, _ in items if ok)
        print("  %s %s：%d 题，对 %d，用时 %d'%02d\"（%d 条记录）" % (
            date, title, len(items), n_ok, sec_all // 60, sec_all % 60, len(items)))
        for iid, ok, sec, pick in items:
            if (date, title, iid) in seen:
                skipped += 1
                continue
            seq += 1
            rec = {
                "id": "A%04d" % seq,
                "item_id": iid,
                "mode": "pad",
                "ok": ok,
                "at": date,
                "context": title,
                "note": "" if ok else (
                    "刷题答错（选了 %s，%d 秒）" % (pick, sec) if pick
                    else "刷题答错（%d 秒，早期版本未记录选项）" % sec),
            }
            recs.append(rec)
            seen.add((date, title, iid))
            added.append(rec)

    # 重做的场次单独提示，避免以后误以为是漏同步
    dup = {}
    for r in rows:
        key = (str(r.get("drill_date") or "")[:10], str(r.get("drill_title") or ""))
        dup[key] = dup.get(key, 0) + 1
    for (date, title), n in dup.items():
        if n > 1:
            print("  · %s %s 做了 %d 遍，只取第一遍" % (date, title, n))

    # 顺手写 done.json：构建页面时用它标「已完成」，否则刷新后看不出做过
    done = {}
    if os.path.exists(DONE):
        try:
            done = json.load(open(DONE, encoding="utf-8"))
        except Exception:
            done = {}
    for (date, title), r in first.items():
        items = parse_answers(r.get("answers", ""))
        if not items:
            continue
        grp = title.split("·")[-1].strip() or title
        done.setdefault(date, {})[grp] = {
            "ok": sum(1 for _, ok, _, _ in items if ok),
            "n": len(items),
            "sec": dump_sec(r.get("answers", "")) or int(r.get("duration_sec") or 0),
        }
    if not a.dry:
        json.dump(done, open(DONE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("\n新增 %d 条，已存在跳过 %d 条，总记录 %d 条" % (len(added), skipped, len(recs)))
    if a.dry:
        print("（--dry，未写入）")
        return
    json.dump(book, open(ATT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("已写入 %s" % ATT)


if __name__ == "__main__":
    main()
