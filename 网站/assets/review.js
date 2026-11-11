/* 错题讲解
   每天做完两组后，把当天的错题发给模型，逐题讲「为什么错、该怎么做」。
   按天存到 daily_review，历史可回看。 */
(function () {
  var MODEL = "deepseek-v4.1-flash";
  var LF = String.fromCharCode(10);
  var cloud = null;
  var att = [];
  var byId = {};
  var today = "";
  var cache = {};          // date -> {payload, n_wrong, summary}

  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function todayStr() {
    var d = new Date();
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
  }
  function esc(t) {
    return String(t == null ? "" : t)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }
  function mmdd(d) { return d.slice(5).replace("-", "/"); }

  /* ---------- 收集当天的错题（要带她选了什么） ---------- */
  function collectWrong(date) {
    var out = [];
    att.forEach(function (a) {
      if (!a || a.at !== date || a.ok || a.mode !== "pad") return;
      var v = byId[a.item_id];
      if (!v) return;
      var opts = v.options || [];
      var pick = a.pick === undefined || a.pick === null || a.pick === "" ? null : parseInt(a.pick, 10);
      out.push({
        item_id: a.item_id,
        subject: v.subject,
        stem: String(v.stem || v["题目"] || "").slice(0, 200),
        options: opts.slice(0, 6),
        answer: v.answer,
        picked: isNaN(pick) ? null : pick,
        explain: String(v.explain || "").slice(0, 200),
        kps: (v.kps || []).slice(0, 2)
      });
    });
    return out;
  }

  /* ---------- prompt ---------- */
  function askPrompt(items) {
    var L = [];
    L.push("你是五年级老师。家长晚上会看你写的这段，用来讲给孩子听。");
    L.push("下面是她今天做错的 " + items.length + " 道题，每道都附了她选的答案。");
    L.push("");
    items.forEach(function (it, i) {
      L.push("【" + (i + 1) + "】" + it.subject + "｜" + (it.kps[0] || "") + "｜id=" + it.item_id);
      L.push("题干：" + it.stem);
      if (it.options.length) {
        L.push("选项：" + it.options.map(function (o, j) {
          return "ABCDEF".charAt(j) + ". " + o;
        }).join("　"));
        L.push("正确答案：" + "ABCDEF".charAt(it.answer) +
          (it.picked === null ? "　她没作答" : "　她选了：" + "ABCDEF".charAt(it.picked)));
      } else {
        L.push("正确答案：" + it.answer + "　她答：" + (it.picked === null ? "—" : it.picked));
      }
      if (it.explain) L.push("题库解析（可参考，别照抄）：" + it.explain);
      L.push("");
    });
    L.push("要求：");
    L.push("1. 每道题说两件事：");
    L.push("   - why：为什么错。必须从「她选的那个选项」倒推，说清是哪一步想歪了。");
    L.push("     如果判断不出来，就写「这道更像是算错了，不是概念问题」，不要硬编。");
    L.push("   - how：该怎么做。给一个能照着走的步骤，不要「要认真审题」这种空话。");
    L.push("2. why 不超过 50 字，how 不超过 80 字。");
    L.push("3. 说人话，不要用「认知偏差」「知识迁移」这类术语。");
    L.push("4. 不要复述题干，不要重抄正确答案。");
    L.push("5. 如果多道题错在同一个知识点，在 summary 里点出来，并给一条练习建议（60 字内）。");
    L.push("");
    L.push("只输出 JSON，不要任何解释性文字，不要 markdown 代码块：");
    L.push('{"items":[{"item_id":"...","why":"...","how":"...","tag":"4-8字"}],"summary":"..."}');
    return L.join(LF);
  }

  /* ---------- 调模型 ---------- */
  async function callLLM(items) {
    var out = "";
    for await (const ch of cloud.llm.chat.completions.create({
      model: MODEL,
      messages: [
        { role: "system", content: "你是五年级老师，说话平实。只输出被要求的 JSON，不加任何解释。" },
        { role: "user", content: askPrompt(items) }
      ],
      stream: true
    })) {
      const d = ch.choices && ch.choices[0] && ch.choices[0].delta;
      if (d && d.content) out += d.content;
    }
    return out.trim();
  }

  function parseJSON(raw) {
    var s = String(raw || "").trim();
    s = s.replace(/^```(?:json)?/i, "").replace(/```$/, "").trim();
    var a = s.indexOf("{"), b = s.lastIndexOf("}");
    if (a >= 0 && b > a) s = s.slice(a, b + 1);
    return JSON.parse(s);
  }

  /* ---------- 渲染 ---------- */
  function card(it) {
    // 选择题才用 ABCD 编号；填空题直接显示填的值
    var opts = it.options || [];
    var hasOpts = opts.length > 0;
    var myPick = it.picked === null || it.picked === undefined || it.picked === ""
      ? "没作答"
      : (hasOpts
          ? ("ABCDEF".charAt(it.picked) + ". " + (opts[it.picked] || ""))
          : String(it.picked));
    var right = hasOpts
      ? ("ABCDEF".charAt(it.answer) + ". " + (opts[it.answer] || ""))
      : String(it.answer);
    return '<div class="card" style="margin-bottom:12px;padding:16px 18px">'
      + '<div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px">'
      + '<b style="font-size:0.933rem;color:#3E3037">'
      + esc(it.subject) + " · " + esc(it.tag || (it.kps || [])[0] || "") + '</b>'
      + '</div>'
      + '<div class="meta" style="margin-top:8px;color:#6B5B63">' + esc((it.stem || "").slice(0, 90)) + '</div>'
      + '<div class="meta" style="margin-top:6px">'
      + '你选了 <b style="color:#E24B4A">' + esc(myPick) + '</b>'
      + '　正确答案 <b style="color:#1D9E75">' + esc(right) + '</b></div>'
      + '<div style="margin-top:12px;font-size:0.867rem;color:#8B7B83">为什么错</div>'
      + '<div style="margin-top:3px;line-height:1.75;color:#3E3037">' + esc(it.why || "") + '</div>'
      + '<div style="margin-top:10px;font-size:0.867rem;color:#8B7B83">该怎么做</div>'
      + '<div style="margin-top:3px;line-height:1.75;color:#3E3037">' + esc(it.how || "") + '</div>'
      + '</div>';
  }

  function renderToday(date, rec, wrongRaw) {
    var box = document.getElementById("rv_today");
    if (!box) return;
    if (!rec) {
      box.innerHTML = '<div class="card empty">今天的讲解还没生成</div>';
      return;
    }
    // 模型偶尔会把同一道题写两遍，按 item_id 去重
    var seen = {};
    var items = ((rec.payload && rec.payload.items) || []).filter(function (it) {
      if (!it || !it.item_id) return false;
      if (seen[it.item_id]) return false;
      seen[it.item_id] = 1;
      return true;
    });
    var html = '<div class="sub" style="margin-top:20px">今天 · ' + mmdd(date)
      + '　' + rec.n_wrong + ' 道错题</div>';
    if (rec.summary) {
      html += '<div class="card" style="padding:14px 16px;margin-bottom:14px;'
        + 'background:linear-gradient(135deg,#FFF7F9,#FFF0F4);border:1px solid #FFE3EC">'
        + '<div style="font-size:0.9rem;line-height:1.75;color:#3E3037">' + esc(rec.summary) + '</div></div>';
    }
    // 老数据里可能没存 picked / answer / options，先补齐再判断题型
    var pickOf = {};
    att.forEach(function (a) { if (a && a.item_id) pickOf[a.item_id] = a.pick; });
    items.forEach(function (it) {
      // 1) 先补选项和答案（判断题型要用）
      if (it.options === undefined || it.options === null) {
        var v0 = byId[it.item_id];
        it.options = (v0 && v0.options) || [];
      }
      if (it.answer === undefined || it.answer === null) {
        var v1 = byId[it.item_id];
        if (v1) { it.answer = v1.answer; it.stem = it.stem || v1.stem; }
      }
      // 2) 再补她选了什么：选择题转成索引，填空题保留原始值（8.4 不能变成 8）
      if (it.picked === undefined || it.picked === null) {
        var pv = pickOf[it.item_id];
        if (pv === undefined || pv === null || pv === "") {
          it.picked = null;
        } else if ((it.options || []).length > 0) {
          var pi = parseInt(pv, 10);
          it.picked = isNaN(pi) ? null : pi;
        } else {
          it.picked = pv;   // 填空题：原样保留，别 parse
        }
      }
    });
    html += items.map(card).join("");
    box.innerHTML = html;
  }

  function renderHistory(rows, skipDate) {
    var box = document.getElementById("rv_history");
    var title = document.getElementById("rv_hist_title");
    if (!box) return;
    var list = rows.filter(function (r) { return r.review_date !== skipDate; });
    if (!list.length) {
      if (title) title.style.display = "none";
      box.innerHTML = "";
      return;
    }
    if (title) title.style.display = "";
    box.innerHTML = list.map(function (r) {
      var items = (r.payload && r.payload.items) || [];
      return '<details style="margin-bottom:10px">'
        + '<summary style="cursor:pointer;padding:12px 14px;background:#fff;border:1px solid #F4E7EC;'
        + 'border-radius:14px;font-size:0.9rem;color:#3E3037">'
        + mmdd(r.review_date) + '　' + r.n_wrong + ' 道错题'
        + (r.summary ? ' · ' + esc(r.summary.slice(0, 18)) + (r.summary.length > 18 ? "…" : "") : "")
        + '</summary>'
        + '<div style="padding:14px 0 0">' + items.map(card).join("") + '</div>'
        + '</details>';
    }).join("");
  }

  /* ---------- 主流程 ---------- */
  async function boot() {
    today = todayStr();
    var sub = document.getElementById("rv_sub");

    try {
      cloud = WorkBuddyCloud.createWorkBuddyCloud({
        endpoint: DB.cloud.endpoint, publishableKey: DB.cloud.key
      });
    } catch (e) { cloud = null; }

    if (!cloud) {
      if (sub) sub.textContent = "连不上云端，稍后再试";
      return;
    }

    // 题库：三科 tax + 大纲 + 变式，用来补题干和选项
    var rows = [], pp = [];
    try { var r1 = await cloud.database.from("drill_submissions").select("*"); if (!r1.error) rows = r1.data || []; } catch (e) {}
    try { var r2 = await cloud.database.from("paper_records").select("*"); if (!r2.error) pp = r2.data || []; } catch (e) {}
    att = Engine.toAttempts(rows, pp);

    var _fs = ["tax-math.json", "tax-cn.json", "tax-en.json"];
    var _rs = await Promise.all(_fs.map(function (f) {
      return fetch("assets/" + f + location.search).then(function (x) { return x.ok ? x.json() : []; }).catch(function () { return []; });
    }));
    var _all = (window.DB && window.DB.outline || []).concat(window.DB && window.DB.variants || []).concat([].concat.apply([], _rs));
    _all.forEach(function (v) { if (v && v.id) byId[v.id] = v; });

    // 已有的讲解
    var recs = [];
    try { var r3 = await cloud.database.from("daily_review").select("*"); if (!r3.error) recs = r3.data || []; } catch (e) {}
    recs.forEach(function (r) { cache[r.review_date] = r; });

    var todayRec = cache[today] || null;
    var wrong = collectWrong(today);
    var doneN = Object.keys(att.filter(function (a) {
      return a.at === today && a.mode === "pad" && a.group;
    }).reduce(function (o, a) { o[a.group] = 1; return o; }, {})).length;

    if (sub) {
      sub.textContent = "今天做了 " + (att.filter(function (a) { return a.at === today && a.mode === "pad"; }).length)
        + " 题，错 " + wrong.length + " 道";
    }

    // 有缓存且错题数没变，直接用
    if (todayRec && todayRec.n_wrong === wrong.length) {
      renderToday(today, todayRec, wrong);
      renderHistory(recs.sort(function (a, b) { return a.review_date < b.review_date ? 1 : -1; }), today);
      return;
    }

    // 一组都没做完，不生成
    if (doneN < 1) {
      var box = document.getElementById("rv_today");
      if (box) box.innerHTML = '<div class="card empty">今天还没开始做题，做完一组之后这里会有讲解。</div>';
      renderHistory(recs.sort(function (a, b) { return a.review_date < b.review_date ? 1 : -1; }), today);
      return;
    }

    if (!wrong.length) {
      var b2 = document.getElementById("rv_today");
      if (b2) b2.innerHTML = '<div class="card empty">今天两组全对，没有需要讲解的题。</div>';
      renderHistory(recs.sort(function (a, b) { return a.review_date < b.review_date ? 1 : -1; }), today);
      return;
    }

    // 生成
    var b3 = document.getElementById("rv_today");
    if (b3) b3.innerHTML = '<div class="card empty">正在生成讲解，大概十几秒…</div>';

    try {
      var raw = await callLLM(wrong.slice(0, 12));
      var data = parseJSON(raw);
      // 把题面信息合进 payload：历史回看时题库可能已经变了，
      // 只靠 item_id 反查会取不到「她选了什么」
      var _byId = {};
      wrong.forEach(function (w) { _byId[w.item_id] = w; });
      (data.items || []).forEach(function (it) {
        var w = _byId[it.item_id];
        if (!w) return;
        it.stem = w.stem; it.options = w.options;
        it.answer = w.answer; it.picked = w.picked;
      });
      var rec = {
        review_date: today,
        payload: data,
        n_wrong: wrong.length,
        summary: data.summary || "",
        model: MODEL
      };
      cache[today] = rec;
      renderToday(today, rec, wrong);
      try {
        if (todayRec) {
          await cloud.database.from("daily_review").update(rec).eq("review_date", today);
        } else {
          await cloud.database.from("daily_review").insert(rec);
        }
      } catch (e) {}
      recs.push(rec);
    } catch (e) {
      // 兜底：显示错题原文
      var b4 = document.getElementById("rv_today");
      if (b4) {
        var raw2 = '<div class="sub" style="margin-top:20px">今天 · ' + mmdd(today)
          + '　' + wrong.length + ' 道错题</div>'
          + '<div class="card" style="padding:12px 14px;margin-bottom:14px">'
          + '<div class="meta">讲解生成失败，下面是错题原文</div></div>'
          + wrong.map(function (it) {
            return card({
              subject: it.subject, stem: it.stem, options: it.options,
              answer: it.answer, picked: it.picked, kps: it.kps,
              why: it.explain || "（题库没有解析）", how: ""
            });
          }).join("");
        b4.innerHTML = raw2;
      }
    }

    renderHistory(recs.sort(function (a, b) { return a.review_date < b.review_date ? 1 : -1; }), today);
  }

  boot();
})();
