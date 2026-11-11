/* AI私教 · 前端引擎
 *
 * 原来这些活都是 Python 在构建时算的：评分、打卡、节奏、今天做哪两套题。
 * 搬到浏览器里以后，只要云端有作答记录，页面自己就能更新，不用再跑构建。
 *
 * 输入：window.DB（构建时内嵌的题库）+ 云端 drill_submissions 行
 * 输出：评分 / 打卡 / 节奏 / 排期
 *
 * 规则必须和本地 Python 版一致，否则家长会看到两套数字：
 *   知识库/score.py、题库/checkin.py、题库/pace.py、刷题/make_week.py
 */
window.Engine = (function () {
  "use strict";

  /* 参数统一从 题库/tuning.json 来（构建时打进 DB.tuning），
     改参数不用动代码，跑一次 build_site 再发布就生效。 */
  var T = (window.DB && window.DB.tuning) || {};
  var S = T["评分"] || {}, C = T["打卡"] || {}, P = T["节奏"] || {}, Q = T["抽题"] || {};
  function num(o, k, d) { return o[k] === undefined || o[k] === null ? d : o[k]; }

  var ALPHA_UP = num(S, "答对逼近系数", 0.30),
      ALPHA_DOWN = num(S, "答错折损", 0.25),
      DECAY = num(S, "月度衰减", 0.92),
      START = num(S, "起点分", 50);
  var MAX_SUB_DELTA = num(S, "单日单科最大变动", 15);
  var MILESTONES = [1, 7, 21];  // D+1 / D+7 / D+21
  var MAX_STAR_PER_DAY = num(C, "单日星数上限", 10);
  var MIN_PER_SESSION = num(C, "每场最少题数", 5);
  var BONUS = C["全对奖励"] || {};
  var TARGET_SEC = num(P, "目标秒", 900), STD_N = num(P, "标准题数", 9);
  var PER_SEC = TARGET_SEC / STD_N;
  var N_MIN = num(P, "题数下限", 6), N_MAX = num(P, "题数上限", 12);
  var STEP = num(P, "单次最大变动", 2), WINDOW = num(P, "观察最近几组", 3);
  var R_SLOW = num(P, "太慢比值", 1.25), R_LATE = num(P, "偏慢比值", 1.10),
      R_OK = num(P, "正好比值", 0.85), R_FAST = num(P, "偏快比值", 0.65);
  var ACC_OK = num(P, "会做正确率", 0.80), ACC_GOOD = num(P, "又快又对正确率", 0.85),
      ACC_PERFECT = num(P, "太快全对正确率", 0.90);
  var SUB_MIN_W = num(Q, "科目权重下限", 0.15);
  var KP_WEAK = num(Q, "薄弱知识点系数", 2.0), KP_STEADY = num(Q, "巩固知识点系数", 1.8);

  /* ---------- 日期工具 ---------- */
  function ymd(d) {
    return d.getFullYear() + "-" +
      String(d.getMonth() + 1).padStart(2, "0") + "-" +
      String(d.getDate()).padStart(2, "0");
  }
  function todayStr() { return ymd(new Date()); }
  function parseDate(s) {
    var p = String(s).split("-");
    return new Date(+p[0], +p[1] - 1, +p[2]);
  }
  function dayDiff(a, b) {           // b - a，单位天
    return Math.round((parseDate(b) - parseDate(a)) / 86400000);
  }
  function addDays(s, n) {
    var d = parseDate(s); d.setDate(d.getDate() + n); return ymd(d);
  }

  /* ---------- 确定性随机（同一天同一组，刷几次都一样） ---------- */
  function hashSeed(str) {
    var h = 2166136261;
    for (var i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }
  function rng(seed) {
    var a = seed >>> 0;
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  /* ---------- 解析云端提交 ---------- */
  /* answers 形如：D20261108|V-004-01=0@74#C,V-006-01=1@20|221
     # 后面是她的作答，早期版本没有这一段。 */
  function parseAnswers(s) {
    var parts = String(s || "").split("|");
    var body = parts.length >= 2 ? parts[1] : "";
    var out = [];
    body.split(",").forEach(function (seg) {
      seg = seg.trim();
      if (!seg) return;
      var at = seg.indexOf("@"), eq = seg.indexOf("=");
      if (eq < 0 || at < 0) return;
      var id = seg.slice(0, eq).trim();
      var ok = seg.slice(eq + 1, at).trim() === "1";
      var rest = seg.slice(at + 1);
      var hash = rest.indexOf("#");
      var sec = parseInt(hash >= 0 ? rest.slice(0, hash) : rest, 10) || 0;
      var pick = hash >= 0 ? rest.slice(hash + 1).trim() : "";
      out.push({ id: id, ok: ok, sec: sec, pick: pick });
    });
    return out;
  }

  /* 同一场做了多遍只取第一遍——后面那次是看过答案重做的。 */
  function firstRuns(rows) {
    var map = {}, order = [];
    (rows || []).forEach(function (r) {
      var date = String(r.drill_date || "").slice(0, 10);
      var title = String(r.drill_title || "刷题");
      if (!date) return;
      var key = date + "|" + title;
      var ts = String(r.created_at || "");
      if (!map[key] || ts < String(map[key].created_at || "")) {
        if (!map[key]) order.push(key);
        map[key] = r;
      }
    });
    return order.map(function (k) { return map[k]; });
  }

  /* 云端行 + 内嵌纸笔记录 → 逐题记录
     纸笔记录是人工录的，不进云端表，只能靠构建时打进来。 */
  function toAttempts(rows, paperRows) {
    var out = [], seen = {};
    function add(a) {
      var k = a.mode + "|" + a.at + "|" + a.context + "|" + a.item_id;
      if (seen[k]) return;
      seen[k] = 1; out.push(a);
    }

    // 纸笔记录：优先用云端 paper_records，没有就退回构建时内嵌的那份
    if (paperRows && paperRows.length) {
      paperRows.forEach(function (r) {
        add({ item_id: r.item_id, ok: !!r.ok, sec: 0, pick: "",
              at: String(r.record_date || "").slice(0, 10),
              context: r.context || "纸笔", mode: "paper", group: 0 });
      });
    } else {
      ((window.DB && window.DB.paper) || []).forEach(function (r) {
        add({ item_id: r.item_id, ok: !!r.ok, sec: 0, pick: "",
              at: r.at, context: r.context || "纸笔", mode: "paper", group: 0 });
      });
    }

    firstRuns(rows).forEach(function (r) {
      var date = String(r.drill_date || "").slice(0, 10);
      var title = String(r.drill_title || "刷题");
      parseAnswers(r.answers).forEach(function (a) {
        add({
          item_id: a.id, ok: a.ok, sec: a.sec, pick: a.pick,
          at: date, context: title, mode: "pad",
          group: /第\s*2|二组/.test(title) ? 2 : 1
        });
      });
    });

    out.sort(function (a, b) { return a.at < b.at ? -1 : a.at > b.at ? 1 : 0; });
    return out;
  }

  /* ---------- 知识点评分 ---------- */
  /* DB.kpOf = { 题目id: [知识点id, ...] }，构建时算好 */
  /* tree 体系：题目 id -> 知识点 id，以及知识点 -> 科目。
     建一次缓存住，1053 个点扫一遍不算贵，但别每次都扫。 */
  function treeIndex() {
    if (window.__treeIdx) return window.__treeIdx;
    var q2t = {}, sub = {};
    var names = {"math": "数", "cn": "语", "en": "英"};
    var T = window.__tree || {};
    Object.keys(names).forEach(function (k) {
      var t = T[k];
      if (!t || !t.topics) return;
      t.topics.forEach(function (tp) {
        sub[tp.id] = names[k];
        (tp.q || []).forEach(function (qid) { q2t[qid] = tp.id; });
      });
    });
    window.__treeIdx = { q2t: q2t, sub: sub };
    return window.__treeIdx;
  }

  function scoreKps(attempts) {
    // 评分只认能对上 tree 的题（开源题库）。自录大纲题和变式题走复测，
    // 不进这张分数表——它们标的是单元级，对不上 tree 的知识点粒度。
    var _ti = treeIndex();
    var q2t = _ti.q2t, kpSub = _ti.sub;
    var state = {};        // kid -> {score, n, ok, last}

    function apply(kid, ok, at) {
      var st = state[kid] || (state[kid] = { score: null, n: 0, ok: 0, last: null });
      var s = st.score === null ? START : st.score;
      s = ok ? s + (100 - s) * ALPHA_UP : s * (1 - ALPHA_DOWN);
      st.score = Math.round(s * 10) / 10;
      st.n += 1; st.ok += ok ? 1 : 0; st.last = at;
    }

    // 按天重放，每天结束对每个科目的均分变化限幅
    var i = 0;
    while (i < attempts.length) {
      var day = attempts[i].at, j = i;
      while (j < attempts.length && attempts[j].at === day) j++;
      var before = {};
      Object.keys(state).forEach(function (k) {
        before[k] = state[k].score === null ? START : state[k].score;
      });
      var touched = {};

      for (var t = i; t < j; t++) {
        var a = attempts[t];
        var tid = q2t[a.item_id];
        var kids = tid ? [tid] : [];
        kids.forEach(function (kid) {
          apply(kid, a.ok, a.at);
          touched[kpSub[kid]] = 1;
        });
      }

      Object.keys(touched).forEach(function (sub) {
        var kids = Object.keys(state).filter(function (k) { return kpSub[k] === sub; });
        var pairs = kids.filter(function (k) { return state[k].score !== null; })
          .map(function (k) { return [before[k] === undefined ? START : before[k], state[k].score, k]; });
        if (!pairs.length) return;
        var delta = pairs.reduce(function (s, p) { return s + (p[1] - p[0]); }, 0) / pairs.length;
        if (Math.abs(delta) > MAX_SUB_DELTA) {
          var scale = MAX_SUB_DELTA / Math.abs(delta);
          pairs.forEach(function (p) {
            state[p[2]].score = Math.round((p[0] + (p[1] - p[0]) * scale) * 10) / 10;
          });
        }
      });
      i = j;
    }

    // 距上次证据每满 30 天衰减 8%
    var today = todayStr();
    Object.keys(state).forEach(function (k) {
      var st = state[k];
      if (st.score === null || !st.last) return;
      var months = Math.floor(dayDiff(st.last, today) / 30);
      if (months > 0) st.score = Math.round(st.score * Math.pow(DECAY, months) * 10) / 10;
    });
    return state;
  }

  /* 教材层 id 长这样：M-5A-U1-01。科目均分只算考点层，和 Python 的 score.py 保持一致；
     教材层的分数只用来决定大纲题出哪一档难度。 */
  function isTextKp(kid) { return /-\d[AB]-U/.test(kid); }

  function subAvg(state, sub) {
    var kpSub = treeIndex().sub;   // 分数按 tree 存，科目表也得用 tree 的
    var arr = Object.keys(state)
      .filter(function (k) {
        return kpSub[k] === sub && state[k].score !== null && !isTextKp(k);
      })
      .map(function (k) { return state[k].score; });
    // 样本少于 3 个时均分不可靠——一道题就能把它拉高或拉低，直接按中等算
    if (arr.length < 3) return 50;
    return arr.reduce(function (a, b) { return a + b; }, 0) / arr.length;
  }

  function band(s) {
    if (s === null || s === undefined) return "未测";
    if (s >= 85) return "熟练";
    if (s >= 70) return "掌握";
    if (s >= 50) return "待巩固";
    return "薄弱";
  }

  /* ---------- 打卡与星星 ---------- */
  function checkin(attempts, withdrawals) {
    var pad = attempts.filter(function (a) { return a.mode === "pad"; });
    var byDay = {};
    pad.forEach(function (a) {
      var d = byDay[a.at] || (byDay[a.at] = { n: 0, ok: 0, sessions: {} });
      d.n += 1; d.ok += a.ok ? 1 : 0;
      var k = a.context || "";
      d.sessions[k] = (d.sessions[k] || 0) + 1;
    });

    // 一天至少一场（同场次 ≥5 题）才算打卡
    var checked = {};
    Object.keys(byDay).forEach(function (d) {
      Object.keys(byDay[d].sessions).forEach(function (k) {
        if (byDay[d].sessions[k] >= MIN_PER_SESSION) checked[d] = 1;
      });
    });

    // 全对奖励：一场 ≥5 题且全对，1 场 +2，2 场 +5（取高不叠加）
    var perfectByDay = {};
    var sess = {};
    pad.forEach(function (a) {
      var k = a.at + "|" + (a.context || "");
      (sess[k] || (sess[k] = [])).push(a.ok);
    });
    var perfectCount = {};
    Object.keys(sess).forEach(function (k) {
      var arr = sess[k];
      if (arr.length >= MIN_PER_SESSION && arr.every(Boolean)) {
        var d = k.split("|")[0];
        perfectCount[d] = (perfectCount[d] || 0) + 1;
      }
    });
    Object.keys(perfectCount).forEach(function (d) {
      perfectByDay[d] = perfectCount[d] >= 2 ? (BONUS["两场"] || 5) : (BONUS["一场"] || 2);
    });

    // 连续天数与每天得星
    var days = Object.keys(checked).sort();
    var earned = {}, streakAt = {}, run = 0, prev = null;
    days.forEach(function (d) {
      run = (prev && dayDiff(prev, d) === 1) ? run + 1 : 1;
      streakAt[d] = run;
      var base = Math.min(run, MAX_STAR_PER_DAY);
      // 按当天答对率打折：≥80% 全拿，60–80% 减半（保底 1 颗），<60% 不给还扣 1 颗
      var day = byDay[d] || { n: 0, ok: 0 };
      var rate = day.n ? day.ok / day.n : 0;
      if (rate >= 0.8) earned[d] = base;
      else if (rate >= 0.6) earned[d] = Math.max(1, Math.floor(base / 2));
      else earned[d] = -1;  // 低于 60%：当日不给，还倒扣 1 颗（允许负）
      prev = d;
    });

    var bonusTotal = Object.keys(perfectByDay).reduce(function (s, d) { return s + perfectByDay[d]; }, 0);
    var totalEarned = Object.keys(earned).reduce(function (s, d) { return s + earned[d]; }, 0) + bonusTotal;
    var withdrawn = (withdrawals || []).reduce(function (s, w) { return s + (+w.stars || 0); }, 0);

    var today = todayStr();
    function streakTo(day) {
      var n = 0, cur = day;
      while (checked[cur]) { n++; cur = addDays(cur, -1); }
      return n;
    }
    var cur = streakTo(today), countingTo = today;
    if (cur === 0) { cur = streakTo(addDays(today, -1)); countingTo = addDays(today, -1); }
    var longest = 0;
    days.forEach(function (d) { longest = Math.max(longest, streakTo(d)); });

    // 每天明细：日历 / 流水前端重画时要用（否则只能靠构建时快照）
    var paperN = {};
    (attempts || []).filter(function (a) { return a.mode === "paper"; }).forEach(function (a) {
      paperN[a.at] = (paperN[a.at] || 0) + 1;
    });
    var dayStat = {};
    Object.keys(byDay).forEach(function (d) {
      var x = byDay[d];
      dayStat[d] = {
        n: x.n, ok: x.ok, rate: x.n ? x.ok / x.n : null,
        star: earned[d] || 0, streak: streakAt[d] || 0,
        perfect: !!perfectByDay[d], checked: !!checked[d],
        perfectGroups: perfectCount[d] || 0, paperN: paperN[d] || 0
      };
    });
    // 只交过纸笔、当天没刷题的日子也要能画出来
    Object.keys(paperN).forEach(function (d) {
      if (dayStat[d]) return;
      dayStat[d] = { n: 0, ok: 0, rate: null, star: earned[d] || 0, streak: streakAt[d] || 0,
                     perfect: false, checked: !!checked[d], perfectGroups: 0, paperN: paperN[d] };
    });

    var todayStar = checked[today] ? (earned[today] || 0) : Math.min(cur + 1, MAX_STAR_PER_DAY);
    var todayMax = Math.min(cur + 1, MAX_STAR_PER_DAY);
    var day = byDay[today] || { n: 0, ok: 0 };

    return {
      checkedToday: !!checked[today],
      streak: cur,
      countingTo: countingTo,
      longest: longest,
      todayStar: todayStar,
      todayMax: todayMax,
      todayN: day.n,
      todayOk: day.ok,
      todayRate: day.n ? day.ok / day.n : null,
      totalEarned: totalEarned,
      withdrawn: withdrawn,
      available: totalEarned - withdrawn,   // 允许负数：扣到欠着
      bonusTotal: bonusTotal,
      earned: earned,
      perfectByDay: perfectByDay,
      perfectGroups: perfectCount,
      checkedDays: checked,
      dayStat: dayStat
    };
  }

  /* ---------- 做题节奏 ---------- */
  function paceOf(attempts) {
    var groups = {};
    attempts.filter(function (a) { return a.mode === "pad"; }).forEach(function (a) {
      var k = a.at + "|" + (a.group || 1);
      var g = groups[k] || (groups[k] = { date: a.at, group: a.group || 1, n: 0, ok: 0, sec: 0 });
      g.n += 1; g.ok += a.ok ? 1 : 0; g.sec += a.sec || 0;
    });
    var list = Object.keys(groups).map(function (k) { return groups[k]; })
      .sort(function (a, b) { return a.date < b.date ? -1 : a.date > b.date ? 1 : a.group - b.group; });

    var base = { n: STD_N, focus: "weak", perSec: PER_SEC, ratio: 1, harder: false,
                 estMin: STD_N * PER_SEC / 60, judge: "起步",
                 why: "还没有用时数据，先按 9 题 / 15 分钟跑", groups: list };
    var ok = list.filter(function (g) { return g.n >= 5 && g.sec >= g.n * 5 && g.sec <= 3600; });
    if (!ok.length) return base;

    var tail = ok.slice(-WINDOW), ws = [1, 2, 3].slice(-tail.length);
    var per = 0, acc = 0, wsum = 0;
    tail.forEach(function (g, i) {
      per += ws[i] * (g.sec / g.n);
      acc += ws[i] * (g.ok / g.n);
      wsum += ws[i];
    });
    per /= wsum; acc /= wsum;

    var r = per / PER_SEC, prevN = tail[tail.length - 1].n;
    var need = Math.round(TARGET_SEC / per);
    need = Math.max(N_MIN, Math.min(N_MAX, need));
    var judge = "正好", focus = "weak", why, harder = false;

    if (r >= R_SLOW) {
      if (acc >= ACC_OK) { judge = "太慢"; focus = "steady"; why = "会做，但每题要 " + Math.round(per) + " 秒（目标 100 秒）。先降到 {N} 题，保证 15 分钟内做完；速度练上来再慢慢加回去"; }
      else { judge = "又慢又错"; focus = "steady"; why = "又慢又错，说明这一档超纲了：降到 {N} 题，抽题先往她已掌握的知识点偏"; }
    } else if (r >= R_LATE) {
      judge = "偏慢"; focus = "steady"; why = "比目标慢 " + Math.round((r - 1) * 100) + "%，题数收到 {N} 题；抽题多给她会的，先把节奏跑顺";
    } else if (r > R_OK) {
      why = "节奏正好在 15 分钟附近，维持 {N} 题，继续补薄弱点";
    } else if (r >= R_FAST) {
      if (acc >= ACC_GOOD) { judge = "偏快"; why = "又快又对，题数加到 {N} 题，并提高薄弱知识点的比例"; }
      else { judge = "偏快但没读透"; need = prevN; why = "做得快但错了 " + Math.round((1 - acc) * prevN) + " 道——不是题简单，是没读透；题数不加，做完回去检查一遍"; }
    } else {
      if (acc >= ACC_PERFECT) {
        judge = "太快";
        why = "远快于目标，题数提到 {N} 题；如果还是全对，就该上更难的知识点了";
      } else {
        judge = "快而错";
        harder = true;
        // 不再把题数压回 prevN+1：题量本来就该按「目标 900 秒 ÷ 实际每题秒」反推，
        // 压回上一组题数等于把 15 分钟的预算扔掉，只剩 2 分钟的量。
        why = "十几秒一道题，对五年级来说太快了——不是题太简单就是没读透。"
            + "题数按实际用时反推到 {N} 题，同时把难度提一档";
      }
    }

    // 差得远就一次多迈几步。原来固定 ±2，从 10 题爬到这里算出来的 30 题要爬十天，
    // 中间每一天都还是「2 分钟做完」。
    var gap = need - prevN;
    var step = Math.max(2, Math.min(STEP, Math.ceil(Math.abs(gap) / 3)));
    var n = prevN + Math.max(-step, Math.min(step, gap));
    n = Math.max(N_MIN, Math.min(N_MAX, n));
    if (n === N_MIN && (judge === "太慢" || judge === "又慢又错")) why = "题量已经压到 " + N_MIN + " 题，再减就没意义了；这一档先练速度——同样的题，目标 15 分钟内做完";
    else if (n === N_MAX && (judge === "太快" || judge === "偏快" || judge === "快而错")) why = "题量已经到 " + N_MAX + " 题上限；再想加训练量，只能换更长、更难的题目";

    return { n: n, focus: focus, perSec: per, ratio: r, acc: acc, harder: harder,
             estMin: n * per / 60, judge: judge, why: why.replace("{N}", n), groups: list };
  }

  /* ---------- 错题复测排期 ---------- */
  /* 对齐 题库/lifecycle.py：变式的作答归到它派生自的原题。 */
  function dueOf(attempts) {
    var errors = (window.DB && window.DB.errors) || [];
    var variants = (window.DB && window.DB.variants) || [];
    var fromOf = {};
    variants.forEach(function (v) { if (v.from) fromOf[v.id] = v.from; });

    var byItem = {};
    attempts.forEach(function (a) {
      var key = fromOf[a.item_id] || a.item_id;
      (byItem[key] || (byItem[key] = [])).push(a);
    });

    // 自动错题：做错过、但不在人工错题库里的题（大纲 / 开源），同样进复习排期
    var manualIds = {};
    errors.forEach(function (e) { manualIds[e.id] = 1; });
    var autoFirst = {};
    attempts.forEach(function (a) {
      if (a.ok) return;
      if (manualIds[a.item_id] || fromOf[a.item_id]) return;
      if (!autoFirst[a.item_id] || a.at < autoFirst[a.item_id]) autoFirst[a.item_id] = a.at;
    });

    var today = todayStr(), out = { list: [], due: 0, late: 0, byId: {} };

    Object.keys(autoFirst).forEach(function (id) {
      var recs = attempts.filter(function (a) { return a.item_id === id; })
        .sort(function (a, b) { return a.at < b.at ? -1 : 1; });
      var start = autoFirst[id];
      var reviews = Math.max(0, recs.length - 1);
      var okStreak = 0;
      for (var i = recs.length - 1; i >= 1; i--) {
        if (recs[i].ok) okStreak++; else break;
      }
      var st, due = null;
      if (reviews >= 3 && okStreak >= 3) st = "已巩固";
      else { st = reviews ? "复测中" : "待复测"; due = addDays(start, MILESTONES[Math.min(reviews, 2)]); }
      var late = due && due <= today ? dayDiff(due, today) : 0;
      if (due && due <= today) out.due++;
      if (late > 0) out.late++;
      out.byId[id] = { status: st, due: due, late: late, reviews: reviews, auto: true };
    });

    errors.forEach(function (e) {
      var recs = (byItem[e.id] || []).slice().sort(function (a, b) { return a.at < b.at ? -1 : 1; });
      var start = recs.length ? recs[0].at : (e.start || null);
      var reviews = Math.max(0, recs.length - 1);
      var okStreak = 0;
      for (var i = recs.length - 1; i >= 1; i--) {
        if (recs[i].ok) okStreak++; else break;
      }
      var status, due = null;
      if (reviews >= 3 && okStreak >= 3) { status = "已巩固"; }
      else if (start) {
        status = reviews ? "复测中" : "待复测";
        due = addDays(start, MILESTONES[Math.min(reviews, 2)]);
      } else { status = "待复测"; }

      var late = due && due <= today ? dayDiff(due, today) : 0;
      if (due && due <= today) out.due++;
      if (late > 0) out.late++;
      out.byId[e.id] = { status: status, due: due, late: late, reviews: reviews };
    });
    return out;
  }

  /* ---------- 专项补练：只考某一个知识点 ---------- */
  /* 诊断查出「这个点不行」或「上游没测过」时，用来生成一组针对性练习。 */
  function planFocus(focusName, kpState, items, n) {
    var want = n || 6;
    var pool = (items || []).filter(function (q) {
      return (q.kps || []).indexOf(focusName) >= 0;
    });

    // 按知识点分数决定出哪一档
    var sc = null;
    var kpOf = (window.DB && window.DB.kpOf) || {};
    for (var i = 0; i < pool.length; i++) {
      var kid = pool[i].kp || (kpOf[pool[i].id] || [])[0];
      if (kid && kpState[kid] && kpState[kid].score !== null) { sc = kpState[kid].score; break; }
    }
    var tgt = wantBand(sc);

    var ranked = pool.map(function (q) {
      return { q: q, gap: Math.abs(qBand(q) - tgt) };
    });
    ranked.sort(function (a, b) { return a.gap - b.gap; });

    return {
      title: focusName,
      n: Math.min(want, ranked.length),
      items: ranked.slice(0, Math.min(want, ranked.length)).map(function (x) { return x.q; }),
      target: tgt
    };
  }

  /* ---------- 教材进度（已学 / 进行中 / 未学） ---------- */
  /* 不存状态，每次按当天日期现算：学期起点 + 单元起始周。 */
  function curriculumProgress(today) {
    var C = (window.DB && window.DB.curriculum) || {};
    var items = C.items || [], terms = C.terms || {};
    var groups = {};
    items.forEach(function (x) {
      var k = x.sub + "|" + x.book;
      (groups[k] || (groups[k] = [])).push(x);
    });

    var out = [];
    Object.keys(groups).forEach(function (k) {
      var arr = groups[k], book = arr[0].book;
      var base = terms[book];
      if (!base) return;
      var uw = {};
      arr.forEach(function (x) { if (uw[x.unit] === undefined) uw[x.unit] = x.week; });
      var units = Object.keys(uw).map(Number).sort(function (a, b) { return a - b; });

      arr.forEach(function (x) {
        var i = units.indexOf(x.unit);
        var start = shiftDate(base, (uw[x.unit] - 1) * 7);
        var nextWeek = i + 1 < units.length ? uw[units[i + 1]] : 21;
        var end = shiftDate(base, (nextWeek - 1) * 7);
        var st = today < start ? "未学" : (today < end ? "进行中" : "已学");
        out.push({ id: x.id, sub: x.sub, book: x.book, unit: x.unit,
                   unitName: x.unitName, name: x.name, status: st,
                   start: start, end: end });
      });
    });
    return out;
  }

  function shiftDate(iso, days) {
    var d = parseDate(iso);
    d.setDate(d.getDate() + days);
    return ymd(d);
  }

  /* ---------- 大纲题的挑选 ---------- */
  /* 知识点分低就挑简单一档，分高就上难度 3；优先和原题同知识点。 */
  /* 目标难度（1–10 分）：知识点分低给简单题，分高给难题 */
  var DIFF_LADDER = Q["难度"] && Q["难度"]["分档"] ? Q["难度"]["分档"]
    : [{ "分": 80, "难度": 6 }, { "分": 70, "难度": 5 }, { "分": 0, "难度": 4 }];
  var DIFF_FLOOR = num(Q["难度"] || {}, "下限", 4);
  var DQ = Q["难度档"] || {};
  var D_HI = num(DQ, "高档分", 80), D_MID = num(DQ, "中档分", 60);
  var KP_PER_GROUP = num(Q, "同组同知识点上限", 1);
  var FQ_CFG = Q["快而错"] || {};
  var FQ_DIFF = num(FQ_CFG, "难度加", 1);

  function targetDiff(score) {
    if (score === null || score === undefined) return DIFF_FLOOR;
    for (var i = 0; i < DIFF_LADDER.length; i++) {
      if (score >= DIFF_LADDER[i]["分"]) {
        return Math.max(DIFF_FLOOR, DIFF_LADDER[i]["难度"]);
      }
    }
    return DIFF_FLOOR;
  }

  /* 难度统一成三档，避免"1–10 连续分"和"1/2/3 档"混着比 */
  function qBand(q) {
    if (q.source === "tax") {
      var d = q.difficulty || 4;         // 开源题 5 维评分，1–10
      return d >= 7 ? 3 : d >= 4 ? 2 : 1;
    }
    // 大纲题的字段是中文「难度」(1/2/3)，变式题是英文 difficulty
    return q["难度"] || q.difficulty || 2;
  }
  function wantBand(sc, harder, quick) {
    var w;
    if (sc === null || sc === undefined) w = 2;
    else if (sc >= D_HI) w = 3;
    else if (sc >= D_MID) w = 2;
    else w = 1;
    // 秒答过：这个知识点出的题偏简单，往上顶一档
    if (quick) w = Math.min(3, w + 1);
    return harder ? Math.min(3, w + 1) : w;
  }

  function pickOutlineFor(subject, kpState, used, rand, kpName, recent, learned, taxItems, harder, kpUsed, quickSet) {
    var all = ((window.DB && window.DB.outline) || []).concat(taxItems || []);
    var kpOf = (window.DB && window.DB.kpOf) || {};
    var pool = all.filter(function (q) {
      if (q.subject !== subject || used[q.id] || (recent && recent[q.id])) return false;
      // 还没学的单元不出题；没有册次信息的（老数据）放行
      if (learned && q.book) {
        if (q.unit === undefined || q.unit === null) {
          // 开源题只带册次，用「这一册有没有学过」判断
          var okBook = false;
          for (var lk in learned) {
            if (lk.indexOf(q.subject + "|" + q.book + "|") === 0 && learned[lk] !== "未学") {
              okBook = true; break;
            }
          }
          if (!okBook) return false;
        } else {
          var st = learned[q.subject + "|" + q.book + "|" + q.unit];
          if (st === "未学") return false;
        }
      }
      return true;
    });
    if (!pool.length) {
      // 这个科目近期的都做过了，退一步允许重复，总比缺题好
      pool = all.filter(function (q) { return q.subject === subject && !used[q.id]; });
    }
    if (!pool.length) return null;

    // 同知识点的题权重高一些，但不是独占——否则题库里数量多的那一类会一直霸占
    var same = kpName ? pool.filter(function (q) {
      return (q.kps || []).indexOf(kpName) >= 0;
    }) : [];
    var cand = pool;

    var items = cand.map(function (q) {
      // 知识点改认 tree 的 id：评分表现在按 tree 存，旧 kpOf 查不到就是 null
      var kid = q.kp || (q.id && treeIndex().q2t[q.id]) || (kpOf[q.id] || [])[0];
      var st = kid ? kpState[kid] : null;
      var sc = st && st.score !== null ? st.score : null;
      // 目标档：1 基础 / 2 中等 / 3 较难。
      // 以前是拿 1–10 的连续分去"撞"，大纲题 1/2/3 乘 2.5 变成 2.5/5/7.5，
      // 撞上 4–6 的目标区间永远命中中间那档，难度 3 基本出不来。
      var wantD = wantBand(sc, harder, !!(quickSet && kid && quickSet[kid]));
      var gap = Math.abs(qBand(q) - wantD);
      var base = 1 / (1 + gap * 2) + (same.length && same.indexOf(q) >= 0 ? 0.6 : 0);
      if (q.source === "tax") base += 0.8;   // 开源题覆盖广，给点加成免得被大纲题压住
      if (q.slow) base *= 1.8;               // 慢题优先：一组全是两秒能答完的短选择题等于没练
      // 本组已经出过这个知识点了，重罚——一组里连着三四道「用字母表示数」最劝退
      if (kpUsed && kid && kpUsed[kid]) base *= 0.15;
      return { q: q, w: base, gap: gap };
    });

    // 目标档有题就只出目标档的：掌握度 80 分以上还让她做基础题，等于白做
    var hit = items.filter(function (x) { return x.gap === 0; });
    if (hit.length) items = hit;

    var tot = 0;
    items.forEach(function (x) { tot += x.w; });
    var r = rand() * tot;
    for (var i = 0; i < items.length; i++) {
      r -= items[i].w;
      if (r <= 0) return items[i].q;
    }
    return items[items.length - 1].q;
  }

  /* ---------- 今天做哪两套题 ---------- */
  /* 和 make_week.py 同规则：科目配额按科目均分，科目内按知识点加权，
     近 7 天做过的降权。用日期做种子，保证同一天刷新结果不变。 */
  var SUB_ORDER = ["数", "语", "英"];

  function quota(subScore, total) {
    var w = {}, tot = 0;
    SUB_ORDER.forEach(function (s) {
      w[s] = Math.max(SUB_MIN_W, (100 - (subScore[s] === undefined ? 50 : subScore[s])) / 100);
      tot += w[s];
    });
    // 单科上限 40%：某一科再弱也不该占掉一半以上，否则孩子一天都在做同一科
    var capSub = Math.max(2, Math.ceil(total * 0.4));
    var want = {}, sum = 0;
    SUB_ORDER.forEach(function (s) {
      want[s] = Math.min(Math.max(1, Math.round(total * w[s] / tot)), capSub);
      sum += want[s];
    });
    var order = SUB_ORDER.slice().sort(function (a, b) { return w[b] - w[a]; });
    while (sum > total) {
      for (var i = order.length - 1; i >= 0 && sum > total; i--) {
        if (want[order[i]] > 1) { want[order[i]]--; sum--; }
      }
      if (order.every(function (s) { return want[s] <= 1; })) break;
    }
    while (sum < total) {
      var bumped = false;
      for (var j = 0; j < order.length && sum < total; j++) {
        if (want[order[j]] < capSub) { want[order[j]]++; sum++; bumped = true; }
      }
      if (!bumped) { want[order[0]]++; sum++; }   // 全都顶格了，只能给权重最大的
    }
    return want;
  }

  function planDay(dateStr, groupNo, kpState, pace, recentSet, overdueList, taxItems, att) {
    var variants = (window.DB && window.DB.variants) || [];
    var kpOf = (window.DB && window.DB.kpOf) || {};
    var rand = rng(hashSeed(dateStr + "#" + groupNo));
    // 第一组还账：到期复测 + 薄弱点，偏简单
    // 第二组推进：没测过的点 + 已经稳的点，偏难一档
    var isReview = (groupNo === 1);
    var harder = isReview ? false : true;

    // 秒答信号：某个知识点 5 秒内答对过 2 次以上，说明出的题太简单
    var QUICK_SEC = 5, QUICK_TIMES = 2;
    var quickCnt = {}, quickSet = {};
    (att || []).forEach(function (a) {
      if (!a || !a.ok || !a.sec || a.sec > QUICK_SEC) return;
      var kid = (kpOf[a.item_id] || [])[0];
      if (kid) quickCnt[kid] = (quickCnt[kid] || 0) + 1;
    });
    Object.keys(quickCnt).forEach(function (kid) {
      if (quickCnt[kid] >= QUICK_TIMES) quickSet[kid] = 1;
    });

    var subScore = {};
    SUB_ORDER.forEach(function (s) { subScore[s] = subAvg(kpState, s); });

    // 教材进度：只从学过的单元里出题
    var learned = {};
    curriculumProgress(dateStr).forEach(function (r) {
      learned[r.sub + "|" + r.book + "|" + r.unit] = r.status;
    });

    var n = pace.n, q = quota(subScore, n * 2);
    var picked = [];

    // 近 7 天做过的题降权。优先用实时记录——她昨天刚做的题，今天不该再出现。
    var recent = {};
    if (recentSet && Object.keys(recentSet).length) {
      Object.keys(recentSet).forEach(function (id) { recent[id] = 1; });
    } else {
      ((window.DB && window.DB.recentIds) || []).forEach(function (id) { recent[id] = 1; });
    }

    var usedIds = {}, usedBySub = {}, overdueIds = {};
    (overdueList || []).forEach(function (id) { overdueIds[id] = 1; });
    var pickedUp = 0;

    // 第一优先：到期待复测的错题，全部出，不再设 40% 上限
    // （2026-11-10 改：欠账要清零，宁可这一组做久一点）
    // （2026-11-11 改：只给第一组，第二组不碰旧账，专心往前推）
    (isReview ? (overdueList || []) : []).forEach(function (errId) {
      var vs = variants.filter(function (v) {
        // 逾期复习就是要重做，不受「近 7 天做过」限制
        return v.from === errId && !usedIds[v.id];
      });
      if (!vs.length) {
        // 自动错题（大纲 / 开源）没有变式，直接出原题
        var pool0 = (window.DB && window.DB.outline || []).concat(taxItems || []);
        var self = null;
        for (var zi = 0; zi < pool0.length; zi++) {
          if (pool0[zi].id === errId && !usedIds[errId]) { self = pool0[zi]; break; }
        }
        if (!self) return;
        usedIds[self.id] = 1;
        overdueIds[self.id] = 1;
        usedBySub[self.subject] = (usedBySub[self.subject] || 0) + 1;
        picked.push(self);
        pickedUp++;
        return;
      }
      var v = vs[Math.floor(rand() * vs.length)];
      usedIds[v.id] = 1;
      overdueIds[v.id] = 1;
      usedBySub[v.subject] = (usedBySub[v.subject] || 0) + 1;
      picked.push(v);
      pickedUp++;
    });

    var remaining = n * 2 - picked.length;   // 逾期题占掉之后还剩几个位置
    SUB_ORDER.forEach(function (s) {
      var pool = variants.filter(function (v) { return v.subject === s; });
      // 逾期题已经占掉的名额，从这一科的配额里扣掉；总数不能超过 n*2
      var wantTotal = Math.min(Math.max(0, q[s] - (usedBySub[s] || 0)), remaining);
      // 当前学期 / 之前学期的比例不是死板对半，看三科整体均分：
      // 整体弱（<60）就多练当前学期，整体强（>60）就多回头复习。
      var _sc = [subScore["数"], subScore["语"], subScore["英"]].map(function (x) {
        return x === undefined || x === null ? 50 : x;
      });
      var _overall = (_sc[0] + _sc[1] + _sc[2]) / 3;
      var prevRatio = Math.max(0.2, Math.min(0.8, 0.5 + (_overall - 60) / 100));
      var want = Math.max(0, Math.round(wantTotal * (1 - prevRatio)));
      // 按知识点分组加权
      var byKp = {};
      pool.forEach(function (v) {
        var k = (kpOf[v.id] || ["_"])[0];
        (byKp[k] || (byKp[k] = [])).push(v);
      });
      var kpIds = Object.keys(byKp);
      var wt = {};
      kpIds.forEach(function (kid) {
        var sc = kpState[kid] && kpState[kid].score !== null ? kpState[kid].score : 50;
        wt[kid] = pace.focus === "steady" ? 1 + (sc / 100) * KP_STEADY : 1 + (1 - sc / 100) * KP_WEAK;
      });

      var chosen = [];
      var guard = 0;
      // 同一个知识点在一组里最多出几道。默认 1 道——连出三道「阅读速度」，
      // 孩子会觉得在重复做同一道题。池子不够再逐级放开。
      var kpCount = {}, kpCap = Math.max(1, KP_PER_GROUP);
      // 逾期复习阶段已经选走的题也占名额，否则补足时又堆回同一个知识点
      picked.forEach(function (v) {
        var k = (kpOf[v.id] || [])[0];
        if (k) kpCount[k] = (kpCount[k] || 0) + 1;
      });
      while (chosen.length < want && guard++ < 200) {
        // 第一组只挑弱项（<70），第二组只挑未测或已稳（>=70）。
        // 先严格过滤；过滤完没题就放开，否则第二组会空。
        var kpScore = function (k) {
          var st = kpState[k];
          return (st && st.score !== null && st.score !== undefined) ? st.score : 100;
        };
        var kpFit = function (k) {
          var sc = kpScore(k);
          return isReview ? sc < 70 : sc >= 70;
        };
        var availBase = kpIds.filter(function (k) {
          return wt[k] > 0 && (kpCount[k] || 0) < kpCap &&
            byKp[k].some(function (v) { return chosen.indexOf(v) < 0 && !usedIds[v.id]; });
        });
        var avail = availBase.filter(kpFit);
        if (!avail.length) avail = availBase;   // 这一科没合适的点，放开
        if (!avail.length) {
          if (kpCap >= 3) break;      // 放开到 3 道仍然没得选，说明这一科真的没题了
          kpCap++; continue;
        }
        // 按掌握度升序取最低的那个点（原来是加权随机）。
        // 没测过的记 100 分排在最后——先补已知薄弱，再摸底未知。
        avail.sort(function (a, b) { return kpScore(a) - kpScore(b); });
        var pickKp = avail[0];
        var arr = byKp[pickKp].filter(function (v) {
          // usedIds 里的是逾期阶段已经选走的，不能再选一次（否则同一道题会出现两遍）
          return chosen.indexOf(v) < 0 && !usedIds[v.id];
        });
        if (!arr.length) { wt[pickKp] = 0; continue; }
        // 组内随机，近期做过的不优先
        var fresh = arr.filter(function (v) { return !recent[v.id]; });
        var src = fresh.length ? fresh : arr;
        var v = src[Math.floor(rand() * src.length)];
        chosen.push(v);
        kpCount[pickKp] = (kpCount[pickKp] || 0) + 1;
      }
      // 变式池不够（语文只有 6 道），用大纲题补足，保证每组题数稳定
      while (chosen.length < want) {
        var fill = pickOutlineFor(s, kpState, usedIds, rand, "", recent, learned, taxItems, harder, kpCount, quickSet);
        if (!fill) break;
        usedIds[fill.id] = 1;
        chosen.push(fill);
        var _fk = (kpOf[fill.id] || [])[0];
        if (_fk) kpCount[_fk] = (kpCount[_fk] || 0) + 1;
      }
      // 之前学期（一到四年级）：补足另一半配额，按掌握度升序
      // 这些册早就学过，靠衰减慢慢掉分，掉了说明该回头练
      var prevQuota = wantTotal - chosen.length;
      if (prevQuota > 0) {
        var prevPool = (taxItems || []).concat((window.DB && window.DB.outline) || [])
          .filter(function (v) {
            if (!v || usedIds[v.id] || !v.book) return false;
            if (!/^[1-4](上|下)$/.test(v.book)) return false;
            if (recent && recent[v.id]) return false;
            if (learned && v.book) {
              // tax 里册次是「1上」，curriculum 里是「一上」，先统一再比
              var BOOK_CN = { "1": "一", "2": "二", "3": "三", "4": "四", "5": "五", "6": "六" };
              var bookCn = String(v.book).replace(/^([1-6])/, function (m) { return BOOK_CN[m]; });
              var okBook = false;
              for (var lk in learned) {
                if (lk.indexOf(v.subject + "|" + bookCn + "|") === 0 && learned[lk] !== "未学") { okBook = true; break; }
              }
              if (!okBook) return false;
            }
            return true;
          });
        var ti = treeIndex().q2t;
        // 第一组补弱项，第二组补没测过 / 已经稳的
        var _prevFit = function (v) {
          var k = ti[v.id];
          var sc = (k && kpState[k] && kpState[k].score !== null && kpState[k].score !== undefined)
            ? kpState[k].score : 100;
          return isReview ? sc < 70 : sc >= 70;
        };
        var _prevAll = prevPool.slice();
        prevPool = prevPool.filter(_prevFit);
        if (!prevPool.length) prevPool = _prevAll;
        prevPool.sort(function (a, b) {
          var ka = ti[a.id], kb = ti[b.id];
          var sa = (ka && kpState[ka] && kpState[ka].score !== null && kpState[ka].score !== undefined)
            ? kpState[ka].score : 100;
          var sb = (kb && kpState[kb] && kpState[kb].score !== null && kpState[kb].score !== undefined)
            ? kpState[kb].score : 100;
          return sa - sb;
        });
        var takenPrev = 0;
        for (var pi = 0; pi < prevPool.length && takenPrev < prevQuota; pi++) {
          var pv = prevPool[pi];
          if (usedIds[pv.id]) continue;
          usedIds[pv.id] = 1;
          chosen.push(pv);
          takenPrev++;
        }
      }

      picked = picked.concat(chosen);
      remaining -= chosen.length;
    });

    // 近 7 天做过的变式，换成同知识点的大纲题——错题复习靠间隔，重复做同一道没意义
    picked.forEach(function (v) { usedIds[v.id] = 1; });
    var kpAll = {};
    picked.forEach(function (v) { var k = (kpOf[v.id] || [])[0]; if (k) kpAll[k] = (kpAll[k] || 0) + 1; });
    picked = picked.map(function (v) {
      // 逾期题必须重做，不能被「近期做过」换掉
      if (!recent[v.id] || overdueIds[v.id]) return v;
      var alt = pickOutlineFor(v.subject, kpState, usedIds, rand, (v.kps || [])[0] || "", recent, learned, taxItems, harder, kpAll, quickSet);
      if (!alt) return v;
      usedIds[alt.id] = 1;
      return alt;
    });

    // 每组至少一道慢题。短选择题两秒就能答完，一组全是这种题等于白练。
    // 不够就从池子里补，换掉一道「不是逾期、也不是慢题」的普通题，总数不变。
    var SLOW_PER_GROUP = 1;
    var slowPool = ((window.DB && window.DB.outline) || []).concat(taxItems || [])
      .filter(function (q) { return q.slow && !usedIds[q.id]; });
    var haveSlow = picked.filter(function (v) { return v.slow; }).length;
    var needSlow = SLOW_PER_GROUP * 2 - haveSlow;
    while (needSlow > 0 && slowPool.length) {
      var cand = slowPool.splice(Math.floor(rand() * slowPool.length), 1)[0];
      var ri = -1;
      for (var qi = picked.length - 1; qi >= 0; qi--) {
        if (!picked[qi].slow && !overdueIds[picked[qi].id]) { ri = qi; break; }
      }
      if (ri < 0) break;
      usedIds[cand.id] = 1;
      picked[ri] = cand;
      needSlow--;
    }

    // 分两组：第一组专做到期的错题（欠账清零），第二组做新题和巩固。
    var g1 = [], g2 = [];
    picked.forEach(function (v) {
      if (overdueIds[v.id]) g1.push(v);
      else g2.push(v);
    });
    // 第一组不足一组题量时，从第二组挪过来补足——「做不满 15 分钟就补别的」
    while (g1.length < n && g2.length > 0) {
      g1.push(g2.shift());
    }


    // 分组时慢题可能被分堆到同一组，这里保证两组各至少一道
    function slowCount(g) { return g.filter(function (v) { return v.slow; }).length; }
    if (slowCount(g1) === 0 || slowCount(g2) === 0) {
      var from = slowCount(g1) > slowCount(g2) ? g1 : g2;
      var to = from === g1 ? g2 : g1;
      if (slowCount(from) >= 2) {
        var si = -1, ti = -1;
        for (var a = 0; a < from.length; a++) { if (from[a].slow) { si = a; break; } }
        for (var b = to.length - 1; b >= 0; b--) {
          if (!to[b].slow && !overdueIds[to[b].id]) { ti = b; break; }
        }
        if (si >= 0 && ti >= 0) {
          var sv = from[si]; from[si] = to[ti]; to[ti] = sv;
        }
      }
    }

    return {
      date: dateStr,
      n: n,
      judge: pace.judge,
      perSec: pace.perSec,
      acc: pace.acc,
      minutes: TARGET_SEC / 60,   // 时长是硬约束，永远 15 分钟；变的只有题量和难度
      quota: q,
      subScore: subScore,
      groups: [g1, g2].map(function (arr, i) {
        return { name: "第 " + (i + 1) + " 组", ids: arr.map(function (v) { return v.id; }) };
      }),
      diffStat: (function () {
        var sum = 0, hard = 0;
        picked.forEach(function (v) {
          var d = v.source === "tax" ? (v.difficulty || 4)
                : (v["难度分"] || (v.difficulty ? v.difficulty * 2.5 : 4));
          sum += d;
          if (d >= 6) hard++;
        });
        return { avg: sum / Math.max(1, picked.length), hard: hard };
      })()
    };
  }

  function recentOf(attempts, days) {
    var cut = addDays(todayStr(), -(days || 7));
    var m = {};
    (attempts || []).forEach(function (a) {
      if (a.at >= cut) m[a.item_id] = 1;
    });
    return m;
  }

  return {
    ymd: ymd, todayStr: todayStr, addDays: addDays, dayDiff: dayDiff, recentOf: recentOf,
    parseAnswers: parseAnswers, firstRuns: firstRuns, toAttempts: toAttempts,
    scoreKps: scoreKps, subAvg: subAvg, band: band,
    checkin: checkin, paceOf: paceOf, planDay: planDay, quota: quota, dueOf: dueOf,
    curriculumProgress: curriculumProgress, planFocus: planFocus,
    consts: { ALPHA_UP: ALPHA_UP, ALPHA_DOWN: ALPHA_DOWN, START: START,
              TARGET_SEC: TARGET_SEC, STD_N: STD_N, MAX_STAR_PER_DAY: MAX_STAR_PER_DAY,
              MILESTONES: MILESTONES, MAX_SUB_DELTA: MAX_SUB_DELTA }
  };
})();
