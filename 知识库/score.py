#!/usr/bin/env python
"""知识点评分引擎。

读：知识库/kps.json（定义）、题库/index.json（题）、题库/attempts.json（作答）
出：知识库/scores.json（每个知识点的评分与证据）

评分规则见 kps.json 的「评分规则」字段。要点：
  · 无证据 = null，不参与薄弱排序
  · 答对向上逼近 100，答错向下打折
  · 距上次证据每满 30 天衰减 8%（知识会生疏）

用法：
  python 知识库/score.py            # 评分并输出报告
  python 知识库/score.py --json     # 只看 scores.json 路径
"""
import argparse
import datetime
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KPS = os.path.join(HERE, "kps.json")
SCORES = os.path.join(HERE, "scores.json")

def _tuning():
    try:
        return json.load(open(os.path.join(ROOT, "题库", "tuning.json"), encoding="utf-8"))
    except Exception:
        return {}


_T = _tuning().get("评分", {})
ALPHA_UP = _T.get("答对逼近系数", 0.30)
ALPHA_DOWN = _T.get("答错折损", 0.25)
DECAY_PER_MONTH = _T.get("月度衰减", 0.92)
START = float(_T.get("起点分", 50))
MAX_SUB_DELTA = float(_T.get("单日单科最大变动", 15))   # 单日单科目均分最多涨/跌这么多


def load():
    k = json.load(open(KPS, encoding="utf-8"))
    items = json.load(open(os.path.join(ROOT, "题库", "index.json"), encoding="utf-8"))["题目"]
    _p = os.path.join(ROOT, "题库", "attempts.json")
    att = json.load(open(_p, encoding="utf-8"))["记录"] if os.path.exists(_p) else []
    if not att: print("⚠ 本地 attempts.json 已删除（2026-11-09 起不再回流云端记录），按空记录处理。")
    return k, items, att


def alias_index(k):
    idx, dup = {}, []
    for kp in k["知识点"]:
        for a in [kp["name"]] + kp.get("alias", []):
            a = a.strip()
            if not a:
                continue
            if a in idx and idx[a] != kp["id"]:
                dup.append((a, idx[a], kp["id"]))
            idx[a] = kp["id"]
    return idx, dup


def match(text, idx):
    """最长别名优先，避免「小数乘法」抢走「小数乘法·解决问题」。"""
    if not text:
        return None
    if text in idx:
        return idx[text]
    best = None
    for a, kid in idx.items():
        if a and a in text and (best is None or len(a) > best[0]):
            best = (len(a), kid)
    return best[1] if best else None


def apply_score(kp_id, ok, at, state):
    st = state.setdefault(kp_id, {"score": None, "n": 0, "last": None, "ok": 0})
    s = START if st["score"] is None else st["score"]
    s = s + (100 - s) * ALPHA_UP if ok else s * (1 - ALPHA_DOWN)
    st.update(score=round(s, 1), n=st["n"] + 1, last=at, ok=st["ok"] + (1 if ok else 0))


def decay(state, today):
    for st in state.values():
        if st["score"] is None or not st["last"]:
            continue
        days = (today - datetime.date.fromisoformat(st["last"])).days
        months = days // 30
        if months > 0:
            st["score"] = round(st["score"] * (DECAY_PER_MONTH ** months), 1)
            st["decayed"] = months


