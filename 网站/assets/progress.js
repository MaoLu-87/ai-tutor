/* 记录页：从云端三张表合并出逐题作答流水，按日期分组显示。 */
(function () {
  var ALL = [], page = 1, PER = 40, fs = "全部", fo = "全部";
  var SUBNAME = { "数": "数学", "语": "语文", "英": "英语" };

  function esc(t) {
    return String(t == null ? "" : t).replace(/&/g, "&amp;").replace(/</g, "&lt;");
  }

  function kpOf(id) {
    var pool = [].concat(DB.variants || [], DB.errors || [], DB.outline || []);
    for (var i = 0; i < pool.length; i++) {
      if (pool[i].id === id) return (pool[i].kps || [])[0] || "";
    }
    return "";
  }

  function subOf(id) {
    if (/^Q-[MCE]-/.test(id)) return id.split("-")[1];
    if (/^[MCE]/.test(id)) return id[0];
    return "";
  }

  function render() {
    var list = ALL.filter(function (a) {
      if (fs !== "全部" && subOf(a.item_id) !== fs) return false;
      if (fo !== "全部" && (fo === "对") !== !!a.ok) return false;
      return true;
    });

    var pages = Math.max(1, Math.ceil(list.length / PER));
    if (page > pages) page = pages;
    var part = list.slice((page - 1) * PER, page * PER);

    // 按日期分组
    var groups = {}, order = [];
    part.forEach(function (a) {
      if (!groups[a.at]) { groups[a.at] = []; order.push(a.at); }
      groups[a.at].push(a);
    });

    var html = order.map(function (d) {
      var rows = groups[d].map(function (a) {
        var flag = a.ok
          ? '<span class="tag ok" style="flex:none">对</span>'
          : '<span class="tag warn" style="flex:none">错</span>';
        var mode = a.mode === "paper" ? "纸笔" : (a.sec ? "刷题 " + a.sec + " 秒" : "刷题");
        return '<div style="display:flex;gap:10px;align-items:baseline;padding:7px 0;'
          + 'border-bottom:1px solid #F8EFF2">' + flag
          + '<div style="flex:1;min-width:0"><b style="font-size:13px">' + esc(a.item_id) + '</b>'
          + '<span class="meta">　' + esc(kpOf(a.item_id) || "—") + '</span>'
          + '<div class="meta" style="margin-top:2px">' + esc(a.context || "") + ' · ' + mode + '</div></div></div>';
      }).join("");
      var d2 = parseInt(d.slice(5, 7), 10) + " 月 " + parseInt(d.slice(8, 10), 10) + " 日";
      return '<div style="margin-bottom:16px"><div class="meta" style="margin:0 0 6px;font-weight:500">'
        + d2 + '　<span style="opacity:.7">' + groups[d].length + ' 题</span></div>' + rows + '</div>';
    }).join("");

    document.getElementById("plist").innerHTML = html
      || '<div class="card empty">没有符合条件的记录</div>';

    var stat = document.getElementById("p_stat");
    var okN = list.filter(function (a) { return a.ok; }).length;
    stat.textContent = "共 " + list.length + " 条 · 对 " + okN + " 条"
      + (list.length ? "（" + Math.round(okN / list.length * 100) + "%）" : "");

    var pg = "";
    if (pages > 1) {
      pg += '<button class="pg" data-p="' + (page - 1) + '"' + (page <= 1 ? " disabled" : "") + ">‹</button>";
      var a2 = Math.max(1, page - 2), b2 = Math.min(pages, a2 + 4);
      a2 = Math.max(1, b2 - 4);
      for (var i = a2; i <= b2; i++) {
        pg += '<button class="pg' + (i === page ? " on" : "") + '" data-p="' + i + '">' + i + "</button>";
      }
      pg += '<button class="pg" data-p="' + (page + 1) + '"' + (page >= pages ? " disabled" : "") + ">›</button>";
    }
    document.getElementById("ppager").innerHTML = pg;
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

  async function boot() {
    var cloud = null;
    try {
      cloud = WorkBuddyCloud.createWorkBuddyCloud({
        endpoint: DB.cloud.endpoint, publishableKey: DB.cloud.key
      });
    } catch (e) {}
    if (!cloud) {
      document.getElementById("p_stat").textContent = "云端连不上，稍后刷新";
      return;
    }

    var rows = [], pp = [];
    try { var r = await cloud.database.from("drill_submissions").select("*"); if (!r.error) rows = r.data || []; } catch (e) {}
    try { var q = await cloud.database.from("paper_records").select("*"); if (!q.error) pp = q.data || []; } catch (e) {}

    ALL = Engine.toAttempts(rows, pp).sort(function (a, b) {
      return a.at < b.at ? 1 : a.at > b.at ? -1 : 0;
    });

    document.querySelectorAll("[data-fsub]").forEach(function (b) {
      b.onclick = function () {
        fs = b.dataset.fsub; page = 1;
        document.querySelectorAll("[data-fsub]").forEach(function (x) { x.classList.toggle("on", x === b); });
        render();
      };
    });
    document.querySelectorAll("[data-fok]").forEach(function (b) {
      b.onclick = function () {
        fo = b.dataset.fok; page = 1;
        document.querySelectorAll("[data-fok]").forEach(function (x) { x.classList.toggle("on", x === b); });
        render();
      };
    });

    render();
  }

  boot();
})();
