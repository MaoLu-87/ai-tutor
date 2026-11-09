#!/usr/bin/env python
"""节奏账本：把每组的实际用时，变成下一组的题量与挑战度调节。

一组的标准是 15 分钟 / 9 题 = 每题 100 秒。孩子做下来必然有快有慢，
快慢不是好坏，是信号：
  · 又快又对 → 题量不够，加题、多抽薄弱知识点
  · 又慢又错 → 太难或量太大，减题、先抽已掌握的稳住
  · 快但错得多 → 不是简单，是粗心，题量不动，只提醒慢一点

用法：
  python 题库/pace.py                          # 重算并打印建议
  python 题库/pace.py --add 2026-11-08:1:9:1120:7   # 日期:第几组:题数:用时秒:答对
  python 题库/pace.py --sync 题库/submissions.json  # 从云端导出批量导入
  python 题库/pace.py --show                   # 只看账本

数据来源：刷题页做完自动上传到云端 drill_submissions（含 duration_sec）。
在没有云端数据之前，用 --add 手工补录也能跑。
"""
import argparse
import datetime
import json
import os
import statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LEDGER = os.path.join(HERE, "pace.json")

def _tuning():
    try:
        return json.load(open(os.path.join(HERE, "tuning.json"), encoding="utf-8"))
    except Exception:
        return {}


_T = _tuning().get("节奏", {})
TARGET_SEC = _T.get("目标秒", 900)                 # 每组目标：15 分钟
STD_N = _T.get("标准题数", 9)                      # 标准题数
PER_SEC = TARGET_SEC / STD_N                       # 100 秒/题
N_MIN, N_MAX = _T.get("题数下限", 6), _T.get("题数上限", 12)
WINDOW = _T.get("观察最近几组", 3)                  # 用最近几组做判断
STEP = _T.get("单次最大变动", 2)                    # 一次最多动几题

R_SLOW = _T.get("太慢比值", 1.25)
R_LATE = _T.get("偏慢比值", 1.10)
R_OK = _T.get("正好比值", 0.85)
R_FAST = _T.get("偏快比值", 0.65)
ACC_OK = _T.get("会做正确率", 0.80)
ACC_GOOD = _T.get("又快又对正确率", 0.85)
ACC_PERFECT = _T.get("太快全对正确率", 0.90)


def load():
    if not os.path.exists(LEDGER):
        return {"版本": 1, "目标秒": TARGET_SEC, "标准题数": STD_N, "组": [], "建议": default_tip()}
    return json.load(open(LEDGER, encoding="utf-8"))


def default_tip(reason="还没有用时数据，先按 9 题 / 15 分钟跑"):
    return {"题数": STD_N, "偏向": "weak", "每题秒": PER_SEC, "比值": 1.0,
            "预计分钟": round(STD_N * PER_SEC / 60, 1), "判断": "起步", "理由": reason}


