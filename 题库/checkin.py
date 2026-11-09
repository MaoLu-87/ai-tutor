#!/usr/bin/env python
"""打卡与星星结算。

打卡：当天至少完成一组练习（同一场次 ≥5 题，一组是 9 题）。
星星：连续第 N 天发 N 颗，单日上限 10 颗；中断则从第 1 天重新数。
提取：把「可提取」清零，留下一条提取记录（日期 + 颗数），兑奖在另一个 App 里人工操作。

读：题库/attempts.json、题库/checkin.json（保留提取记录）
出：题库/checkin.json

用法：
  python 题库/checkin.py              重算
  python 题库/checkin.py --withdraw   全部提取（命令行兜底，正常用网页按钮）
"""
import argparse
import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ATT = os.path.join(HERE, "attempts.json")
OUT = os.path.join(HERE, "checkin.json")

def _tuning():
    try:
        return json.load(open(os.path.join(HERE, "tuning.json"), encoding="utf-8"))
    except Exception:
        return {}


_T = _tuning().get("打卡", {})
MIN_PER_SESSION = _T.get("每场最少题数", 5)      # 一场至少做这么多题才算完成一组
MAX_STAR_PER_DAY = _T.get("单日星数上限", 10)    # 单日上限
_BONUS = _T.get("全对奖励", {})


def load_days():
    att = json.load(open(ATT, encoding="utf-8"))["记录"]
    days, sessions = {}, {}
    for r in att:
        d = r.get("at")
        if not d:
            continue
        days.setdefault(d, {"n": 0, "pad_n": 0, "pad_ok": 0, "paper_n": 0})
        days[d]["n"] += 1
        if r.get("mode") == "pad":
            days[d]["pad_n"] += 1
            days[d]["pad_ok"] += 1 if r.get("ok") else 0
            key = (d, r.get("context", ""))
            sessions[key] = sessions.get(key, 0) + 1
        else:
            days[d]["paper_n"] += 1
    checked = {d for (d, _), n in sessions.items() if n >= MIN_PER_SESSION}
    return days, checked


def group_bonus(att):
    """按「场次」判断全对：一场（同一天同一标题）做够 MIN_PER_SESSION 题且全对。
    1 组全对 +2 颗，2 组全对 +5 颗（当日封顶 5，不叠加）。"""
    groups = {}
    for r in att:
        if r.get("mode") != "pad":
            continue
        key = (r.get("at"), r.get("context", ""))
        groups.setdefault(key, []).append(bool(r.get("ok")))
    perfect = {}
    for (d, _), oks in groups.items():
        if len(oks) >= MIN_PER_SESSION and all(oks):
            perfect[d] = perfect.get(d, 0) + 1
    return {d: (_BONUS.get("两场", 5) if n >= 2 else _BONUS.get("一场", 2))
            for d, n in perfect.items()}, perfect


def band_of(pad_n, pad_ok, paper_n):
    if pad_n == 0:
        return ("record", None) if paper_n else ("none", None)
    rate = pad_ok / pad_n
    if pad_n >= 3 and pad_ok == pad_n:
        return ("perfect", rate)
    if rate >= 0.95:
        return ("b95", rate)
    if rate >= 0.90:
        return ("b90", rate)
    if rate >= 0.80:
        return ("b80", rate)
    if rate >= 0.70:
        return ("b70", rate)
    return ("b0", rate)


