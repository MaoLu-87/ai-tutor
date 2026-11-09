/* 知识树 · 单册视图（三科）
   数据：assets/tree-math.json（节点 + 先修边 + 题目挂载）
   状态：云端作答实时算 */
(function () {
  var T = null, byId = {}, qToTopic = {}, pre = {}, suc = {};
  var cur = null, opened = {};
  var cache = {}, curSub = "math";
  var SUBS = [{ k: "math", n: "数学" }, { k: "cn", n: "语文" }, { k: "en", n: "英语" }];
  var doneMap = {}, okMap = {};

  var BOOKS = [];
  for (var g = 1; g <= 6; g++) for (var i = 0; i < 2; i++)
    BOOKS.push({ g: g, s: i ? "下" : "上", label: g + (i ? "下" : "上") });

  function esc(t) {
    return String(t == null ? "" : t).replace(/&/g, "&amp;").replace(/</g, "&lt;");
  }

  function rateOf(id) {
    var d = doneMap[id] || 0;
    if (!d) return null;
    return (okMap[id] || 0) / d;
  }

  function colorOf(id, hasQ) {
    var r = rateOf(id);
    if (r === null) return hasQ ? "#B4B2A9" : "#DCD5D8";
    if (r >= 0.8) return "#1D9E75";
    if (r >= 0.6) return "#EF9F27";
    return "#E24B4A";
  }

  function stateText(id, hasQ) {
    var r = rateOf(id);
    if (r === null) return hasQ ? "未测" : "待补题";
    var d = doneMap[id], o = okMap[id] || 0;
    return "掌握 " + Math.round(r * 100) + "%（" + o + "/" + d + "）";
  }

  function nodeCard(t) {
    var hasQ = (t.q || []).length > 0;
    var open = opened[t.id];
    var preN = (pre[t.id] || []).length, sucN = (suc[t.id] || []).length;

    var head = '<div data-id="' + t.id + '" style="display:flex;gap:10px;align-items:flex-start;'
      + 'padding:9px 0;border-bottom:1px solid #F8EFF2;cursor:pointer">'
      + '<span style="width:8px;height:8px;border-radius:50%;margin-top:6px;flex:none;background:'
      + colorOf(t.id, hasQ) + '"></span>'
      + '<div style="flex:1;min-width:0">'
      + '<div style="font-size:13.5px;color:#3E3037' + (hasQ ? "" : ";opacity:.65") + '">'
      + esc(t.name) + '</div>'
      + '<div class="meta" style="margin-top:2px">' + stateText(t.id, hasQ)
      + (preN ? " · 前置 " + preN : "") + (sucN ? " · 后继 " + sucN : "") + '</div>'
      + '</div>'
      + (open ? '<span class="meta" style="flex:none">收起</span>'
              : '<span class="meta" style="flex:none">展开</span>')
      + '</div>';

    if (!open) return head;

    var body = '<div style="padding:0 0 12px 18px">';
    if (t.d) body += '<div class="meta" style="margin-bottom:8px;line-height:1.7">' + esc(t.d) + '</div>';

    if (t.c && t.c.length) {
      body += '<div style="margin-bottom:8px"><div class="meta" style="font-weight:500">掌握标准</div>'
        + t.c.map(function (x) { return '<div class="meta" style="line-height:1.7">· ' + esc(x) + '</div>'; }).join("")
        + '</div>';
    }

    if (preN) {
      body += '<div style="margin-bottom:8px"><div class="meta" style="font-weight:500">要先会</div>'
        + (pre[t.id] || []).map(function (pid) {
          var p = byId[pid];
          return p ? '<div class="meta" style="line-height:1.7">· ' + esc(p.name)
            + ' <span style="opacity:.6">' + p.g + p.s + '</span></div>' : "";
        }).join("") + '</div>';
    }

    if (sucN) {
      body += '<div style="margin-bottom:8px"><div class="meta" style="font-weight:500">学会后能学</div>'
        + (suc[t.id] || []).slice(0, 6).map(function (sid) {
          var s = byId[sid];
          return s ? '<div class="meta" style="line-height:1.7">· ' + esc(s.name)
            + ' <span style="opacity:.6">' + s.g + s.s + '</span></div>' : "";
        }).join("")
        + (sucN > 6 ? '<div class="meta" style="opacity:.6">… 还有 ' + (sucN - 6) + ' 个</div>' : "")
        + '</div>';
    }

    if (hasQ) {
      body += '<div><div class="meta" style="font-weight:500">她的题（' + t.q.length + ' 道）</div>'
        + t.q.slice(0, 8).map(function (qid) {
          return '<div class="meta" style="line-height:1.7">· ' + esc(qid) + '</div>';
        }).join("")
        + (t.q.length > 8 ? '<div class="meta" style="opacity:.6">… 还有 ' + (t.q.length - 8) + ' 道</div>' : "")
        + '</div>';
    } else {
      body += '<div class="meta" style="color:#B9ACB2">这个点还没有题，属于补题清单。</div>';
    }

    return head + body + '</div>';
  }

  /* 只沿 hard 边往上追，最多 3 层；soft 边不算地基 */
  function traceUp(id, depth) {
    var out = [], seen = {};
    (function walk(nid, d) {
      if (d > (depth || 3)) return;
      (pre[nid] || []).forEach(function (e) {
        if (!e.hard || seen[e.id] || !byId[e.id]) return;
        seen[e.id] = 1;
        out.push({ node: byId[e.id], level: d });
        walk(e.id, d + 1);
      });
    })(id, 1);
    return out;
  }

  function diagnose() {
    var weak = T.topics.filter(function (t) {
      var d = doneMap[t.id] || 0;
      return d > 0 && (okMap[t.id] || 0) / d < 0.6;
    });
    if (!weak.length) return "";

    var cards = weak.map(function (t) {
      var d = doneMap[t.id], o = okMap[t.id] || 0;
      var ups = traceUp(t.id, 3);

      var lowUp = ups.filter(function (u) {
        var ud = doneMap[u.node.id] || 0;
        return ud > 0 && (okMap[u.node.id] || 0) / ud < 0.6;
      });
      var untested = ups.filter(function (u) { return !doneMap[u.node.id]; });

      var kind, color, tip, act, actName;
      if (lowUp.length) {
        kind = "地基有问题";
        color = "#E24B4A";
        actName = lowUp[0].node.name;
        tip = "先补「" + actName + "」，再回来练这个";
        act = "补地基 · 练「" + actName + "」";
      } else if (untested.length) {
        kind = "上游没测过";
        color = "#EF9F27";
        actName = untested[0].node.name;
        tip = "先测「" + actName + "」，确认地基再练这里";
        act = "先测「" + actName + "」";
      } else {
        kind = "这个点本身";
        color = "#185FA5";
        actName = t.name;
        tip = "地基都过了，是这个知识点没吃透，集中练";
        act = "集中练「" + actName + "」";
      }
      var btn = '<a href="drill.html?focus=' + encodeURIComponent(actName) + location.search.replace(/^\?/, "&")
        + '" style="display:inline-block;margin-top:8px;padding:7px 14px;border-radius:999px;'
        + 'background:' + color + ';color:#fff;font-size:12.5px;text-decoration:none">'
        + act + ' →</a>';

      var upTxt = ups.length
        ? '<div class="meta" style="margin-top:5px">上游 ' + ups.length + ' 个（只算硬依赖）：'
          + ups.slice(0, 5).map(function (u) {
              var ud = doneMap[u.node.id] || 0;
              var ur = ud ? Math.round((okMap[u.node.id] || 0) / ud * 100) + "%" : "未测";
              return esc(u.node.name) + "（" + ur + "，" + u.node.g + u.node.s + "）";
            }).join("、")
          + (ups.length > 5 ? "…" : "") + '</div>'
        : '<div class="meta" style="margin-top:5px">这是根节点，没有硬依赖上游</div>';

      return '<div style="padding:9px 0;border-bottom:1px solid #F8EFF2">'
        + '<div style="display:flex;gap:8px;align-items:baseline">'
        + '<span style="width:6px;height:6px;border-radius:50%;flex:none;margin-top:6px;background:' + color + '"></span>'
        + '<div style="flex:1"><b style="font-size:13px">' + esc(t.name) + '</b>'
        + '<span class="meta">　错 ' + (d - o) + "/" + d + '</span>'
        + '<div class="meta" style="margin-top:2px;color:' + color + '">' + kind + '</div>'
        + upTxt
        + '<div class="meta" style="margin-top:4px;color:#5F5E5A">' + tip + '</div>'
        + btn
        + '</div></div></div>';
    }).join("");

    return '<details class="card" style="margin-bottom:12px">'
      + '<summary style="font-weight:500;font-size:13.5px;cursor:pointer">诊断 · '
      + weak.length + ' 个点答对率不到 60%（点开看结论）</summary>'
      + '<div class="meta" style="margin:6px 0 4px">沿「要先会」往上找一层，看是地基塌了还是这个点本身没吃透</div>'
      + cards + '</details>';
  }

  /* 补题清单：没题、但被别的点依赖的节点，按重要度排 */
  function todoList() {
    var cand = T.topics.filter(function (t) {
      return !(t.q || []).length && (suc[t.id] || []).length > 0;
    });
    if (!cand.length) return "";
    cand.sort(function (a, b) { return (suc[b.id] || []).length - (suc[a.id] || []).length; });

    var rows = cand.slice(0, 12).map(function (t, i) {
      var n = (suc[t.id] || []).length;
      return '<div style="display:flex;gap:10px;padding:7px 0;border-bottom:1px solid #F8EFF2">'
        + '<span class="meta" style="flex:none;width:18px">' + (i + 1) + '</span>'
        + '<div style="flex:1"><div style="font-size:13px">' + esc(t.name) + '</div>'
        + '<div class="meta" style="margin-top:2px">' + t.g + t.s + ' · ' + esc((t.ch || "").replace(/^.+?册\s*/, ""))
        + ' · 有 ' + n + ' 个点依赖它</div></div></div>';
    }).join("");

    return '<details class="card" style="margin-bottom:12px">'
      + '<summary style="font-weight:500;font-size:13.5px;cursor:pointer">补题清单 · '
      + cand.length + ' 个点没题</summary>'
      + '<div class="meta" style="margin:6px 0 4px">按「有多少个点依赖它」排序，排前面的补了最划算</div>'
      + rows + '</details>';
  }

  function render() {
    if (!cur) {
      var now = new Date(), m = now.getMonth() + 1;
      cur = { g: 5, s: (m >= 9 || m <= 1) ? "上" : "下" };
    }
    var box = document.getElementById("tree");
    var list = T.topics.filter(function (t) { return t.g === cur.g && t.s === cur.s; });
    if (!list.length) {
      box.innerHTML = '<div class="card empty">这一册没有节点</div>';
      return;
    }

    // 按章分组
    var groups = {}, order = [];
    list.forEach(function (t) {
      var k = t.ch || "未分单元";
      if (!groups[k]) { groups[k] = []; order.push(k); }
      groups[k].push(t);
    });

    var html = order.map(function (k) {
      var arr = groups[k];
      var has = arr.filter(function (t) { return (t.q || []).length; }).length;
      return '<div class="card" style="margin-bottom:12px">'
        + '<div class="row" style="margin-bottom:4px"><b style="font-size:13px">'
        + esc(k.replace(/^.+?册\s*/, "")) + '</b>'
        + '<span class="meta">' + arr.length + ' 个点 · ' + has + ' 个有题</span></div>'
        + arr.map(nodeCard).join("") + '</div>';
    }).join("");

    box.innerHTML = diagnose() + todoList() + html;

    box.querySelectorAll("[data-id]").forEach(function (el) {
      el.onclick = function () {
        var id = el.dataset.id;
        opened[id] = !opened[id];
        render();
      };
    });

    var stat = list.filter(function (t) { return (t.q || []).length; }).length;
    document.getElementById("t_stat").textContent =
      cur.g + cur.s + " · " + list.length + " 个知识点 · " + stat + " 个有题";
  }

  function renderBooks() {
    document.getElementById("books").innerHTML = BOOKS.map(function (b) {
      var on = cur && b.g === cur.g && b.s === cur.s;
      return '<button data-b="' + b.g + b.s + '" style="border:1px solid ' + (on ? "#FFC9D8" : "#EFE3E8")
        + ';background:' + (on ? "#FFE7EE" : "#fff") + ';color:' + (on ? "#E85E86" : "#8B7B83")
        + ';font-size:12.5px;font-family:inherit;padding:6px 11px;border-radius:999px;'
        + 'cursor:pointer;' + (on ? "font-weight:500" : "") + '">' + b.label + '</button>';
    }).join("");
    document.querySelectorAll("[data-b]").forEach(function (b) {
      b.onclick = function () {
        var k = b.dataset.b;
        cur = { g: parseInt(k[0], 10), s: k[1] };
        opened = {};
        renderBooks(); render();
      };
    });
  }

  async function boot() {
    function reindex() {
      byId = {}; qToTopic = {}; pre = {}; suc = {};
      T.topics.forEach(function (t) {
        byId[t.id] = t;
        (t.q || []).forEach(function (q) { qToTopic[q] = t.id; });
      });
      T.edges.forEach(function (e) {
        (pre[e.t] || (pre[e.t] = [])).push({ id: e.p, hard: e.s === "hard" });
        (suc[e.p] || (suc[e.p] = [])).push(e.t);
      });
    }
    window.onerror = function (m, f, l) {
      var e = document.getElementById("t_stat");
      if (e) e.textContent = "出错：" + m + "（第 " + l + " 行）";
    };
    async function loadSub(k) {
      if (!cache[k]) {
        var r = await fetch("assets/tree-" + k + ".json" + location.search);
        cache[k] = await r.json();
      }
      T = cache[k];
      reindex();
      opened = {};
      cur = null;
      renderSubs();
      renderBooks();
      render();
    }

    function renderSubs() {
      document.getElementById("subs").innerHTML = SUBS.map(function (x) {
        var on = x.k === curSub;
        return '<button data-sub="' + x.k + '" style="border:1px solid ' + (on ? "#FFC9D8" : "#EFE3E8")
          + ';background:' + (on ? "#FFE7E8" : "#fff") + ';color:' + (on ? "#E85E86" : "#8B7B83")
          + ';font-size:13px;font-family:inherit;padding:7px 16px;border-radius:999px;cursor:pointer;'
          + (on ? "font-weight:500" : "") + '">' + x.n + '</button>';
      }).join("");
      document.querySelectorAll("[data-sub]").forEach(function (b) {
        b.onclick = async function () {
          curSub = b.dataset.sub;
          await loadSub(curSub);
        };
      });
    }

    try {
      await loadSub("math");
    } catch (e) {
      document.getElementById("tree").innerHTML =
        '<div class="card empty">图谱数据没加载出来：' + (e && e.message ? e.message : e) + '</div>';
      return;
    }



    var cloud = null;
    try {
      cloud = WorkBuddyCloud.createWorkBuddyCloud({
        endpoint: DB.cloud.endpoint, publishableKey: DB.cloud.key
      });
    } catch (e) {}

    var att = [];
    if (cloud) {
      var rows = [], pp = [];
      try { var a = await cloud.database.from("drill_submissions").select("*"); if (!a.error) rows = a.data || []; } catch (e) {}
      try { var b = await cloud.database.from("paper_records").select("*"); if (!b.error) pp = b.data || []; } catch (e) {}
      att = Engine.toAttempts(rows, pp);
    }

    att.forEach(function (a) {
      var tid = qToTopic[a.item_id];
      if (!tid) return;
      doneMap[tid] = (doneMap[tid] || 0) + 1;
      if (a.ok) okMap[tid] = (okMap[tid] || 0) + 1;
    });

    renderBooks();
    render();
  }

  boot();
})();