def band(s):
    if s is None:
        return "未测"
    if s >= 85:
        return "熟练"
    if s >= 70:
        return "掌握"
    if s >= 50:
        return "待巩固"
    return "薄弱"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    k, items, att = load()
    idx, dup = alias_index(k)
    by_item = {i["id"]: i for i in items}

    state, unmatched = {}, set()
    kp_sub = {kp["id"]: kp["sub"] for kp in k["知识点"]}
    recs = sorted(att, key=lambda x: (x["at"], x["id"]))
    capped = []

    # 按天重放，每天结束对每个科目的均分变化限幅
    i = 0
    while i < len(recs):
        day, j = recs[i]["at"], i
        while j < len(recs) and recs[j]["at"] == day:
            j += 1
        before = {kid: (st["score"] if st["score"] is not None else START)
                  for kid, st in state.items()}
        touched = set()

        for r in recs[i:j]:
            it = by_item.get(r["item_id"])
            names = (it or {}).get("kps", []) or []
            if not names:
                unmatched.add("(题 %s 无知识点字段)" % r["item_id"])
                continue
            hit = False
            for nm in names:
                kid = match(nm, idx)
                if kid:
                    apply_score(kid, r["ok"], r["at"], state)
                    touched.add(kp_sub.get(kid))
                    hit = True
                else:
                    unmatched.add(nm)
            if not hit:
                unmatched.add(names[0])

        for sub in sorted(x for x in touched if x):
            kids = [kid for kid in state if kp_sub.get(kid) == sub]
            pairs = [(before.get(kid, START), state[kid]["score"], kid) for kid in kids
                     if state[kid]["score"] is not None]
            if not pairs:
                continue
            delta = sum(y - x for x, y, _ in pairs) / len(pairs)
            if abs(delta) > MAX_SUB_DELTA:
                scale = MAX_SUB_DELTA / abs(delta)
                for x, y, kid in pairs:
                    state[kid]["score"] = round(x + (y - x) * scale, 1)
                capped.append((day, sub, round(delta, 1), len(pairs)))
        i = j

    today = datetime.date.today()
    decay(state, today)

    out = {"生成时间": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
           "规则": {"答对": "+30%% 缺口", "答错": "×0.75", "月衰减": "×0.92"},
           "知识点": []}
    for kp in k["知识点"]:
        st = state.get(kp["id"], {"score": None, "n": 0, "last": None, "ok": 0})
        out["知识点"].append({
            "id": kp["id"], "sub": kp["sub"], "stage": kp["stage"],
            "domain": kp["domain"], "name": kp["name"],
            "score": st["score"], "band": band(st["score"]),
            "evidence": st["n"], "ok": st["ok"], "last": st["last"],
            "decayed_months": st.get("decayed", 0),
        })
    json.dump(out, open(SCORES, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    if a.json:
        print(SCORES)
        return

    measured = [x for x in out["知识点"] if x["score"] is not None]
    print("知识点总数 %d｜有证据 %d｜未测 %d" % (
        len(out["知识点"]), len(measured), len(out["知识点"]) - len(measured)))
    if dup:
        print("\n⚠ 别名冲突 %d 处：%s" % (len(dup), dup[:3]))
    if capped:
        print("\n单日单科变化限幅（±%.0f 分）%d 次：" % (MAX_SUB_DELTA, len(capped)))
        for d, sub, delta, n in capped:
            print("  %s %s：原本会变 %+.1f 分（%d 个知识点）→ 压到 %+.1f" % (
                d, sub, delta, n, MAX_SUB_DELTA if delta > 0 else -MAX_SUB_DELTA))

    print("\n【最薄弱】")
    for x in sorted(measured, key=lambda y: y["score"])[:12]:
        print("  %-8s %-14s %5.1f  %-4s 证据%d次" % (
            x["id"], x["name"][:14], x["score"], x["band"], x["evidence"]))

    print("\n【按学科】")
    for s in ("数", "语", "英"):
        g = [x for x in measured if x["sub"] == s]
        if g:
            avg = sum(x["score"] for x in g) / len(g)
            print("  %s：%d 个知识点有证据，平均分 %.1f" % (s, len(g), avg))

    if unmatched:
        print("\n【未映射到知识点的题库标签】%d 个（需补 alias）" % len(unmatched))
        for u in sorted(unmatched)[:10]:
            print("  -", u)

    print("\n已写入 %s" % SCORES)


if __name__ == "__main__":
    main()
