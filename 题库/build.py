#!/usr/bin/env python
"""把三科错题库 + 变式题，汇总成统一索引。

产出：
  题库/index.json   三科统一视图（错题 + 变式），供站点构建与出卷使用

用法：python 题库/build.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SUBJECTS = [
    ("数", "数学错题库/错题库.json", "M"),
    ("语", "语文错题库/错题库.json", "C"),
    ("英", "英语错题库/错题库.json", "E"),
]
VARIANTS = os.path.join(HERE, "variants.json")
INDEX = os.path.join(HERE, "index.json")



def load_errors():
    out = []
    for subj, rel, _ in SUBJECTS:
        p = os.path.join(ROOT, rel)
        if not os.path.exists(p):
            continue
        data = json.load(open(p, encoding="utf-8"))
        for q in data.get("题目", []):
            out.append({
                "id": q["id"],
                "subject": subj,
                "unit": q.get("单元", ""),
                "kps": [q.get("知识点", "")] if q.get("知识点") else [],
                "type": q.get("题型", ""),
                "stem": q.get("题目", ""),
                "answer": q.get("正确答案", ""),
                "explain": q.get("正确思路", ""),
                "wrong": q.get("孩子答案", ""),
                "cause": q.get("错因", []),
                "cause_note": q.get("错因说明", ""),
                "source": q.get("来源", ""),
                "difficulty": q.get("难度", 2),
                "status": q.get("掌握状态", "未掌握"),
                "start": q.get("录入日期", ""),
                "retests": q.get("复测记录", []),
                "options": q.get("选项", []),
                "kind": "error",
            })
    return out


def load_variants():
    if not os.path.exists(VARIANTS):
        return []
    data = json.load(open(VARIANTS, encoding="utf-8"))
    out = []
    for v in data.get("题目", []):
        out.append({
            "id": v["id"],
            "subject": v.get("subject", "数"),
            "unit": v.get("unit", ""),
            "kps": v.get("kps", []),
            "type": v["type"],
            "stem": v["stem"],
            "answer": v["answer"],
            "options": v.get("options", []),
            "hint": v.get("hint", ""),
            "explain": v.get("explain", ""),
            "script": v.get("script", ""),
            "from": v.get("from", ""),
            "difficulty": v.get("difficulty", 2),
            "status": "未练",
            "kind": "variant",
        })
    return out


def main():
    items = load_errors() + load_variants()
    json.dump({"版本": 1, "题目数": len(items), "题目": items},
              open(INDEX, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 统计
    from collections import Counter
    c = Counter(i["subject"] for i in items)
    k = Counter(x for i in items for x in i["kps"])
    print("统一索引: %d 条  ->  %s" % (len(items), INDEX))
    print("  按科目:", dict(c))
    print("  覆盖知识点:", len(k), "个")
    for name, n in k.most_common():
        print("    %-22s %d" % (name, n))


if __name__ == "__main__":
    main()
