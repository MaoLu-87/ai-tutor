#!/usr/bin/env python
"""把我们的数学题映射到 cn-math-taxonomy 的节点上。

输出 知识库/taxonomy/map-math.json：
  {"题库知识点名": {"topic": "cnm_p132", "how": "精确/包含/人工", "题数": 3}}
没映射上的记 null，并列出原因。

用法：python 知识库/taxonomy/build_map.py [--check]
"""
import argparse
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TAX = os.path.join(HERE, "topics-primary.json")
OUT = os.path.join(HERE, "map-math.json")

# 手工映射：字符串匹配对不上、但确认是同一回事的
MANUAL = {
    "整数乘法运算定律推广到小数": ("cnm_p133", "并进「小数乘小数」，图谱没有单独一条"),
    "小数乘法的应用": ("cnm_p134", ""),
    "解决问题（估算·分段计费）": ("cnm_p134", "图谱把它归到小数乘法的应用"),
    "小数乘法·解决问题": ("cnm_p134", ""),
    "用数对表示位置": ("cnm_p136", "图谱标在 6 上（人教版是五上第 2 单元），位置有出入"),
    "商的近似数": ("cnm_p139", "并进「小数除法的应用」"),
    "小数除法·商的近似数": ("cnm_p139", ""),
    "循环小数": ("cnm_p139", "图谱没有单独节点"),
    "解决问题（进一法·去尾法）": ("cnm_p139", ""),
    "小数除法·解决问题": ("cnm_p139", ""),
    "小数乘除混合运算": ("cnm_p139", ""),
    "解方程": ("cnm_p145", "图谱叫「解简易方程」"),
    "实际问题与方程": ("cnm_p146", "图谱叫「列方程解决实际问题」"),
    "运算定律": ("cnm_p117", "图谱叫「用运算律简便计算」（四下）"),
    "同级运算顺序": ("cnm_p112", "图谱叫「整数四则混合运算」（四下）"),
    "小数点定位": ("cnm_p133", "并进「小数乘小数」"),
    "小数减法·解决问题": ("cnm_p126", "图谱「小数加减解决实际问题」（四下）"),
    "两位数位值": ("cnm_p055", "图谱「万以内数的组成」（二下）"),
    "审题": (None, "通用能力，图谱里没有对应节点"),
}

# 图谱已知问题，标出来不阻塞
KNOWN_ISSUES = {
    "cnm_p136": "「用有序数对确定位置」图谱标在 6 上，人教版实际是五上第 2 单元",
}


def norm(s):
    return re.sub(r"[·（）()、\s]", "", s or "")


def load_sources():
    """返回 {知识点名: [题号...]}，只收数学。"""
    src = {}

    ol = json.load(open(os.path.join(ROOT, "大纲题库", "题库.json"), encoding="utf-8"))
    kmap = {k["id"]: k["名称"] for k in ol["知识点"]}
    for q in ol["题目"]:
        if q["知识点"][0][0] != "M":
            continue
        for k in q["知识点"]:
            src.setdefault(kmap.get(k, k), []).append(q["id"])

    for v in json.load(open(os.path.join(ROOT, "题库", "variants.json"), encoding="utf-8"))["题目"]:
        if v["subject"] != "数":
            continue
        for k in v.get("kps", []):
            src.setdefault(k, []).append(v["id"])

    for q in json.load(open(os.path.join(ROOT, "数学错题库", "错题库.json"), encoding="utf-8"))["题目"]:
        if q.get("知识点"):
            src.setdefault(q["知识点"], []).append(q["id"])

    return src


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    topics = json.load(open(TAX, encoding="utf-8"))
    math = [x for x in topics if x["sub"] == "数"]
    by_norm = {norm(x["name"]): x for x in math}

    src = load_sources()
    out = {}
    stat = {"精确": 0, "包含": 0, "人工": 0, "无": 0}

    for name, qids in sorted(src.items()):
        n = norm(name)
        hit = by_norm.get(n)
        how = "精确"
        note = ""
        if not hit:
            cand = [x for k, x in by_norm.items()
                    if len(k) >= 3 and len(n) >= 3 and (n in k or k in n)]
            if cand:
                hit, how = cand[0], "包含"
        if not hit and name in MANUAL:
            tid, note = MANUAL[name]
            hit = next((x for x in math if x["id"] == tid), None)
            how = "人工" if hit else "无"
        if not hit:
            how = "无"
        stat[how] += 1

        out[name] = {
            "topic": hit["id"] if hit else None,
            "topicName": hit["name"] if hit else "",
            "book": ("%d%s" % (hit["grade"], hit["sem"])) if hit else "",
            "how": how,
            "note": note or (KNOWN_ISSUES.get(hit["id"], "") if hit else ""),
            "题数": len(qids),
            "题": qids,
        }

    total_q = sum(v["题数"] for v in out.values())
    mapped_q = sum(v["题数"] for v in out.values() if v["topic"])
    covered = len({v["topic"] for v in out.values() if v["topic"]})

    print("数学知识点 %d 个 → 命中 %d（精确 %d / 包含 %d / 人工 %d），无对应 %d"
          % (len(out), len(out) - stat["无"], stat["精确"], stat["包含"], stat["人工"], stat["无"]))
    print("题目 %d 道，能挂到节点上的 %d 道（%.0f%%）" % (total_q, mapped_q, mapped_q / total_q * 100))
    print("覆盖图谱节点 %d / %d（%.0f%%）" % (covered, len(math), covered / len(math) * 100))

    print("\n没挂上的：")
    for k, v in out.items():
        if not v["topic"]:
            print("  %-20s %d 道 · %s" % (k, v["题数"], v["note"]))

    seen_note = set()
    notes = []
    for v in out.values():
        if v["note"] and v["topic"] and v["note"] not in seen_note:
            seen_note.add(v["note"])
            notes.append((v["topicName"], v["note"]))
    if notes:
        print("\n映射但需留意：")
        for n, note in notes:
            print("  %-22s %s" % (n, note))

    if a.check:
        return
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("\n已写入 %s" % OUT)


if __name__ == "__main__":
    main()