def save(d):
    d["更新"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    json.dump(d, open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def make_record(date, group, n, sec, score):
    n = int(n)
    sec = int(sec)
    group = int(group)
    score = int(score)
    if n <= 0:
        raise ValueError("题数必须大于 0")
    return {
        "id": "%s-%d" % (date, group),
        "date": date,
        "组": group,
        "题数": n,
        "用时": sec,
        "答对": int(score),
        "每题秒": round(sec / n, 1),
        "比值": round(sec / n / PER_SEC, 3),
        "正确率": round(score / n, 3),
    }


def add(d, date, group, n, sec, score):
    rec = make_record(date, group, n, sec, score)
    d["组"] = [g for g in d["组"] if g["id"] != rec["id"]]
    d["组"].append(rec)
    d["组"].sort(key=lambda g: (g["date"], g["组"]))
    return rec


def suggest(records):
    """最近 WINDOW 组加权，算出下一组给几题、往哪边偏。

    题数以「15 分钟装得下」为准倒推（900 ÷ 每题秒），再限幅一次最多动 2 题，
    避免孩子题目数量忽上忽下。
    """
    ok = [g for g in records
          if g["题数"] >= 5 and g["用时"] >= g["题数"] * 5 and g["用时"] <= 3600]
    if not ok:
        return default_tip()
    tail = ok[-WINDOW:]
    ws = [1, 2, 3][-len(tail):]
    per = sum(w * g["每题秒"] for w, g in zip(ws, tail)) / sum(ws)
    acc = sum(w * g["正确率"] for w, g in zip(ws, tail)) / sum(ws)
    r = per / PER_SEC
    prev_n = tail[-1]["题数"]

    need = int(round(TARGET_SEC / per))          # 15 分钟能装下几题
    need = max(N_MIN, min(N_MAX, need))
    judge, focus = "正好", "weak"

    if r >= R_SLOW:
        if acc >= ACC_OK:
            judge, focus = "太慢", "steady"
            why = "会做，但每题要 %.0f 秒（目标 100 秒）。先降到 {N} 题，保证 15 分钟内做完；速度练上来再慢慢加回去" % (per,)
        else:
            judge, focus = "又慢又错", "steady"
            why = "又慢又错，说明这一档超纲了：降到 {N} 题，抽题先往她已掌握的知识点偏"
    elif r >= R_LATE:
        judge, focus = "偏慢", "steady"
        why = "比目标慢 %.0f%%，题数收到 {N} 题；抽题多给她会的，先把节奏跑顺" % ((r - 1) * 100,)
    elif r > R_OK:
        why = "节奏正好在 15 分钟附近，维持 {N} 题，继续补薄弱点"
    elif r >= R_FAST:
        if acc >= ACC_GOOD:
            judge = "偏快"
            why = "又快又对，题数加到 {N} 题，并提高薄弱知识点的比例"
        else:
            judge = "偏快但没读透"
            need = prev_n
            why = "做得快但 %d 道错——不是题简单，是没读透；题数不加，做完回去检查一遍" % round((1 - acc) * prev_n)
    else:
        if acc >= ACC_PERFECT:
            judge = "太快"
            why = "远快于目标，题数提到 {N} 题；如果还是全对，就该上更难的知识点了"
        else:
            judge = "快而错"
            need = prev_n
            why = "速度快但错误不少，更像在赶；题数不动，先把速度换成准确率"

    # 渐进：一次最多动 2 题
    n = max(prev_n - STEP, min(prev_n + STEP, need))
    n = max(N_MIN, min(N_MAX, n))
    # 已经顶到边界，就别再说「降到 N 题」这种空话
    if n == N_MIN and judge in ("太慢", "又慢又错"):
        why = "题量已经压到 %d 题，再减就没意义了；这一档先练速度——同样的题，目标 %d 分钟内做完" % (N_MIN, TARGET_SEC // 60)
    elif n == N_MAX and judge in ("太快", "偏快"):
        why = "题量已经到 %d 题上限；再想加挑战，只能换更难的知识点" % N_MAX
    why = why.replace("{N}", str(n))
    est = n * per / 60
    return {"题数": n, "偏向": focus, "每题秒": round(per, 1), "比值": round(r, 3),
            "正确率": round(acc, 3), "预计分钟": round(est, 1), "判断": judge, "理由": why}


def sync_file(d, path):
    """从云端导出导入。兼容 drill_submissions 的行：
    drill_date / drill_title / total / duration_sec / score / answers"""
    rows = json.load(open(path, encoding="utf-8"))
    if isinstance(rows, dict):
        rows = rows.get("记录") or rows.get("data") or rows.get("rows") or []
    n = 0
    for r in rows:
        date = r.get("drill_date") or r.get("date") or r.get("日期")
        total = r.get("total") or r.get("题数")
        sec = r.get("duration_sec") or r.get("用时") or r.get("sec")
        if not date or not total or not sec:
            continue
        title = str(r.get("drill_title") or r.get("title") or "")
        group = 1 if ("第 1" in title or "第1" in title) else 2 if ("第 2" in title or "第2" in title) else 1
        score = r.get("score")
        if score is None:
            score = sum(1 for x in str(r.get("answers", "")).split(",") if "=1@" in x)
        add(d, str(date)[:10], group, total, sec, score)
        n += 1
    return n


def show(d):
    print("目标：每组 %d 分钟 / %d 题（每题 %.0f 秒）" % (TARGET_SEC // 60, STD_N, PER_SEC))
    print("账本：%d 组" % len(d["组"]))
    if d["组"]:
        print("  %-12s %-4s %-4s %-8s %-8s %-7s %s" % ("日期", "组", "题数", "用时", "每题秒", "比值", "正确率"))
        for g in d["组"][-8:]:
            print("  %-12s %-4d %-4d %-8s %-8.0f %-7.2f %d%%" % (
                g["date"], g["组"], g["题数"], fmt_sec(g["用时"]), g["每题秒"], g["比值"],
                round(g["正确率"] * 100)))
    s = d["建议"]
    print("\n下一组建议：%d 题 · 预计 %.1f 分钟 · 偏向%s" % (
        s["题数"], s["预计分钟"], {"weak": "薄弱点", "steady": "已掌握"}.get(s["偏向"], s["偏向"])))
    print("  判断：%s" % s["判断"])
    print("  理由：%s" % s["理由"])


def fmt_sec(s):
    s = int(s)
    return "%d'%02d\"" % (s // 60, s % 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--add", default="", help="日期:第几组:题数:用时秒:答对")
    ap.add_argument("--sync", default="", help="云端导出的 JSON 文件")
    ap.add_argument("--show", action="store_true", help="只看账本")
    ap.add_argument("--reset", action="store_true", help="清空账本（测试后务必执行）")
    a = ap.parse_args()

    d = load()
    if a.reset:
        d = {"版本": 1, "目标秒": TARGET_SEC, "标准题数": STD_N, "组": [], "建议": default_tip()}
        save(d)
        print("账本已清空")
        show(d)
        return

    changed = False
    if a.add:
        parts = a.add.split(":")
        if len(parts) != 5:
            raise SystemExit("格式：--add 2026-11-08:1:9:1120:7")
        add(d, parts[0], parts[1], parts[2], parts[3], parts[4])
        changed = True
    if a.sync:
        n = sync_file(d, a.sync)
        print("从 %s 导入 %d 组" % (a.sync, n))
        changed = True

    if changed or not a.show:
        d["建议"] = suggest(d["组"])
        save(d)
    show(d)


if __name__ == "__main__":
    main()
