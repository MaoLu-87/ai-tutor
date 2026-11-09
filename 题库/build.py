#!/usr/bin/env python
"""把三科错题库 + 变式题，汇总成统一索引，并生成刷题页用的题库。

产出：
  题库/index.json         三科统一视图（错题 + 变式），供诊断与出卷使用
  刷题/drill-bank.json    只含可点选/可输入的客观题，供 make_drill.py 使用

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
BANK = os.path.join(ROOT, "刷题", "drill-bank.json")

DRILL_TYPES = {"choice", "number", "选择", "填空", "口算", "判断"}


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


def to_bank(items):
    bank = []
    for it in items:
        if it["kind"] != "variant":
            continue
        bank.append({
            "id": it["id"],
            "单元": it["unit"],
            "知识点": "、".join(it["kps"]),
            "类型": it["type"],
            "题干": it["stem"],
            "选项": it.get("options", []),
            "答案": it["answer"],
            "提示": it.get("hint", ""),
            "解释": it.get("explain", ""),
            "原文": it.get("script", ""),
            "派生自": it.get("from", ""),
        })
    return {"版本": 2, "说明": "由 题库/build.py 自动生成，请勿手改。改题目请编辑 题库/variants.json。",
            "题目": bank}


def main():
    items = load_errors() + load_variants()
    json.dump({"版本": 1, "题目数": len(items), "题目": items},
              open(INDEX, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    bank = to_bank(items)
    os.makedirs(os.path.dirname(BANK), exist_ok=True)
    json.dump(bank, open(BANK, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    # 统计
    from collections import Counter
    c = Counter(i["subject"] for i in items)
    k = Counter(x for i in items for x in i["kps"])
    print("统一索引: %d 条  ->  %s" % (len(items), INDEX))
    print("  按科目:", dict(c))
    print("刷题题库: %d 道  ->  %s" % (len(bank["题目"]), BANK))
    print("  覆盖知识点:", len(k), "个")
    for name, n in k.most_common():
        print("    %-22s %d" % (name, n))


if __name__ == "__main__":
    main()
