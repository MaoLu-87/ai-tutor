#!/usr/bin/env python
# 生成 iPad 刷题页（单文件、离线可用、结果生成短码）
#
# 用法:
#   python make_drill.py                      全部题，标题用今天日期
#   python make_drill.py --ids M5A-005,M5A-006 只出指定题
#   python make_drill.py --title "11月9日 · 数学回炉"
import argparse, datetime, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
BANK = os.path.join(HERE, "drill-bank.json")
OUT = os.path.join(HERE, "drill.html")

TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover,user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<title>__TITLE__</title>
<style>
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent;-webkit-font-smoothing:antialiased}
html,body{margin:0;padding:0;height:100%}
body{font-family:-apple-system,"PingFang SC","HarmonyOS Sans","Helvetica Neue",sans-serif;
  background:#FFF9F5;color:#3E3037;display:flex;align-items:center;justify-content:center;
  padding:16px;padding-bottom:calc(16px + env(safe-area-inset-bottom));}
.wrap{width:100%;max-width:720px}
.dots{display:flex;gap:6px;justify-content:center;margin-bottom:18px}
.dot{width:24px;height:5px;border-radius:3px;background:#F6E7EC}
.dot.ok{background:#54C9B3}.dot.no{background:#FF7FA3}.dot.now{background:#E85E86}
.card{background:#fff;border-radius:24px;padding:26px 24px 22px;box-shadow:0 10px 30px rgba(232,94,134,.10)}
.tag{font-size:12.5px;color:#E85E86;background:#FFE7EE;display:inline-block;
  padding:4px 11px;border-radius:999px;margin-bottom:14px}
.q{font-size:21px;line-height:1.62;font-weight:500;margin-bottom:22px;letter-spacing:-.2px}
.opt{display:block;width:100%;text-align:left;font-size:18px;line-height:1.5;padding:15px 17px;
  margin-bottom:10px;border:1.5px solid #F1E6EA;background:#fff;border-radius:18px;color:#3E3037;font-family:inherit}
.opt:active{background:#FFF6F6}
.opt.ok{border-color:#54C9B3;background:#E1F6F1}
.opt.no{border-color:#FF7FA3;background:#FFE9E4}
.opt .k{display:inline-flex;align-items:center;justify-content:center;width:24px;height:24px;
  border-radius:50%;background:#FBF2F5;color:#9A8790;font-size:12px;margin-right:10px;vertical-align:-2px}
.opt.ok .k{background:#54C9B3;color:#fff}
.opt.no .k{background:#FF7FA3;color:#fff}
input.num{width:100%;font-size:30px;padding:14px 16px;border:1.5px solid #F1E6EA;border-radius:18px;
  font-family:inherit;text-align:center;letter-spacing:1px;background:#fff;color:#3E3037}
input.num:focus{outline:none;border-color:#FF7FA3}
.btn{display:block;width:100%;font-size:18px;padding:15px;border-radius:999px;border:none;
  background:linear-gradient(135deg,#FF8FAE,#FF6E96);color:#fff;font-family:inherit;margin-top:14px;
  box-shadow:0 8px 20px rgba(255,110,150,.26)}
.btn.ghost{background:#F8EFF2;color:#8B7B83;box-shadow:none}
.btn:disabled{opacity:.45}
.fb{margin-top:16px;padding:13px 15px;border-radius:16px;font-size:15px;line-height:1.6;display:none}
.fb.ok{background:#E1F6F1;color:#2E9C87;display:block}
.fb.no{background:#FFE9E4;color:#C9406A;display:block}
.fb b{font-weight:600}
.hintline{font-size:14px;color:#9A8790;margin-top:14px;line-height:1.7}
.center{text-align:center}
.big{font-size:60px;font-weight:600;line-height:1.1;margin:6px 0;color:#E85E86;letter-spacing:-2px}
.code{font-family:ui-monospace,Menlo,monospace;font-size:14px;background:#FFF9F5;border-radius:14px;
  padding:14px;word-break:break-all;line-height:1.6;margin-top:14px;user-select:all;-webkit-user-select:all}
.small{font-size:13px;color:#9A8790;line-height:1.6}
.pace{font-size:12.5px;color:#9A8790;line-height:1.65;margin-top:8px;padding:8px 12px;
  background:#FFF6F9;border-radius:12px;display:inline-block;text-align:left}
.pace b{color:#E85E86;font-weight:600}
.timer{font-size:13px;color:#9A8790;text-align:center;margin-top:14px}
.back{display:inline-block;font-size:14px;color:#B9ACB2;margin-bottom:12px}
.back:active{color:#3E3037}
a.btn.ghost{display:block;text-align:center;text-decoration:none;margin-top:10px;line-height:1.2}
h1{font-size:25px;margin:0 0 8px;text-align:center;letter-spacing:-.4px}
.sync{font-size:13px;text-align:center;margin-top:12px;color:#9A8790}
.sync.ok{color:#2E9C87}
.sync.no{color:#C9406A}
.audio{display:flex;align-items:center;gap:12px;background:#FFF3F6;border:1.5px solid #FFE0E9;
  border-radius:18px;padding:14px 16px;margin-bottom:18px}
.play{border:none;background:linear-gradient(135deg,#FF8FAE,#FF6E96);color:#fff;font-family:inherit;
  font-size:16px;padding:11px 20px;border-radius:999px;box-shadow:0 6px 16px rgba(255,110,150,.28)}
.play:active{transform:scale(.97)}
.play[disabled]{opacity:.5}
.audio .cnt{font-size:12.5px;color:#9A8790}
</style></style>
</head>
<body>
<div class="wrap">
  <div class="dots" id="dots"></div>
  <div class="card" id="card"></div>
</div>
<script src="assets/cloud-sdk.js"></script>
__EXTRA_JS__
<script>
let DATA = __DATA__;
let cloud = null;
try {
  if (window.WorkBuddyCloud) {
    cloud = WorkBuddyCloud.createWorkBuddyCloud({
      endpoint: "https://your-app.workbuddy.host",
      publishableKey: "wbpk_YOUR_APP_ID_YOUR_KEY"
    });
  }
} catch (e) { cloud = null; }
let idx = 0, answers = [], t0 = 0, retried = false, picked = null;
let DONE_KEY = "done:" + DATA.date + "|" + DATA.title;

const $ = id => document.getElementById(id);
const fmt = s => Math.floor(s/60) + "'" + String(Math.round(s%60)).padStart(2,"0") + '"';

function start(){
  t0 = Date.now();
  render();
}

function dots(){
  $("dots").innerHTML = DATA.items.map((it,i)=>{
    let c = "dot";
    if (i < answers.length) c += answers[i].ok ? " ok" : " no";
    else if (i === idx) c += " now";
    return `<div class="${c}"></div>`;
  }).join("");
}

function render(){
  dots();
  const it = DATA.items[idx];
  let html = `<div class="tag">第 ${idx+1} 题 / 共 ${DATA.items.length} 题 · ${it.kp}</div>
    <div class="q">${it.q}</div>`;

  const pick = (it.type === "choice" || it.type === "listening");
  if (it.type === "listening"){
    html += `<div class="audio"><button class="play" id="play">▶ 播放录音</button>
      <span class="cnt" id="cnt">可以重听</span><audio id="au" preload="auto"></audio></div>`;
  }
  if (pick){
    html += it.options.map((o,i)=>
      `<button class="opt" data-i="${i}"><span class="k">${"ABCD"[i]}</span>${o}</button>`).join("");
  } else {
    html += `<input class="num" id="num" inputmode="decimal" autocomplete="off" placeholder="填答案">
             <button class="btn" id="sub">确定</button>`;
  }
  html += `<div class="fb" id="fb"></div>`;
  $("card").innerHTML = html;

  if (it.type === "listening"){
    const au = $("au"), btn = $("play"), cnt = $("cnt");
    au.src = it.audio + location.search;
    let times = 0;
    btn.onclick = ()=>{
      au.currentTime = 0;
      au.play().then(()=>{
        times++;
        btn.textContent = "↻ 再听一遍";
        cnt.textContent = "已听 " + times + " 遍";
      }).catch(()=>{ cnt.textContent = "音频加载失败"; });
    };
    au.onerror = ()=>{ cnt.textContent = "音频加载失败，请联网后刷新"; };
  }
  if (pick){
    $("card").querySelectorAll(".opt").forEach(b=>{
      b.onclick = ()=> choose(parseInt(b.dataset.i));
    });
  } else {
    const n = $("num");
    n.focus();
    $("sub").onclick = ()=> choose(n.value.trim());
    n.onkeydown = e => { if (e.key === "Enter") choose(n.value.trim()); };
  }
}

function check(it, val){
  if (it.type === "choice" || it.type === "listening") return parseInt(val) === it.answer;
  const v = parseFloat(String(val).replace(/[^\d.\-]/g,""));
  return Number.isFinite(v) && Math.abs(v - it.answer) < 1e-6;
}

function choose(val){
  const it = DATA.items[idx];
  const ok = check(it, val);

  if (it.type === "choice" || it.type === "listening"){
    const btns = $("card").querySelectorAll(".opt");
    btns.forEach(b=> b.disabled = true);
    btns[val].classList.add(ok ? "ok" : "no");
    if (!ok) btns[it.answer].classList.add("ok");
  } else {
    $("sub").disabled = true;
    $("num").disabled = true;
  }

  const fb = $("fb");
  if (ok){
    const sec = (Date.now()-t0)/1000;
    answers.push({id: it.id, ok: true, sec: Math.round(sec), pick: val});
    fb.className = "fb ok";
    fb.innerHTML = `<b>对了</b>　${it.kp}`;
    setTimeout(()=>{ idx++; next(); }, 850);
  } else if (!retried && it.type === "number"){
    retried = true;
    fb.className = "fb no";
    fb.innerHTML = `<b>再想想</b>　${it.hint || "先别急着算，把题目再读一遍，圈出关键数字和问的是什么。"}`;
    setTimeout(()=>{
      $("sub").disabled = false;
      $("num").disabled = false;
      $("num").select();
      fb.className = "fb"; fb.innerHTML = "";
    }, 1400);
  } else {
    const sec = (Date.now()-t0)/1000;
    answers.push({id: it.id, ok: false, sec: Math.round(sec), pick: val});
    fb.className = "fb no";
    fb.innerHTML = `<b>正确答案：${it.show}</b><br>${it.explain || it.hint}`;
    setTimeout(()=>{ idx++; next(); }, 2200);
  }
}

function next(){
  retried = false;
  if (idx < DATA.items.length){ render(); t0 = Date.now(); }
  else finish();
}

function finish(){
  const okN = answers.filter(a=>a.ok).length;
  const total = answers.reduce((s,a)=>s+a.sec,0);
  const d = new Date();
  const ymd = d.getFullYear() + String(d.getMonth()+1).padStart(2,"0") + String(d.getDate()).padStart(2,"0");
  const clean = v => String(v == null ? "" : v).replace(/[,|#]/g, " ").slice(0, 20);
  const body = answers.map(a=>`${a.id}=${a.ok?1:0}@${a.sec}${clean(a.pick) ? "#" + clean(a.pick) : ""}`).join(",");
  const code = `D${ymd}|${body}|${total}`;

  const wrong = answers.filter(a=>!a.ok).map(a=>a.id).join(" ");
  const target = (DATA.minutes || 15) * 60;
  const acc = okN / DATA.items.length;
  const nWrong = DATA.items.length - okN;
  let tip;
  if (total < 60) tip = "";
  else if (total > target * 1.3) tip = `比目标慢了 <b>${fmt(total-target)}</b>，下一组会少给你几道`;
  else if (total < target * 0.7) {
    tip = acc >= 0.85
      ? `比目标快了 <b>${fmt(target-total)}</b>，下一组会多给你几道`
      : `很快，但错了 <b>${nWrong}</b> 道——不是题不够，是没读透；下一组题量不变，做完记得回头检查`;
  }
  else tip = "节奏刚好落在目标上，继续保持";
  $("dots").innerHTML = "";
  $("card").innerHTML = `
    <div class="center">
      <div class="tag">完成</div>
      <div class="big">${okN} / ${DATA.items.length}</div>
      <div class="small">用时 ${fmt(total)}${wrong ? "　错题：" + wrong : "　全对"}</div>
      ${tip ? `<div class="pace">${tip}</div>` : ""}
    </div>
    <div class="sync" id="sync">正在上传…</div>
    <div class="code" id="code">${code}</div>
    <button class="btn" id="copy">复制结果码</button>
    ${(() => {
      const m = String(DATA.title || "").match(/第\s*(\d)\s*组/);
      const g = m ? parseInt(m[1], 10) : 0;
      return g === 1 ? `<a class="btn" href="drill.html?d=${DATA.date}&g=2">继续第 2 组</a>` : "";
    })()}
    <button class="btn ghost" id="again">再来一遍</button>
    <a class="btn ghost" href="index.html">回到首页</a>
    <div class="hintline center">这串码会自动上传；万一失败，长按复制发给家长。</div>`;
  $("copy").onclick = async ()=>{
    try{ await navigator.clipboard.writeText(code); $("copy").textContent = "已复制"; }
    catch(e){ const r = document.createRange(); r.selectNode($("code"));
      getSelection().removeAllRanges(); getSelection().addRange(r); $("copy").textContent = "已选中，请长按复制"; }
  };
  try{ localStorage.setItem(DONE_KEY, JSON.stringify({ok:okN, n:DATA.items.length, sec:Math.round(total)}));
       sessionStorage.removeItem("redo|" + DONE_KEY); }catch(e){}
  $("again").onclick = ()=>{
    try{ localStorage.removeItem(DONE_KEY); sessionStorage.setItem("redo|" + DONE_KEY, "1"); }catch(e){}
    location.hash = "#q"; location.reload();
  };
  upload(code, okN, total);
}

function loadDone(){
  try{ return JSON.parse(localStorage.getItem(DONE_KEY) || "null"); }catch(e){ return null; }
}

function showDone(d){
  $("dots").innerHTML = "";
  $("card").innerHTML = `
    <div class="center">
      <div class="tag">这组已经做完了</div>
      <div class="big">${d.ok} / ${d.n}</div>
      <div class="small">用时 ${fmt(d.sec)}</div>
      <div class="pace">成绩已经上传，家长那边能看到。<br>刷新不会丢，也不会重复计分。</div>
    </div>
    <button class="btn ghost" id="redo">再练一遍</button>
    <a class="btn ghost" href="index.html">回到首页</a>
    <div class="hintline center">想换一组？回首页点另一组。</div>`;
  $("redo").onclick = ()=>{
    try{ localStorage.removeItem(DONE_KEY); sessionStorage.setItem("redo|" + DONE_KEY, "1"); }catch(e){}
    location.hash = "#q"; location.reload();
  };
}

async function upload(code, okN, sec){
  const box = $("sync");
  if (!cloud){ box.textContent = "云端未就绪，请把这串发给家长"; box.className = "sync no"; return; }
  try {
    const { error } = await cloud.database.from("drill_submissions").insert({
      drill_date: DATA.date,
      drill_title: DATA.title,
      answers: code,
      score: okN,
      total: DATA.items.length,
      duration_sec: Math.round(sec)
    });
    if (error) throw error;
    box.textContent = "已自动上传";
    box.className = "sync ok";
  } catch (e) {
    box.textContent = "上传失败，请把这串发给家长";
    box.className = "sync no";
  }
}

function intro(){
  $("dots").innerHTML = "";
  $("card").innerHTML = `
    <a class="back" href="index.html">‹ 首页</a>
    <h1>${DATA.title}</h1>
    <div class="small center" style="margin-bottom:6px">共 ${DATA.items.length} 题${DATA.minutes ? "　限时 " + DATA.minutes + " 分钟" : ""}</div>
    <div class="hintline">做完会自动上传，不用管。<br>答错了先给你一句提示，再试一次；还错才看答案。</div>
    <button class="btn" id="go">开始</button>`;
  $("go").onclick = start;
}

function run(){
  const _redone = sessionStorage.getItem("redo|" + DONE_KEY) === "1";
  const _done = _redone ? null : (loadDone() || DATA.preDone || null);
  if (_done && _done.n === DATA.items.length) showDone(_done);
  else if (location.hash.indexOf('#q') === 0) start();
  else intro();
}

/* 没有预置题目时，现场算：读云端记录 → 评分 → 节奏 → 今天的题 */
async function loadDynamic(){
  const p = new URLSearchParams(location.search);
  const day = p.get("d") || Engine.todayStr();
  const gno = Math.max(1, Math.min(2, parseInt(p.get("g") || "1", 10)));
  $("dots").innerHTML = "";
  $("card").innerHTML = '<div class="center"><div class="tag">正在准备题目</div>' +
    '<div class="small" id="ld">读取云端记录…</div></div>';

  let rows = [], pp = [];
  if (cloud) {
    try {
      const r = await cloud.database.from("drill_submissions").select("*");
      if (!r.error) rows = r.data || [];
      else document.getElementById("ld").textContent = "云端读取失败，按基础规则出题";
      try {
        const q = await cloud.database.from("paper_records").select("*");
        if (!q.error) pp = q.data || [];
      } catch (e) {}
    } catch (e) { }
  }
  try {
    let tax = [];
    for (const f of ["tax-math.json", "tax-cn.json", "tax-en.json"]) {
      try {
        const tRes = await fetch("assets/" + f + location.search);
        if (tRes.ok) tax = tax.concat(await tRes.json());
      } catch (e) {}
    }
    const attempts = Engine.toAttempts(rows, pp);
    const kpState = Engine.scoreKps(attempts);
    const pace = Engine.paceOf(attempts);
    const due = Engine.dueOf(attempts);
    const od = Object.keys(due.byId).filter(function (id) {
      const x = due.byId[id];
      return x.due && x.due <= day && x.status !== "已巩固";
    });
    const byId = {};
    (window.DB.variants || []).forEach(v => byId[v.id] = v);
    (window.DB.outline || []).forEach(v => byId[v.id] = v);
    (tax || []).forEach(v => byId[v.id] = v);

    // 专项补练：?focus=知识点名，只考这一个点
    const focusName = p.get("focus");
    let picked = [];
    if (focusName) {
      const all = [].concat(window.DB.outline || [], tax || []);
      const r = Engine.planFocus(focusName, kpState, all, 6);
      picked = r.items;
      DATA.title = "补练 · " + focusName;
      DATA.minutes = 10;
    } else {
      const plan = Engine.planDay(day, gno, kpState, pace, Engine.recentOf(attempts, 7), od, tax);
      const grp = plan.groups[gno - 1] || plan.groups[0];
      picked = grp.ids.map(id => byId[id]).filter(Boolean);
      DATA.title = parseInt(day.slice(5, 7), 10) + "月" + parseInt(day.slice(8, 10), 10) + "日 · 第 " + gno + " 组";
      DATA.minutes = plan.minutes || 15;
    }

    DATA.items = picked.map(v => ({
      id: v.id,
      kp: (v.kps || [])[0] || "",
      type: v.type,
      q: v.stem,
      options: v.options || [],
      answer: v.answer,
      hint: v.hint || "",
      explain: v.explain || "",
      show: (v.type === "choice" || v.type === "listening")
        ? "ABCD"[v.answer] + ". " + (v.options || [])[v.answer]
        : String(v.answer),
      audio: v.type === "listening" ? "assets/audio/" + v.id + ".mp3" : ""
    }));
    DATA.date = day;
    DATA.preDone = null;
    DONE_KEY = "done:" + DATA.date + "|" + DATA.title;
  } catch (e) {
    $("card").innerHTML = '<div class="center"><div class="tag">出题失败</div>' +
      '<div class="small">' + (e && e.message ? e.message : e) + '</div>' +
      '<a class="btn ghost" href="index.html">回到首页</a></div>';
    return;
  }
  run();
}

if (DATA.items && DATA.items.length) run(); else loadDynamic();
</script>
</body>
</html>"""


def build(items, title, out_name="drill.html", minutes=0, pre_done=None, extra_js=""):
    for it in items:
        if it.get("show"):
            pass
        elif it["type"] == "choice":
            it["show"] = "ABCD"[it["answer"]] + ". " + it["options"][it["answer"]]
        else:
            it["show"] = str(it["answer"])
    fields = ("id", "kp", "type", "q", "options", "answer", "hint", "explain", "show", "audio")
    data = {"title": title, "date": datetime.date.today().isoformat(), "minutes": minutes,
            "preDone": pre_done,
            "items": [{k: it[k] for k in fields if k in it} for it in items]}
    for it in data["items"]:
        if it.get("type") == "listening" and not it.get("audio"):
            it["audio"] = "assets/audio/%s.mp3" % it["id"]
    html = (TEMPLATE.replace("__TITLE__", title)
                    .replace("__EXTRA_JS__", extra_js)
                    .replace("__DATA__", json.dumps(data, ensure_ascii=False)))
    local = os.path.join(HERE, out_name)
    with open(local, "w", encoding="utf-8") as f:
        f.write(html)
    # 发布目录只放这一个文件：答案库不进公网
    pub = os.path.join(HERE, "app")
    a_out = out_name
    os.makedirs(pub, exist_ok=True)

    with open(os.path.join(pub, a_out), "w", encoding="utf-8") as f:
        f.write(html)
    return local


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", default="")
    ap.add_argument("--title", default="")
    ap.add_argument("--n", type=int, default=0, help="只抽 n 道，按知识点均匀取")
    ap.add_argument("--minutes", type=int, default=0, help="建议用时，显示在开始页")
    ap.add_argument("--done", default="", help="构建时已知已完成：答对/总题数/用时秒，如 5/9/221")
    ap.add_argument("--dynamic", action="store_true", help="输出动态版：题目在浏览器里现算，不用预生成")
    ap.add_argument("--out", default="drill.html", help="输出到 publish/ 下的文件名")
    ap.add_argument("--due", action="store_true", help="只抽与『今天该复测』的错题同源的变式")
    a = ap.parse_args()

    bank = json.load(open(BANK, encoding="utf-8"))["题目"]
    items = bank
    if a.ids:
        want = [x.strip() for x in a.ids.split(",") if x.strip()]
        items = [b for b in bank if b["id"] in want]
        items.sort(key=lambda b: want.index(b["id"]))

    if a.due:
        duef = os.path.join(os.path.dirname(HERE), "题库", "due.json")
        if os.path.exists(duef):
            d = json.load(open(duef, encoding="utf-8"))
            want = set(d.get("due", [])) | set(d.get("soon", []))
            picked = [b for b in items if b.get("派生自") in want]
            items = picked if picked else items
            print("按到期错题取题：", len(items), "道")

    if a.n and 0 < a.n < len(items):
        groups = {}
        for it in items:
            groups.setdefault(it.get("知识点", "其他").split("、")[0], []).append(it)
        picked, depth = [], 0
        while len(picked) < a.n:
            added = False
            for g in groups.values():
                if depth < len(g) and len(picked) < a.n:
                    picked.append(g[depth]); added = True
            if not added:
                break
            depth += 1
        items = picked

    # 转成前端字段名
    norm = []
    for it in items:
        norm.append({
            "id": it["id"], "kp": it["知识点"], "type": it["类型"],
            "q": it["题干"], "options": it.get("选项", []),
            "answer": it["答案"], "hint": it["提示"], "explain": it.get("解释", ""),
            "audio": ("assets/audio/%s.mp3" % it["id"]) if it.get("类型") == "listening" else "",
            "show": it.get("显示", ""),
        })

    title = a.title or (datetime.date.today().strftime("%m月%d日") + " · 每日练习")
    if a.dynamic:
        out = build([], "刷题", a.out, 0, None,
                    '<script src="assets/db.js"></script>\n<script src="assets/engine.js"></script>')
        print("动态版已生成:", out)
        return

    pre = None
    if a.done:
        parts = a.done.split("/")
        if len(parts) == 3:
            pre = {"ok": int(parts[0]), "n": int(parts[1]), "sec": int(parts[2])}
    out = build(norm, title, a.out, a.minutes, pre)
    print("生成:", out, "题数:", len(norm), "大小: %.0f KB" % (os.path.getsize(out) / 1024))


if __name__ == "__main__":
    main()