def streak_to(checked, day):
    n, cur = 0, day
    while cur.isoformat() in checked:
        n += 1
        cur -= datetime.timedelta(days=1)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--withdraw", action="store_true")
    ap.add_argument("--note", default="")
    ap.add_argument("--add", default="", help="补录一条提取：YYYY-MM-DD:星星数[:备注]")
    a = ap.parse_args()

    att_raw = json.load(open(ATT, encoding="utf-8"))["记录"]
    bonus, perfect = group_bonus(att_raw)
    days, checked = load_days()
    today = datetime.date.today()

    old = {}
    if os.path.exists(OUT):
        old = json.load(open(OUT, encoding="utf-8"))
    withdraws = old.get("提取记录", [])

    earned, streak_at, streak, prev = {}, {}, 0, None
    for d in sorted(checked):
        cur = datetime.date.fromisoformat(d)
        streak = streak + 1 if (prev and (cur - prev).days == 1) else 1
        streak_at[d] = streak
        base = min(streak, MAX_STAR_PER_DAY)
        # 按当天答对率打折：≥80% 全拿，60–80% 减半（保底 1 颗），<60% 不给还扣 1 颗
        x = days.get(d, {})
        rate = (x["pad_ok"] / x["pad_n"]) if x.get("pad_n") else 0
        if rate >= 0.8:
            earned[d] = base
        elif rate >= 0.6:
            earned[d] = max(1, base // 2)
        else:
            earned[d] = -1   # 当日不给，还倒扣 1 颗（允许负）
        prev = cur
    total_earned = sum(earned.values()) + sum(bonus.values())

    if a.add:
        parts = a.add.split(":")
        date_s, stars_s = parts[0], parts[1]
        memo = parts[2] if len(parts) > 2 else ""
        key = "%s|%s|%s" % (date_s, stars_s, memo)
        if not any("%s|%s|%s" % (w["date"], w["星星"], w.get("备注", "")) == key for w in withdraws):
            withdraws.append({"date": date_s, "星星": int(stars_s), "备注": memo})
            print("补录提取：%s %s 颗 %s" % (date_s, stars_s, memo))

    if a.withdraw:
        avail = total_earned - sum(w["星星"] for w in withdraws)
        if avail <= 0:
            print("没有可提取的星星")
            return
        withdraws.append({"date": today.isoformat(), "星星": avail, "备注": a.note})
        print("已提取 %d 颗星（%s）" % (avail, today.isoformat()))

    withdrawn = sum(w["星星"] for w in withdraws)
    available = total_earned - withdrawn

    cur_streak = streak_to(checked, today)
    counting_to = today
    if cur_streak == 0:
        cur_streak = streak_to(checked, today - datetime.timedelta(days=1))
        counting_to = today - datetime.timedelta(days=1)
    longest = max([streak_to(checked, datetime.date.fromisoformat(d)) for d in checked] or [0])
    longest = max(longest, old.get("最长连续", 0), cur_streak)
    if today.isoformat() in checked:
        today_star = earned.get(today.isoformat(), 0)
    else:
        # 今天还没打卡：做完就是第 cur_streak+1 天
        today_star = min(cur_streak + 1, MAX_STAR_PER_DAY)

    first = today.replace(day=1)
    nxt = (first + datetime.timedelta(days=32)).replace(day=1)
    calendar_days = []
    d = first
    while d < nxt:
        key = d.isoformat()
        rec = days.get(key) or {"n": 0, "pad_n": 0, "pad_ok": 0, "paper_n": 0}
        band, rate = band_of(rec["pad_n"], rec["pad_ok"], rec["paper_n"])
        calendar_days.append({
            "date": key, "dow": d.weekday(),
            "checked": key in checked,
            "n": rec["n"], "pad_n": rec["pad_n"], "pad_ok": rec["pad_ok"],
            "rate": round(rate, 4) if rate is not None else None,
            "band": band, "star": earned.get(key, 0),
            "is_today": d == today, "future": d > today,
        })
        d += datetime.timedelta(days=1)

    flow = []
    for d, st in earned.items():
        flow.append({"date": d, "type": "in", "stars": st,
                     "note": "连续第 %d 天%s" % (streak_at[d], "（封顶）" if streak_at[d] > MAX_STAR_PER_DAY else "")})
    for d, b in bonus.items():
        flow.append({"date": d, "type": "in", "stars": b,
                     "note": "全对奖励（%d 组全对）" % perfect.get(d, 1)})
    for w in withdraws:
        flow.append({"date": w["date"], "type": "out", "stars": w["星星"],
                     "note": w.get("备注") or "提取"})
    flow.sort(key=lambda x: (x["date"], 0 if x["type"] == "out" else 1), reverse=True)

    out = {
        "生成时间": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "今日已打卡": today.isoformat() in checked,
        "连续天数": cur_streak,
        "统计截止": counting_to.isoformat(),
        "最长连续": longest,
        "今日可得": today_star,
        "全对奖励合计": sum(bonus.values()),
        "全对奖励记录": bonus,
        "累计获得": total_earned,
        "已提取": withdrawn,
        "可提取": available,
        "提取记录": withdraws,
        "流水": flow,
        "本月": calendar_days,
        "打卡总天数": len(checked),
        "规则": {"每组最少题数": MIN_PER_SESSION, "单日上限": MAX_STAR_PER_DAY},
    }
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    print("今日已打卡：%s" % ("是" if out["今日已打卡"] else "否"))
    print("连续 %d 天（最长 %d 天）｜打卡总天数 %d" % (cur_streak, longest, len(checked)))
    print("累计获得 %d 颗｜已提取 %d｜可提取 %d" % (total_earned, withdrawn, available))
    if cur_streak:
        print("今天这组值 %d 颗星" % today_star)


if __name__ == "__main__":
    main()
