#!/usr/bin/env python
"""按《难度标准.md》的五个维度给题目打分，算出 1–10 的难度分。

规则是启发式的，但**可复现**：同一道题跑两次结果一样，两个人按同一套关键词判也基本一致。
打完会跟原有的人工档位（1/2/3）对照，偏离超过 2 分的标出来人工复核。

用法：
  python 大纲题库/rate.py           # 重算并写回
  python 大纲题库/rate.py --check   # 只看分布，不写
"""
import argparse
import json
import os
import re
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "题库.json")

# —— 关键词表，改这里就是改标准 ——
MULTI_STEP = r"再|然后|还剩|找回|够不够|剩下|平均|每[个只件套种]|至少|最多"
INVERSE = r"原来|求宽|求长|求这个数|反过来|已知.{0,6}求"
ERROR_PRONE = r"保留|近似|进位|补 ?0|化简|单位换算|循环|余数"
SITUATION = r"[元米千克克厘米分米]|苹果|铅笔|老师|同学|小明|小红|妈妈|爸爸|课本|书包"
CONCEPT_ONLY = r"下面哪|哪种|哪个是|属于|叫什么|的意义是|英文是|读音|说明方法|修辞"


def rate(q):
    stem = q.get("题干", "") or ""
    typ = q.get("类型", "")
    opts = q.get("选项") or []

    _id = q.get("id", "")
    # 题号形如 Q-C-5A-U5-02-1，科目在第二段
    sub = _id.split("-")[1] if _id.count("-") >= 1 else "M"

    # 语文英语没有「运算步骤」，A 用信息处理量代替
    if sub in ("C", "E"):
        parts_a = 0 if len(stem) <= 40 else (1 if len(stem) <= 80 else 2)
        if re.search(r"能不能|为什么|作用|概括|分析|表达|体会|说明", stem):
            parts_b = 2
        elif re.search(r"选出不同类|下面哪|正确|哪个", stem):
            parts_b = 1
        else:
            parts_b = 0
        parts_c = 0
        parts_d = 1 if (typ == "choice" and len(opts) >= 3) else 0
        if q.get("id", "").rsplit("-", 1)[-1].isdigit() and int(q["id"].rsplit("-", 1)[-1]) >= 3:
            parts_d = min(2, parts_d + 1)
        parts_e = 1 if len(stem) > 50 else 0
        total = parts_a + parts_b + parts_c + parts_d + parts_e
        score = int(round(1 + total * 0.9))
        return ({"A": parts_a, "B": parts_b, "C": parts_c, "D": parts_d, "E": parts_e},
                max(1, min(10, score)))

    # A 步骤数：看有没有「多步信号」，没有就按题型判
    hits = len(re.findall(MULTI_STEP, stem))
    if hits >= 2:
        a = 2
    elif hits == 1:
        a = 1
    else:
        a = 1 if typ == "number" else 0
        # 选择题里也可能要算（「1.25 × 8 的积是」），有运算符就算一步
        if typ == "choice" and re.search(r"[×÷+\-]", stem):
            a = 1

    # B 认知操作：概念辨析 0，计算/判断 1，要建模或组织语言 2
    if re.search(r"列方程|方程|够吗|为什么|作用|概括|分析|说明.{0,4}作用|解决", stem):
        b = 2
    elif typ == "number" or re.search(CONCEPT_ONLY, stem):
        b = 1 if typ == "number" else 0
    else:
        b = 1

    # C 逆向程度
    if len(re.findall(INVERSE, stem)) >= 2:
        c = 2
    elif re.search(INVERSE, stem):
        c = 1
    else:
        c = 0

    # D 干扰强度：选择题本身就有干扰项；再叠易错关键词
    d = 0
    if typ == "choice" and len(opts) >= 3:
        d = 1
    if re.search(ERROR_PRONE, stem):
        d = min(2, d + 1)
    # 同一知识点的第 3 题，出题时就是按「易错」设计的，D 加一档
    tail = q.get("id", "").rsplit("-", 1)[-1]
    if tail.isdigit() and int(tail) >= 3:
        d = min(2, d + 1)

    # E 情境信息：有生活场景 / 多条件
    e = 0
    if re.search(SITUATION, stem):
        e = 1
        # 三个以上数字 + 有单位，才算「多条件要筛选」
        if len(re.findall(r"\d+(?:\.\d+)?", stem)) >= 3:
            e = 2

    total = a + b + c + d + e
    score = int(round(1 + total * 0.9))
    return {"A": a, "B": b, "C": c, "D": d, "E": e}, max(1, min(10, score))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    d = json.load(open(PATH, encoding="utf-8"))
    dist = Counter()
    moved = []

    for q in d["题目"]:
        parts, sc = rate(q)
        old = q.get("难度", 2)
        # 人工档位 1/2/3 大致对应 3 / 5 / 7
        expect = {1: 3, 2: 5, 3: 7}[old]
        if abs(sc - expect) > 2:
            moved.append((q["id"], old, sc))
        q["难度拆解"] = parts
        q["难度分"] = sc
        dist[sc] += 1

    print("题目 %d 道，难度分分布：" % len(d["题目"]))
    for k in sorted(dist):
        print("  %2d 分  %3d 道  %s" % (k, dist[k], "█" * (dist[k] // 2)))
    avg = sum(q["难度分"] for q in d["题目"]) / len(d["题目"])
    print("  平均 %.1f 分" % avg)

    if moved:
        print("\n与人工档位偏离 >2 分、建议复核的 %d 道：" % len(moved))
        for i, old, sc in moved[:15]:
            print("  %-18s 人工档位 %d（约 %d 分）→ 规则算出 %d 分" % (i, old, {1: 3, 2: 5, 3: 7}[old], sc))

    if a.check:
        print("\n（--check，未写回）")
        return

    json.dump(d, open(PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("\n已写回 %s" % PATH)


if __name__ == "__main__":
    main()
