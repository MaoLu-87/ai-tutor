/* 题目库页面：把三个题库合成一个可筛选、可分页的列表。
   数据来自 assets/db.js（构建时注入）。 */
(function () {
  var ALL = [];
  window.__taxLoaded = false;

  (DB.errors || []).forEach(function (e) {
    ALL.push({
      id: e.id, sub: e.subject, kp: (e.kps || [])[0] || "",
      stem: e.stem, ans: e.answer, exp: e.explain || "",
      options: e.options || [],
      cause: e.cause_note || "", wrong: e.wrong || "",
      diff: e.difficulty ? e.difficulty * 2.5 : 4, src: "错题",
      rt: (e.retests || []).slice(-1)[0]
    });
  });
  // 手动录入的错题库（数学/语文/英语），比自动错题多了错因、讲解和变式
  var SUB_CN = { math: "数", cn: "语", en: "英" };
  Object.keys(DB.wrong || {}).forEach(function (k) {
    (DB.wrong[k] || []).forEach(function (w) {
      var dup = ALL.some(function (x) { return x.id === w.id; });
      if (dup) return;
      ALL.push({
        id: w.id, sub: SUB_CN[k] || "", kp: w["知识点"] || "",
        stem: w["题目"] || "", ans: w["正确答案"] || "", exp: w["正确思路"] || "",
        options: [], cause: w["错因说明"] || "", wrong: w["孩子答案"] || "",
        diff: (w["难度"] || 3) * 2.5, src: "错题"
      });
    });
  });

  (DB.variants || []).forEach(function (v) {
    ALL.push({
      id: v.id, sub: v.subject, kp: (v.kps || [])[0] || "",
      stem: v.stem, ans: ansText(v), exp: v.explain || "",
      cause: "", wrong: "", diff: v.difficulty ? v.difficulty * 2.5 : 4, src: "变式"
    });
  });
  (DB.outline || []).forEach(function (v) {
    ALL.push({
      id: v.id, sub: v.subject, kp: (v.kps || [])[0] || "",
      stem: v.stem, ans: ansText(v), exp: v.explain || "",
      cause: "", wrong: "", diff: v["难度分"] || 4, src: "大纲"
    });
  });

  async function loadTax() {
    for (var f of ["tax-math.json", "tax-cn.json", "tax-en.json"]) {
      try {
        var r = await fetch("assets/" + f + location.search);
        if (!r.ok) continue;
        var arr = await r.json();
        arr.forEach(function (v) {
          ALL.push({
            id: v.id, sub: v.subject, kp: (v.kps || [])[0] || "",
            stem: v.stem, ans: ansText(v), exp: v.explain || "",
            cause: "", wrong: "", diff: v.difficulty || 4, src: "开源"
          });
        });
      } catch (e) {}
    }
  }

  function ansText(q) {
    var a = q.answer;
    var opts = q.options || [];
    if (q.type === "choice" || q.type === "listening") {
      return (typeof a === "number" && opts[a] !== undefined)
        ? ("ABCD"[a] + ". " + opts[a]) : String(a);
    }
    return String(a);
  }

  var PER = 50, page = 1, fs = "全部", fu = "全部", kw = "";
  var TAG = { "错题": "#D2604F", "变式": "#E85E86", "大纲": "#2E9C87", "开源": "#378ADD", "补充": "#7F77DD" };

  function esc(t) {
    return String(t == null ? "" : t)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function match(q) {
    if (fs !== "全部" && q.src !== fs) return false;
    if (fu !== "全部" && q.sub !== fu) return false;
    if (kw) {
      var s = (q.id + q.stem + q.kp).toLowerCase();
      if (s.indexOf(kw) < 0) return false;
    }
    return true;
  }

  function card(q) {
    var dnum = Math.round(q.diff);
    var rt = q.rt
      ? '<span class="tag warn" style="margin-left:6px">复测' + esc(q.rt["结果"]) +
        " " + esc(String(q.rt["日期"]).slice(5)) + "</span>"
      : "";
    var detail = "";
    if (q.wrong) detail += '<div><span class="k">孩子写的</span>　' + esc(q.wrong) + "</div>";
    detail += '<div><span class="k">答案</span>　' + esc(q.ans) + "</div>";
    if (q.exp) detail += '<div style="margin-top:6px"><span class="k">讲解</span>　' + esc(q.exp) + "</div>";
    if (q.cause) detail += '<div style="margin-top:6px"><span class="k">错因</span>　' + esc(q.cause) + "</div>";

    var optHtml = "";
    if ((q.options || []).length) {
      optHtml = '<div style="margin-top:6px">' + q.options.map(function (o, i) {
        return '<div class="meta" style="line-height:1.7">' + "ABCD"[i] + ". " + esc(o) + '</div>';
      }).join("") + '</div>';
    }

    return '<div class="item"><div class="row"><div class="stem">' + esc(q.stem) + "</div>" +
      '<span class="meta" style="white-space:nowrap">' + dnum + ' 分</span></div>' +
      optHtml + '<div class="meta">' + esc(q.id) + " · " + esc(q.kp || "—") +
      '<span class="qsrc" style="background:' + TAG[q.src] + '1a;color:' + TAG[q.src] + '">' +
      q.src + "</span>" + rt + "</div>" +
      "<details><summary>看答案和讲解</summary><div class=\"detail\">" + detail +
      "</div></details></div>";
  }

  function render() {
    var list = ALL.filter(match);
    var pages = Math.max(1, Math.ceil(list.length / PER));
    if (page > pages) page = pages;
    var part = list.slice((page - 1) * PER, page * PER);

    document.getElementById("stat").textContent =
      "筛出 " + list.length + " 道" + (pages > 1 ? "，第 " + page + " / " + pages + " 页" : "");
    var subEl = document.getElementById("bank_sub");
    if (subEl) {
      var c = {};
      ALL.forEach(function (q) { c[q.src] = (c[q.src] || 0) + 1; });
      subEl.textContent = "共 " + ALL.length + " 道 · 错题 " + (c["错题"] || 0)
        + " / 变式 " + (c["变式"] || 0) + " / 大纲 " + (c["大纲"] || 0)
        + " / 开源 " + (c["开源"] || 0);
    }
    document.getElementById("list").innerHTML = part.length
      ? part.map(card).join("")
      : '<div class="card empty">没有符合条件的题</div>';

    var pg = "";
    if (pages > 1) {
      pg += '<button class="pg" data-p="' + (page - 1) + '"' + (page <= 1 ? " disabled" : "") + ">‹</button>";
      var a = Math.max(1, page - 2), b = Math.min(pages, a + 4);
      a = Math.max(1, b - 4);
      for (var i = a; i <= b; i++) {
        pg += '<button class="pg' + (i === page ? " on" : "") + '" data-p="' + i + '">' + i + "</button>";
      }
      pg += '<button class="pg" data-p="' + (page + 1) + '"' + (page >= pages ? " disabled" : "") + ">›</button>";
    }
    document.getElementById("pager").innerHTML = pg;

    document.querySelectorAll(".pg").forEach(function (b) {
      b.onclick = function () {
        var v = parseInt(b.dataset.p, 10);
        if (v >= 1 && v <= pages) {
          page = v; render();
          window.scrollTo({ top: 0, behavior: "smooth" });
        }
      };
    });
  }

  document.querySelectorAll("[data-src]").forEach(function (b) {
    b.onclick = function () {
      fs = b.dataset.src; page = 1;
      document.querySelectorAll("[data-src]").forEach(function (x) {
        x.classList.toggle("on", x === b);
      });
      render();
    };
  });
  document.querySelectorAll("[data-sub]").forEach(function (b) {
    b.onclick = function () {
      fu = b.dataset.sub; page = 1;
      document.querySelectorAll("[data-sub]").forEach(function (x) {
        x.classList.toggle("on", x === b);
      });
      render();
    };
  });
  var kwBox = document.getElementById("kw");
  if (kwBox) {
    kwBox.oninput = function (e) {
      kw = e.target.value.trim().toLowerCase();
      page = 1; render();
    };
  }

  loadTax().then(render);
})();
