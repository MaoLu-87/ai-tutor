#!/usr/bin/env python
"""大纲题库自检：结构、答案索引、每个知识点的题数与难度分布。

用法：python 大纲题库/check.py
"""
import json
import os
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "题库.json")


def main():
    d = json.load(open(PATH, encoding="utf-8"))
    kps = {k["id"] for k in d["知识点"]}
    qs = d["题目"]
    errs = []

    ids = Counter(q["id"] for q in qs)
    for i, n in ids.items():
        if n > 1:
            errs.append("题目 id 重复：%s × %d" % (i, n))

    for q in qs:
        qid = q.get("id", "?")
        if not q.get("知识点"):
            errs.append("%s 没有知识点" % qid)
        for k in q.get("知识点", []):
            if k not in kps:
                errs.append("%s 引用了不存在的基础点 %s" % (qid, k))
        if q.get("难度") not in (1, 2, 3):
            errs.append("%s 难度必须是 1/2/3，现在是 %r" % (qid, q.get("难度")))
        if not q.get("解析"):
            errs.append("%s 缺解析" % qid)
        t = q.get("类型")
        if t == "choice":
            opts = q.get("选项") or []
            if len(opts) < 2:
                errs.append("%s 选项不足" % qid)
            a = q.get("答案")
            if not isinstance(a, int) or not (0 <= a < len(opts)):
                errs.append("%s 答案下标越界：%r（共 %d 个选项）" % (qid, a, len(opts)))
        elif t == "number":
            if not isinstance(q.get("答案"), (int, float)):
                errs.append("%s number 题答案不是数字：%r" % (qid, q.get("答案")))
        else:
            errs.append("%s 未知题型 %r" % (qid, t))

    # 每个知识点题数
    by_kp = defaultdict(list)
    for q in qs:
        for k in q["知识点"]:
            by_kp[k].append(q)
    thin = [(k, len(v)) for k, v in by_kp.items() if len(v) < 3]
    zero = [k for k in kps if k not in by_kp]

    print("题目 %d 道，知识点 %d 个（题库定义 %d 个）" % (len(qs), len(by_kp), len(kps)))
    print("难度分布：", dict(sorted(Counter(q["难度"] for q in qs).items())))
    print("题型分布：", dict(Counter(q["类型"] for q in qs)))
    if zero:
        print("\n没出题的知识点 %d 个：%s" % (len(zero), "、".join(sorted(zero))))
    if thin:
        print("题数不足 3 的知识点：%s" % thin)

    if errs:
        print("\n发现 %d 个问题：" % len(errs))
        for e in errs:
            print("  ✗", e)
    else:
        print("\n结构检查通过")


if __name__ == "__main__":
    main()
