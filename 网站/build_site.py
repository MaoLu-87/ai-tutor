#!/usr/bin/env python
"""生成「学生 · 私人 AI 家教」网站（纯静态，数据在构建时内嵌）。

读：题库/index.json、attempts.json、due.json、数学错题库/错题库.json
出：网站/site/{index,subject,progress,drill}.html + assets/data.js?v=__DBVER__ + assets/style.css?v=__DBVER__

用法：python 网站/build_site.py
"""
import datetime
import json
import os
import re
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
QB = os.path.join(ROOT, "题库")
OUT = os.path.join(ROOT, "刷题", "app")
SHARE_CODE = "UCNVMYGOEA"          # 站点访问码；换了要同步改这里
Q = ("?sharecode=" + SHARE_CODE) if SHARE_CODE else ""

SUBJECTS = [("数", "数学", "#5B8DEF"), ("语", "语文", "#FF7FA3"), ("英", "英语", "#54C9B3")]
MILESTONES = [1, 7, 21]


CSS = """html{font-size:93.75%;-webkit-text-size-adjust:100%}
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent;-webkit-font-smoothing:antialiased}
html,body{margin:0;padding:0;overflow-x:hidden}
body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","HarmonyOS Sans","Microsoft YaHei",sans-serif;
  background:#FBEEE9;color:#3E3037;line-height:1.6;font-size:1rem}
a{color:inherit;text-decoration:none}
.wrap{max-width:780px;margin:0 auto;padding:18px 18px 64px}
.nav{display:flex;align-items:center;gap:14px;padding:12px 18px;background:rgba(255,249,245,.92);
  backdrop-filter:blur(10px);border-bottom:1px solid #F6E7EC;position:sticky;top:0;z-index:9}
.nav .links{display:flex;flex-wrap:wrap;gap:13px;justify-content:flex-end;flex:1;min-width:0}
.nav a{font-size:0.9rem;color:#9A8790;white-space:nowrap}
.nav a.on{color:#E85E86;font-weight:600}
h1{font-size:1.733rem;font-weight:600;margin:18px 0 4px;letter-spacing:-.8px}
h2{font-size:1rem;font-weight:600;margin:24px 0 10px;display:flex;align-items:center;gap:7px}
h2:before{content:"";width:4px;height:14px;border-radius:3px;background:linear-gradient(180deg,#FFB1C6,#FF7FA3)}
.sub{color:#9A8790;font-size:0.867rem;margin-bottom:16px}
.card{display:block;background:#fff;border-radius:22px;padding:16px 18px;margin-bottom:12px;
  box-shadow:0 10px 28px rgba(180,90,110,.10)}
.card.is-done{background:#F6FBF9;box-shadow:inset 0 0 0 1.5px #C9ECDB,0 10px 28px rgba(180,90,110,.06)}
.card.is-done .n{color:#2E9C87}
.card.is-done .tag{background:#E1F6F1;color:#2E9C87}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.grid .card{margin:0;cursor:pointer;transition:.15s}
.grid .card:active{transform:scale(.985)}
.kpi-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px}
.kpi{padding:14px 14px 12px;text-align:center}
.kpi .big{font-size:2rem;font-weight:600;letter-spacing:-1.2px;line-height:1.15;color:#E85E86}
.dot{width:9px;height:9px;border-radius:50%;display:inline-block;margin-right:7px}
.big{font-size:2rem;font-weight:600;letter-spacing:-1px;line-height:1.2}
.tag{display:inline-block;font-size:0.767rem;padding:3px 9px;border-radius:999px;background:#F8EFF2;color:#8B7B83;white-space:nowrap}
.tag.warn{background:#FFE9E4;color:#D2604F}
.tag.ok{background:#E1F6F1;color:#2E9C87}
.row{display:flex;justify-content:space-between;align-items:baseline;gap:10px}
.bar{height:7px;background:#EFEDEE;border-radius:5px;overflow:hidden;margin-top:8px}
.bar i{display:block;height:100%;border-radius:5px;background:linear-gradient(90deg,#FFB1C6,#FF7FA3)}
.item{border-left:4px solid #F1E3E8;padding:12px 0 12px 14px;margin-bottom:6px}
.item.q{border-color:#5B8DEF}.item.c{border-color:#FF7FA3}.item.e{border-color:#54C9B3}
.stem{font-size:0.967rem;font-weight:500;margin-bottom:4px;line-height:1.55}
.meta{font-size:0.833rem;color:#9A8790;line-height:1.6}
.k{color:#B9ACB2}
details{margin-top:6px}
summary{cursor:pointer;font-size:0.867rem;color:#E85E86;list-style:none}
summary::-webkit-details-marker{display:none}
summary::before{content:"▸ ";font-size:0.733rem}
details[open] summary::before{content:"▾ "}
.detail{font-size:0.9rem;background:#FFF9F5;border-radius:14px;padding:11px 13px;margin-top:8px;line-height:1.75}
.empty{text-align:center;color:#B9ACB2;padding:36px 0;font-size:0.9rem}
.btn{display:block;text-align:center;padding:13px 18px;border-radius:999px;border:0;
  background:linear-gradient(135deg,#FF8FAE,#FF6E96);color:#fff;font-size:1rem;font-weight:500;
  box-shadow:0 8px 20px rgba(255,110,150,.26);font-family:inherit}
a.btn{text-decoration:none}
.btn.ghost{background:#F8EFF2;color:#8B7B83;box-shadow:none}
.tl{position:relative;padding-left:18px}
.tl::before{content:"";position:absolute;left:4px;top:6px;bottom:6px;width:2px;background:#F6E7EC}
.tl div{position:relative;margin-bottom:12px;font-size:0.9rem}
.tl div::before{content:"";position:absolute;left:-18px;top:8px;width:9px;height:9px;border-radius:50%;background:#fff;border:2px solid #F0DCE3}
/* 今日答题：数字打头，科目做彩色胶囊，一屏看完今天要做什么 */
.tc-card{text-align:center;padding:24px 18px 20px}
.tc-num{display:flex;align-items:baseline;justify-content:center}
.tc-num b{font-size:2.65rem;font-weight:700;letter-spacing:-2px;line-height:1;color:#3E3037}
.tc-num i{font-size:0.92rem;font-style:normal;color:#8B7B83;margin:0 3px 0 5px;padding-bottom:4px}
.tc-num em{font-size:1.05rem;font-style:normal;color:#E0CFD5;margin:0 8px}
.tc-subs{display:flex;justify-content:center;gap:7px;flex-wrap:wrap;margin-top:15px}
.tc-subs span{font-size:0.78rem;padding:4px 11px;border-radius:999px;font-weight:500}
/* 右上角固定角标：15 分钟，不随内容变化 */
.tc-card{position:relative}
.tc-badge{position:absolute;right:13px;top:13px;width:56px;height:56px;border-radius:50%;
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  background:linear-gradient(140deg,#FFEAF1,#FFD5E1);color:#E85E86;
  box-shadow:inset 0 0 0 1.5px rgba(255,255,255,.8),0 4px 12px rgba(232,94,134,.15)}
.tc-badge b{font-size:1.18rem;font-weight:700;line-height:1.05;letter-spacing:-.6px}
.tc-badge i{font-size:0.6rem;font-style:normal;opacity:.85;margin-top:1px}

.foot{text-align:center;color:#C0B2B8;font-size:0.8rem;margin-top:36px}

/* ---------- 小老师：每次打开首页从右边探出头说句话 ---------- */
.teach{position:fixed;left:auto;right:24px;bottom:26px;z-index:30;display:flex;
  flex-direction:row;align-items:flex-end;gap:14px;transform:translateX(240px);
  transition:transform .8s cubic-bezier(.34,1.28,.52,1);pointer-events:none}
.teach.in{transform:translateX(0)}
/* 大屏左边是导航栏，探头的起点挪到导航右侧 */
@media (min-width:900px){.teach{right:28px}}

.teach-fig svg{display:block;width:116px;height:139px}
@media (min-width:900px){.teach-fig svg{width:150px;height:180px}}
.teach-bubble:before,.teach-bubble:after{content:"";position:absolute;width:0;height:0;
  border-style:solid;border-color:transparent}
.teach-bubble:before{right:-11px;bottom:14px;border-width:10px 0 10px 12px;border-left-color:#FFE7EE}
.teach-bubble:after{right:-8px;bottom:16px;border-width:8px 0 8px 9px;border-left-color:#fff}
/* 眨眼：周期缩到 4 秒、闭眼停留拉长到 240ms，否则一闪而过看不见。
   SVG 里 transform 要用 fill-box 才可靠地绕自身中心缩放。 */
.teach-fig .eye-l,.teach-fig .eye-r{
  transform-box:fill-box;transform-origin:center;
  animation:blink 4s ease-in-out infinite}
.teach-fig .eye-r{animation-delay:.09s}
@keyframes blink{0%,86%,100%{transform:scaleY(1)}89%,95%{transform:scaleY(.06)}}
@media (prefers-reduced-motion: reduce){.teach-fig .eye-l,.teach-fig .eye-r{animation:none}}
.teach-fig{position:relative;pointer-events:auto;cursor:pointer;filter:drop-shadow(0 10px 20px rgba(200,110,140,.18));
  -webkit-tap-highlight-color:transparent}
.teach-fig:active{transform:scale(.96)}
/* 关闭按钮：贴在小老师头顶右侧，纯白实底，压在内容上也看得清 */
.teach-x{position:absolute;right:-7px;top:-7px;width:25px;height:25px;padding:0;
  display:flex;align-items:center;justify-content:center;
  border-radius:50%;border:1.5px solid #F0D5DE;background:#fff;
  color:#A8939C;font-size:15px;line-height:1;font-family:inherit;cursor:pointer;
  box-shadow:0 2px 10px rgba(180,90,110,.24);pointer-events:auto;
  transition:transform .15s,background .15s,color .15s,border-color .15s}
.teach-x:hover{background:#FFF0F4;color:#E85E86;border-color:#FFD3E0}
.teach-x:active{transform:scale(.88)}
.teach-bubble{position:relative;max-width:232px;margin-bottom:34px;background:#fff;
  border:1.5px solid #FFE7EE;border-radius:18px;padding:12px 15px;font-size:0.9rem;line-height:1.62;
  color:#3E3037;box-shadow:0 8px 22px rgba(200,110,140,.16);
  opacity:0;transform:translateY(10px);transition:opacity .45s .3s,transform .45s .3s}
.teach.in .teach-bubble{opacity:1;transform:translateY(0)}
@media (max-width:420px){
  .teach-bubble{max-width:186px;font-size:0.85rem}
}
.cal{display:grid;grid-template-columns:repeat(7,1fr);gap:6px}
.cal div{height:46px;display:flex;flex-direction:column;align-items:center;justify-content:center;
  border-radius:14px;font-size:0.9rem;line-height:1.05;background:#FBF5F7;color:#BFB0B6}
.cal .hd{color:#B9ACB2;font-size:0.767rem;height:auto;padding-bottom:4px;background:transparent}
.cal .perfect{background:#FFF3D8;color:#B87A0B;font-weight:600;box-shadow:inset 0 0 0 1.5px #FFC24B}
.cal .b95{background:#C9EFE6;color:#1D8873;font-weight:600}
.cal .b90{background:#E1F6F1;color:#2E9C87}
.cal .b80{background:#EAF6E0;color:#4F7A17}
.cal .b70{background:#FDF0DC;color:#B87A0B}
.cal .b0{background:#FFE9E4;color:#D2604F}
.cal .record{background:#F3ECEE;color:#8B7B83}
.cal .none{background:#FBF5F7;color:#C7B9BF}
.cal .fut{background:transparent;color:#E0D3D8}
.cal .td{box-shadow:inset 0 0 0 2px #FF7FA3}
.cal i{display:block;font-style:normal;font-size:0.6rem;line-height:1;margin-top:2px;opacity:.85}
.legend{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:12px}
.legend span{font-size:0.767rem;color:#9A8790;display:flex;align-items:center;gap:5px}
.legend b{width:12px;height:12px;border-radius:4px;display:inline-block}
.flowbox{background:#fff;border-radius:16px;padding:14px 18px;margin-top:6px;box-shadow:0 6px 18px rgba(232,94,134,.07)}
.flowbox > summary{cursor:pointer;list-style:none;font-size:0.9rem;font-weight:500;display:flex;align-items:center;color:#3E3037}
.flowbox > summary::-webkit-details-marker{display:none}
.flowbox > summary::before{content:"▸";font-size:0.733rem;color:#B9ACB2;margin-right:7px}
.flowbox[open] > summary::before{content:"▾"}
.flowbox > summary::after{content:"点开";margin-left:auto;font-size:0.733rem;color:#B9ACB2;font-weight:400}
.flowbox[open] > summary::after{content:"收起"}
.mini{display:block}
.mini summary{display:flex;align-items:center;list-style:none;cursor:pointer;font-size:0.833rem;color:#8B7B83}
.mini summary::-webkit-details-marker{display:none}
.mini summary::before{content:"▸";font-size:0.667rem;color:#B9ACB2;margin-right:6px}
.mini[open] summary::before{content:"▾"}
.mini summary::after{content:"点开";margin-left:auto;font-size:0.733rem;color:#B9ACB2}
.mini[open] summary::after{content:"收起"}
.tabs{display:flex;gap:8px;margin:8px 0 16px}
.tabs a{flex:1;text-align:center;padding:11px 6px;border-radius:16px;background:#fff;color:#8B7B83;
  font-size:0.933rem;box-shadow:0 6px 18px rgba(232,94,134,.07);white-space:nowrap}
.tabs a.on{background:#FFE7EE;color:#E85E86;font-weight:600}
.tabs a .dot{margin-right:6px}
.tabs a em{font-style:normal;font-size:0.733rem;margin-left:7px;opacity:.7}
.hero{background:linear-gradient(135deg,#FF9DB8 0%,#FF7FA3 52%,#FF9E7D 100%);border-radius:24px;
  padding:18px 20px;color:#fff;box-shadow:0 14px 32px rgba(255,127,163,.30);position:relative;overflow:hidden}
.hero:before{content:"";position:absolute;right:-30px;top:-40px;width:130px;height:130px;border-radius:50%;background:rgba(255,255,255,.13)}
.hero:after{content:"";position:absolute;right:34px;bottom:-46px;width:86px;height:86px;border-radius:50%;background:rgba(255,255,255,.09)}
.hero .row{position:relative}
.hero .num{font-size:3.067rem;font-weight:600;line-height:1;letter-spacing:-2px;color:#fff}
.hero .unit{font-size:0.867rem;opacity:.92;margin-left:6px}
.hero .pill{background:rgba(255,255,255,.22);border-radius:999px;padding:7px 13px;font-size:0.867rem;font-weight:500}
.hero .tip{font-size:0.8rem;opacity:.92;margin-top:10px;position:relative;line-height:1.75}
.hero .lab{font-size:0.767rem;opacity:.85}
.g2{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:14px}
.g2 .card{margin:0;padding:13px 14px}
.g2 .card b{font-size:0.933rem}
.g2 .n{font-size:1.467rem;font-weight:600;letter-spacing:-1px;color:#E85E86;line-height:1.2;margin-top:2px}
.greeting{font-size:0.833rem;color:#B08B96;margin-bottom:6px;letter-spacing:.3px}
.stars{font-size:1.467rem;letter-spacing:3px;color:#FFC24B}
.streak{position:relative;display:inline-block;text-align:center;padding:6px 0 0}
.streak .num{font-size:3.867rem;font-weight:600;line-height:.95;letter-spacing:-2.5px;font-variant-numeric:tabular-nums}
.s0 .num{color:#AEA9A4}
.s1 .num{color:#3E3037}
.s3 .num{color:#5B8DEF;text-shadow:0 0 16px rgba(91,141,239,.28)}
.s5 .num{color:#C9820F;text-shadow:0 0 20px rgba(255,194,75,.38);animation:breathe 2.6s ease-in-out infinite}
.s7 .num,.s10 .num{background:linear-gradient(100deg,#8A5200,#C9820F,#FFCF5C,#C9820F,#8A5200);
  background-size:220% auto;-webkit-background-clip:text;background-clip:text;
  -webkit-text-fill-color:transparent;color:#A86400;
  animation:shine 3.2s linear infinite;filter:drop-shadow(0 0 8px rgba(200,130,15,.45))}
.s10 .num{font-size:4.267rem;filter:drop-shadow(0 0 16px rgba(200,130,15,.55))}
.crown{display:block;margin:0 auto 0;width:46px;height:30px;animation:float 2.8s ease-in-out infinite}
.s10 .crown{width:58px;height:37px;margin-bottom:-2px}
.spark{position:absolute;width:5px;height:5px;border-radius:50%;background:#FFC24B;opacity:0;animation:pop 2.6s ease-in-out infinite}
.spark.a{left:8%;top:26%}.spark.b{right:6%;top:40%;animation-delay:.9s}.spark.c{left:24%;top:8%;animation-delay:1.7s}
@keyframes breathe{0%,100%{transform:scale(1)}50%{transform:scale(1.07)}}
@keyframes shine{0%{background-position:0% 50%}100%{background-position:220% 50%}}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}
@keyframes pop{0%,100%{opacity:0;transform:scale(.4)}45%{opacity:1;transform:scale(1)}70%{opacity:0;transform:scale(.6)}}
@media (prefers-reduced-motion: reduce){.streak .num,.crown,.spark{animation:none!important}}

/* 首页连打卡片：底色是粉色渐变，数字本身就是白的，
   所以档位只能靠「光晕强弱 + 装饰」区分，换颜色会糊在同色背景上 */
.hero .streak{position:relative;display:inline-flex;align-items:baseline;gap:2px;padding:0}
.hero .streak .num{color:#fff;transition:text-shadow .3s}
.hero .s0 .num{opacity:.5;text-shadow:none}
.hero .s1 .num{opacity:1;text-shadow:0 1px 3px rgba(180,60,90,.22);
  -webkit-text-stroke:.4px rgba(255,255,255,.35)}
.hero .s3 .num{opacity:1;
  text-shadow:0 2px 18px rgba(255,255,255,.75),0 0 38px rgba(255,214,228,.95),0 0 64px rgba(255,190,210,.55);
  -webkit-text-stroke:.9px rgba(255,255,255,.55)}
.hero .s3 .unit{text-shadow:0 0 12px rgba(255,255,255,.55)}
.hero .s5 .num{
  text-shadow:0 2px 22px rgba(255,255,255,.9),0 0 46px rgba(255,205,222,1),0 0 76px rgba(255,196,218,.6);
  -webkit-text-stroke:1.1px rgba(255,255,255,.68);
  animation:breathe 2.6s ease-in-out infinite}
.hero .s5 .unit{text-shadow:0 0 14px rgba(255,255,255,.65)}
.hero .s7 .num,.hero .s10 .num{
  text-shadow:0 2px 24px rgba(255,255,255,1),0 0 52px rgba(255,196,218,1),0 0 88px rgba(255,180,205,.7);
  -webkit-text-stroke:1.2px rgba(255,255,255,.78);
  animation:breathe 3s ease-in-out infinite}
.hero .s7 .unit,.hero .s10 .unit{text-shadow:0 0 16px rgba(255,255,255,.75)}
.hero .s10 .num{font-size:3.333rem}
.hero .crown{width:26px;height:17px;margin-right:3px;animation:float 2.8s ease-in-out infinite;flex:none;
  filter:drop-shadow(0 2px 6px rgba(200,80,120,.35))}
.hero .s10 .crown{width:32px;height:21px}
.hero .spark{position:absolute;width:4px;height:4px;border-radius:50%;background:#fff;
  box-shadow:0 0 8px rgba(255,255,255,.9);opacity:0;animation:pop 2.6s ease-in-out infinite}
.hero .spark.a{left:-7px;top:16%}
.hero .spark.b{right:-5px;top:46%;animation-delay:.9s}
.hero .spark.c{left:32%;top:-8%;animation-delay:1.7s}
@media(max-width:860px){.nav{padding:11px 20px 11px 14px}.nav .links{gap:10px}.nav a{font-size:0.853rem}.nav b{font-size:0.933rem}}
@media(max-width:640px){.grid{grid-template-columns:1fr}.kpi-grid{grid-template-columns:repeat(2,1fr)}h1{font-size:1.4rem}}
.lz{background:linear-gradient(135deg,#FFF7FA,#FFF0F4);border:1.5px solid #FFE1EA;border-radius:22px;
  padding:15px 16px;margin-bottom:14px;box-shadow:0 10px 28px rgba(180,90,110,.08)}
.lz .lh{display:flex;align-items:center;gap:8px;font-size:0.967rem;font-weight:600;color:#E85E86;margin-bottom:11px}
.lz .lh em{font-style:normal;font-size:0.8rem;font-weight:400;color:#B09AA3;margin-left:auto}
.lz .one{background:#fff;border-radius:16px;padding:12px 14px;margin-bottom:9px;box-shadow:0 4px 14px rgba(180,90,110,.06)}
.lz .one:last-child{margin-bottom:0}
.lz .q{font-size:0.933rem;color:#4A3B42;line-height:1.62;margin-bottom:9px}
.lz .bar2{display:flex;align-items:center;gap:10px}
.lz button{appearance:none;border:0;background:linear-gradient(135deg,#FF9EB8,#FF7FA3);color:#fff;
  font-size:0.9rem;font-weight:600;padding:8px 17px;border-radius:999px;font-family:inherit;cursor:pointer;
  box-shadow:0 6px 14px rgba(255,127,163,.28)}
.lz button:active{transform:scale(.97)}
.lz .cnt{font-size:0.8rem;color:#9A8790}
.lz details{margin-top:9px;border-top:1px dashed #F2E6EB;padding-top:7px}
.lz summary{font-size:0.833rem;color:#A08D96;cursor:pointer;list-style:none}
.lz summary::-webkit-details-marker{display:none}
.lz summary:before{content:"▸ ";color:#FFA9C2}
.lz details[open] summary:before{content:"▾ "}
.lz .script{margin-top:8px;font-size:0.9rem;color:#5C4B53;line-height:1.72;background:#FFF9FB;
  border-radius:11px;padding:9px 11px}
.lz .opts{margin-top:7px;font-size:0.867rem;color:#6B5A62;line-height:1.8}
.lz .opts b{color:#2E9C87;font-weight:600}

/* ---------- 大屏适配：iPad 全系 / 横屏手机 ----------
   字号全部是 rem，改 html 的百分比即可整站等比放大；
   宽度和卡片内边距单独给，免得字大了显得挤。 */
@media (min-width:641px){
  html{font-size:100%}
  .wrap{max-width:880px;padding:24px 26px 84px}
  .card{padding:20px 22px;margin-bottom:15px}
  .nav{padding:14px 24px}
  .kpi{padding:18px 16px 15px}
  h2{margin:28px 0 12px}
}
@media (min-width:900px){
  html{font-size:106.25%}
  /* 横屏 iPad 上顶栏太浪费纵向空间，导航挪到左边成竖列 */
  .nav{position:fixed;left:0;top:0;bottom:0;width:232px;
    display:flex;flex-direction:column;align-items:stretch;gap:0;
    padding:22px 14px 18px;overflow-y:auto;
    border-right:1px solid #F6E7EC;border-bottom:0;
    background:rgba(255,249,245,.97)}
  .nav > a{padding:2px 10px 16px}
  .nav .links{flex-direction:column;align-items:stretch;justify-content:flex-start;
    gap:2px;width:100%;flex:1;min-width:0}
  .nav .links a{width:100%;padding:11px 14px;border-radius:12px;
    font-size:1rem;text-align:left;white-space:normal}
  .nav .links a.on{background:#FFE7EE}
  .wrap{margin:0 0 0 232px;max-width:1064px;padding:26px 34px 96px}
  .grid{gap:17px}
  .kpi-grid{gap:14px}
  .card{padding:22px 25px;margin-bottom:17px}
  h2{margin:32px 0 14px}
  /* 知识树和练习记录都是「分组的短条目」，单列在平板上浪费一半宽度。
     知识树用 grid 而不是瀑布流：瀑布流会把「第 6 单元」排到「第 1 单元」旁边，
     看着像顺序乱了；grid 按行排，1/2、3/4 成对出现，顺序符合直觉。 */
  /* 知识树改单列：单元点数差得太多（有的 1 个点，有的 7 个），
     两列会把长短不一的卡片并排放，中间留一片空白。单列按顺序往下读更顺。 */
  #tree{display:block}
  #plist{display:grid;grid-template-columns:1fr 1fr;
    gap:16px 18px;align-items:start;grid-auto-flow:dense}
  /* 只有练习记录还是 grid，用 gap 代替 margin；
     知识树已改单列，这里不能再压 margin-bottom，否则卡片会贴在一起 */
  #plist > *{margin-bottom:0 !important}
  #tree > .empty, #plist > .empty{grid-column:1 / -1}
  /* 诊断和补题清单是整体提示，通栏 */
  #tree > details{grid-column:1 / -1}
}
@media (min-width:1200px){
  html{font-size:112.5%}
  .nav{width:252px;padding:26px 16px 20px}
  .wrap{margin-left:252px;max-width:1120px;padding:30px 40px 104px}
}
"""


def _load_json(path, key=None, default=None):
    """读 JSON，文件缺失或损坏时返回默认值。

    2026-11-09 起本地不再回流作答记录，attempts.json 已删。
    这里统一容错，免得少一个文件就让整站构建失败。
    """
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return d.get(key) if key else d
    except Exception:
        return default if default is not None else ([] if key else {})


def load_scores():
    f = os.path.join(ROOT, "知识库", "scores.json")
    if not os.path.exists(f):
        return None
    return json.load(open(f, encoding="utf-8"))


def load():
    idx = json.load(open(os.path.join(QB, "index.json"), encoding="utf-8"))["题目"]
    att = _load_json(os.path.join(QB, "attempts.json"), "记录", [])
    due = json.load(open(os.path.join(QB, "due.json"), encoding="utf-8"))
    return idx, att, due


def analyse(items, att):
    by_id = {i["id"]: i for i in items}
    by = {}
    for a in att:
        it = by_id.get(a["item_id"], {})
        # 变式练的是原题的知识点，作答要归到派生来源上
        key = it.get("from") if it.get("kind") == "variant" and it.get("from") else a["item_id"]
        by.setdefault(key, []).append(a)
    out = []
    today = datetime.date.today()
    for it in items:
        if it["kind"] != "error":
            out.append(dict(it, reviews=0, status="未练", due=None, late=0, last=None, last_note=""))
            continue
        recs = sorted(by.get(it["id"], []), key=lambda r: r["at"])
        start = datetime.date.fromisoformat(recs[0]["at"]) if recs else None
        reviews = max(0, len(recs) - 1)
        ok_streak = 0
        for r in reversed(recs[1:]):
            if r["ok"]:
                ok_streak += 1
            else:
                break
        if reviews >= 3 and ok_streak >= 3:
            status, due_d = "已巩固", None
        elif start:
            status = "复测中" if reviews else "待复测"
            due_d = start + datetime.timedelta(days=MILESTONES[min(reviews, 2)])
        else:
            status, due_d = "待复测", None
        out.append(dict(it, reviews=reviews, status=status,
                        due=due_d.isoformat() if due_d else None,
                        late=(today - due_d).days if due_d and due_d <= today else 0,
                        last=recs[-1]["at"] if recs else None,
                        last_note=recs[-1].get("note", "") if recs else ""))
    out.sort(key=lambda x: (x["due"] or "9999"))
    return out





BRAND = "AI私教"

LOGO = ('<svg viewBox="0 0 180 180" width="28" height="28" aria-hidden="true" '
        'xmlns="http://www.w3.org/2000/svg" style="flex:none;border-radius:9px;display:block">'
        '<defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#FFA9C2"/><stop offset=".55" stop-color="#FF7FA3"/>'
        '<stop offset="1" stop-color="#FF9E7D"/></linearGradient>'
        '<linearGradient id="ls" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#FFE39A"/><stop offset="1" stop-color="#FFC24B"/></linearGradient></defs>'
        '<rect width="180" height="180" rx="42" fill="url(#lg)"/>'
        '<circle cx="150" cy="24" r="34" fill="#fff" opacity=".10"/>'
        '<path d="M88 62 C74 52 54 50 38 56 L38 126 C54 120 74 122 88 132 Z" fill="#fff"/>'
        '<path d="M92 62 C106 52 126 50 142 56 L142 126 C126 120 106 122 92 132 Z" fill="#FFF0F4"/>'
        '<path d="M90 64 L90 130" stroke="#FF7FA3" stroke-width="3" opacity=".35" stroke-linecap="round"/>'
        '<path d="M138 22 L142 33 L153 37 L142 41 L138 52 L134 41 L123 37 L134 33 Z" fill="url(#ls)" '
        'stroke="#fff" stroke-width="2.5" stroke-linejoin="round"/>'
        '</svg>')


def nav(cur):
    drill = "drill.html"
    links = [("index.html", "总览"), ("tree.html", "知识树"),
             ("bank.html", "题目库"), ("review.html", "讲解"),
             ("exams.html", "考试"), ("checkin2.html", "打卡")]
    parts = "".join(
        '<a href="%s"%s>%s</a>' % (h, ' class="on"' if h == cur else "", t)
        for h, t in links)
    brand = ('<a href="index.html" style="display:flex;align-items:center;gap:9px;flex:none">'
             '%s<b style="font-size:1rem;letter-spacing:-.2px">%s</b></a>') % (LOGO, BRAND)
    return '<div class="nav">%s<div class="links">%s</div></div>' % (brand, parts)


# 首页的小老师。文案后面接大模型生成，现在先写死一句占位。
TEACHER_HTML = '''
<div class="teach" id="teach" aria-hidden="true">
  <div class="teach-bubble" id="teachBubble"></div>
  <div class="teach-fig" id="teachFig" title="点我收起">
    <button class="teach-x" id="teachClose" type="button" aria-label="关闭">&#215;</button>
    <svg viewBox="0 0 150 180" xmlns="http://www.w3.org/2000/svg">
      <ellipse cx="75" cy="177" rx="30" ry="5" fill="#E85E86" opacity=".09"/>
      <!-- 头发底 -->
      <ellipse cx="75" cy="90" rx="46" ry="44" fill="#5C4B53"/>
      <!-- 脸 -->
      <ellipse cx="75" cy="95" rx="38" ry="36" fill="#FFE3D4"/>
      <!-- 刘海：中分，露出额头 -->
      <path d="M37 84 Q40 50 60 47 Q55 60 58 73 Q46 75 37 84 Z" fill="#5C4B53"/>
      <path d="M113 84 Q110 50 90 47 Q95 60 92 73 Q104 75 113 84 Z" fill="#5C4B53"/>
      <!-- 小揪揪 -->
      <circle cx="31" cy="62" r="10" fill="#5C4B53"/>
      <circle cx="119" cy="62" r="10" fill="#5C4B53"/>
      <circle cx="31" cy="62" r="3.6" fill="#FF8FAE" opacity=".5"/>
      <circle cx="119" cy="62" r="3.6" fill="#FF8FAE" opacity=".5"/>
      <!-- 眼白 / 瞳孔 / 高光包成一组，眨的时候一起压扁 -->
      <g class="eye-l">
        <ellipse cx="61" cy="96" rx="8.5" ry="9.5" fill="#FFF"/>
        <circle cx="62" cy="97" r="5" fill="#3E3037"/>
        <circle cx="60" cy="94" r="1.9" fill="#FFF"/>
      </g>
      <g class="eye-r">
        <ellipse cx="89" cy="96" rx="8.5" ry="9.5" fill="#FFF"/>
        <circle cx="90" cy="97" r="5" fill="#3E3037"/>
        <circle cx="88" cy="94" r="1.9" fill="#FFF"/>
      </g>
      <!-- 圆框眼镜 -->
      <circle cx="61" cy="96" r="13" fill="none" stroke="#E85E86" stroke-width="2.4" opacity=".95"/>
      <circle cx="89" cy="96" r="13" fill="none" stroke="#E85E86" stroke-width="2.4" opacity=".95"/>
      <path d="M74 96 L76 96" stroke="#E85E86" stroke-width="2.4" opacity=".95" stroke-linecap="round"/>
      <path d="M48 95 L38 92" stroke="#E85E86" stroke-width="2.4" opacity=".95" stroke-linecap="round"/>
      <path d="M102 95 L112 92" stroke="#E85E86" stroke-width="2.4" opacity=".95" stroke-linecap="round"/>
      <!-- 腮红 -->
      <ellipse cx="46" cy="112" rx="8" ry="4.6" fill="#FFB8C8" opacity=".7"/>
      <ellipse cx="104" cy="112" rx="8" ry="4.6" fill="#FFB8C8" opacity=".7"/>
      <!-- 笑 -->
      <path d="M65 116 Q75 126 85 116" stroke="#C96A72" stroke-width="3" fill="none" stroke-linecap="round"/>
      <!-- 身子：圆肩 -->
      <path d="M44 134 Q75 148 106 134 Q114 156 116 180 L34 180 Q36 156 44 134 Z" fill="#FFC2D6" stroke="#F095B8" stroke-width="1.6"/>
      <path d="M44 134 Q75 148 106 134" stroke="#F5BDD2" stroke-width="2" fill="none"/>
      <!-- 领结 -->
      <path d="M75 140 l-10 -7 v14 z" fill="#FF7FA3"/>
      <path d="M75 140 l10 -7 v14 z" fill="#FF8FAE"/>
      <circle cx="75" cy="140" r="3.2" fill="#E85E86"/>
    </svg>
  </div>
</div>
<script>(function(){
  var t = document.getElementById("teach");
  if (!t) return;
  var b = document.getElementById("teachBubble");
  var stopped = false, timer = null, closed = false;
  var LF = String.fromCharCode(10);

  function pad(n){ return String(n).padStart(2, "0"); }
  function greetWord(){
    var h = new Date().getHours();
    if (h >= 5 && h < 11) return "早上好";
    if (h >= 11 && h < 14) return "中午好";
    if (h >= 14 && h < 19) return "下午好";
    return "晚上好";
  }
  function todayStr(){
    var d = new Date();
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
  }

  var NICK = "__NICK__";
  var MODEL = "deepseek-v4.1-flash";
  // 兜底：没有缓存、生成失败、离线时都显示这句
  var line = NICK + "，" + greetWord() + "！今天也一起加油～";

  // 一个字一个字往外蹦，遇到标点停一下
  function typeOut(){
    if (!b) return;
    if (timer) clearTimeout(timer);
    b.textContent = "";
    var i = 0;
    (function step(){
      if (stopped) return;
      if (i >= line.length) { scheduleHide(); return; }   // 说完了，从这一刻开始计时
      var ch = line.charAt(i);
      b.textContent = line.slice(0, ++i);
      var d = 45;
      if ("，、；".indexOf(ch) >= 0) d = 230;
      else if ("。！？～".indexOf(ch) >= 0) d = 420;
      timer = setTimeout(step, d);
    })();
  }

  // 说完之后留一分钟给孩子读完，再自己收起来
  var hideTimer = null;
  function scheduleHide(){
    if (hideTimer) clearTimeout(hideTimer);
    hideTimer = setTimeout(hide, 60000);
  }

  function show(){
    if (closed) return;          // 点过关闭就一直不出现，刷新页面才重置
    t.classList.add("in");
    setTimeout(typeOut, 850);
  }
  function hide(){
    stopped = true;
    if (timer) clearTimeout(timer);
    t.classList.remove("in");
  }
  function repaint(next){
    if (!next || next === line) return;
    line = next;
    if (t.classList.contains("in") && !stopped) typeOut();
  }

  /* -------- 近 7 天统计 -------- */
  function stats7(att, ck){
    var days = [];
    for (var i = 6; i >= 0; i--) {
      var d = new Date(); d.setDate(d.getDate() - i);
      days.push(d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()));
    }
    var cut = days[0], recentCut = days[4];

    var n = 0, ok = 0, seenDay = {}, byDay = {}, kpSet = {};
    var sub = {"数": [0, 0], "语": [0, 0], "英": [0, 0]};
    var subRecent = {"数": [0, 0], "语": [0, 0], "英": [0, 0]};
    var recent = [0, 0], earlier = [0, 0];
    var wrongKp = {};
    var secs = [], maxStreakWrong = 0;
    var kpOf = (window.DB && window.DB.kpOf) || {};
    var kpName = {};
    ((window.DB && window.DB.kps) || []).forEach(function(k){ kpName[k.id] = k.name; });

    var all = (att || []).filter(function(a){ return a && a.at && a.at >= cut; });
    // 只有屏幕作答才有「对/错」的含义；纸笔记录是错题清单，ok 恒为 false
    var rows = all.filter(function(a){ return a.mode === "pad"; });
    var paperCount = all.length - rows.length;
    rows.sort(function(a, b){ return a.at < b.at ? -1 : a.at > b.at ? 1 : 0; });

    // 知识点覆盖用全部记录，错题也算「见过」
    all.forEach(function(a){
      var kid = (kpOf[a.item_id] || [])[0] || "";
      if (kid) kpSet[kid] = 1;
    });

    var streak = 0;
    rows.forEach(function(a){
      n++; if (a.ok) ok++;
      seenDay[a.at] = 1;
      if (!byDay[a.at]) byDay[a.at] = [0, 0];
      byDay[a.at][0]++; if (a.ok) byDay[a.at][1]++;

      var kid = (kpOf[a.item_id] || [])[0] || "";
      var s2 = {"M": "数", "C": "语", "E": "英"}[kid.charAt(0)];
      if (s2) {
        sub[s2][0]++; if (a.ok) sub[s2][1]++;
        if (a.at >= recentCut) { subRecent[s2][0]++; if (a.ok) subRecent[s2][1]++; }
      }

      if (a.at >= recentCut) { recent[0]++; if (a.ok) recent[1]++; }
      else { earlier[0]++; if (a.ok) earlier[1]++; }

      if (!a.ok && kid) wrongKp[kid] = (wrongKp[kid] || 0) + 1;
      if (typeof a.sec === "number" && a.sec > 0) secs.push(a.sec);

      streak = a.ok ? 0 : streak + 1;
      if (streak > maxStreakWrong) maxStreakWrong = streak;
    });

    var avgSec = 0;
    if (secs.length) {
      var tot = 0;
      for (var i = 0; i < secs.length; i++) tot += secs[i];
      avgSec = Math.round(tot / secs.length);
    }

    var best = null, worst = null;
    Object.keys(byDay).forEach(function(d){
      var v = byDay[d], r = v[1] * 100 / v[0];
      if (!best || r > best.r) best = { d: d, r: Math.round(r) };
      if (!worst || r < worst.r) worst = { d: d, r: Math.round(r) };
    });

    var weakId = null, weakN = 0;
    Object.keys(wrongKp).forEach(function(k){
      if (wrongKp[k] > weakN) { weakN = wrongKp[k]; weakId = k; }
    });

    return {
      n: n, ok: ok,
      activeDays: Object.keys(seenDay).length,
      sub: sub, subRecent: subRecent,
      recent: recent, earlier: earlier,
      avgSec: avgSec,
      kpCount: Object.keys(kpSet).length,
      maxStreakWrong: maxStreakWrong,
      best: best, worst: worst,
      weakName: weakId ? (kpName[weakId] || null) : null,
      weakN: weakN,
      paperCount: paperCount,
      streak: (ck && ck.streak) || 0,
      checkedToday: !!(ck && ck.checkedToday)
    };
  }

  function buildData(st){
    var L = [];
    var acc = Math.round(st.ok * 100 / Math.max(1, st.n));
    var names = {"数": "数学", "语": "语文", "英": "英语"};
    var arr = ["数", "语", "英"].filter(function(k){ return st.sub[k][0] > 0; });

    L.push("近 7 天做了 " + st.n + " 道题，正确率 " + acc + "%，覆盖 " + st.kpCount + " 个知识点");
    L.push("其中 " + st.activeDays + " 天有练习，连续打卡 " + st.streak + " 天，"
      + (st.checkedToday ? "今天已经做过" : "今天还没开始"));

    if (arr.length) {
      L.push("各科：" + arr.map(function(k){
        return names[k] + " " + Math.round(st.sub[k][1] * 100 / st.sub[k][0])
          + "%（" + st.sub[k][0] + " 道）";
      }).join("、"));
    }

    if (st.earlier[0] >= 3 && st.recent[0] >= 3) {
      var e = Math.round(st.earlier[1] * 100 / st.earlier[0]);
      var r = Math.round(st.recent[1] * 100 / st.recent[0]);
      var diff = r - e;
      L.push("整体最近 3 天 " + r + "%，前 4 天 " + e + "%"
        + (Math.abs(diff) >= 5
            ? ("，" + (diff > 0 ? "上升 " : "下滑 ") + Math.abs(diff) + " 个百分点")
            : "，基本持平"));
    }

    var moved = [];
    arr.forEach(function(k){
      var a = st.sub[k], b = st.subRecent[k];
      if (a[0] >= 4 && b[0] >= 2) {
        var o = Math.round(a[1] * 100 / a[0]);
        var c = Math.round(b[1] * 100 / b[0]);
        if (Math.abs(c - o) >= 15) moved.push(names[k] + "从 " + o + "% 变成 " + c + "%");
      }
    });
    if (moved.length) L.push("变化明显的：" + moved.join("、"));

    if (st.avgSec) L.push("平均每题 " + st.avgSec + " 秒");
    if (st.maxStreakWrong >= 3) L.push("最长连错过 " + st.maxStreakWrong + " 道");
    if (st.best && st.worst && st.best.d !== st.worst.d) {
      L.push("最好的一天 " + st.best.d.slice(5).replace("-", "/") + "（" + st.best.r + "%），"
        + "最差的一天 " + st.worst.d.slice(5).replace("-", "/") + "（" + st.worst.r + "%）");
    }
    if (st.paperCount) {
      L.push("另有 " + st.paperCount + " 道纸笔错题在复习清单里");
    }
    if (st.weakName && st.weakN >= 2) {
      L.push("错得最多的是「" + st.weakName + "」，" + st.weakN + " 次");
    }

    return L.join(LF);
  }

  function askPrompt(dataText){
    return "你是五年级学生同学的班主任。她每天打开学习页面时，会看到你写的一段评语。" + LF
      + "根据下面最近 7 天的做题情况，写这段评语。" + LF
      + "要求：" + LF
      + "- 70 字以内，三句话" + LF
      + "- 第一句：整体状态，带一个具体数字；不要只夸某一科，要落到整体表现或最突出的地方" + LF
      + "- 第二句：指出一个真正的问题或最该保持的地方，配一条具体做法" + LF
      + "- 第三句：一句实在的鼓励" + LF
      + "- 像老师当面说话，不要「你真棒」「继续努力」这类空话" + LF
      + "- 不要写称呼或名字，直接从内容开始（名字由程序另加）" + LF
      + "- 如果做题量或正确率明显下滑，就直接说出来，但要给改法" + LF
      + "- 只输出这三句话本身，不要引号、不要分点、不要额外解释" + LF + LF
      + dataText;
  }

  /* -------- 调模型 -------- */
  async function callLLM(cloud, dataText){
    var out = "";
    for await (const chunk of cloud.llm.chat.completions.create({
      model: MODEL,
      messages: [
        { role: "system",
          content: "你是五年级学生的班主任，说话像当面聊天。只输出被要求的那段评语，不加引号，不分点，不解释。" },
        { role: "user", content: askPrompt(dataText) }
      ],
      stream: true
    })) {
      const dd = chunk.choices && chunk.choices[0] && chunk.choices[0].delta;
      if (dd && dd.content) out += dd.content;
    }
    return out.trim()
      .replace(/^[「『"']/, "").replace(/[」』"']$/, "")
      .split(LF).join(" ").trim();
  }

  /* -------- 取缓存，没有就生成并写库 -------- */
  async function boot(){
    var D = window.DB;
    var cloud;
    try {
      cloud = WorkBuddyCloud.createWorkBuddyCloud({
        endpoint: D.cloud.endpoint, publishableKey: D.cloud.key
      });
    } catch (e) { show(); return; }

    var today = todayStr();
    var rows = [];
    try {
      var r = await cloud.database.from("daily_brief").select("*");
      rows = (r && r.data) || [];
    } catch (e) {}

    var todayHit = null, latest = null;
    for (var i = 0; i < rows.length; i++) {
      var rw = rows[i];
      if (!rw || !rw.line) continue;
      if (rw.brief_date === today) todayHit = rw;
      if (!latest || rw.brief_date > latest.brief_date) latest = rw;
    }

    if (todayHit) {                 // 今天的评语已经生成过
      line = todayHit.line;
      show();
      return;
    }

    // 今天还没生成：先显示最近一次（通常是昨天），保证随时打开都有话说
    if (latest) line = latest.line;
    show();

    // 每天只生成一次，且只在「今天已打卡」之后生成。
    // 打卡前打开就显示上一次的评语，不浪费一次模型调用。
    var ck0 = window.__ck;
    if (!ck0 || !ck0.checkedToday) return;

    var st = stats7(window.__att || [], window.__ck);
    if (!st.n) return;

    try {
      var text = await callLLM(cloud, buildData(st));
      if (!text) return;
      var full = NICK + "，" + text;      // 名字固定由代码拼，不让模型自己起称呼
      repaint(full);
      await cloud.database.from("daily_brief").insert({
        brief_date: today, line: full, model: MODEL
      });
    } catch (e) { document.title = "ERR " + (e && (e.code || e.message)); }
  }

  // 要等两件事：db.js 加载完（window.DB），以及首页把作答记录和打卡状态算完。
  // 只等前者会拿到空数组，统计为 0 就直接跳过生成了。
  var tries = 0;
  (function waitDB(){
    if (window.DB && window.DB.cloud && Array.isArray(window.__att) && window.__ck) return boot();
    if (++tries > 80) return show();
    setTimeout(waitDB, 100);
  })();

  // 不再从页面加载时定死 18 秒，改成「说完话后 60 秒」（见 scheduleHide）
  var fig = document.getElementById("teachFig");
  if (fig) fig.onclick = hide;

  // 点 × 彻底关掉：本次会话不再出现，刷新首页才回来
  var x = document.getElementById("teachClose");
  if (x) x.onclick = function(e){
    if (e && e.stopPropagation) e.stopPropagation();
    closed = true;
    if (hideTimer) clearTimeout(hideTimer);
    hide();
  };
})();
</script>
'''


def page(title, cur, body):
    extra = TEACHER_HTML.replace("__NICK__", NICK) if cur == "index.html" else ""
    # db.js 内容会变（题库更新），URL 必须带版本号，否则浏览器一直用旧缓存
    ver = datetime.datetime.now().strftime("%Y%m%d%H%M")
    html = ('<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            '<meta name="apple-mobile-web-app-capable" content="yes">'
            '<title>%s</title>'
            '<link rel="stylesheet" href="assets/style.css?v=__DBVER__">'
            '<link rel="icon" href="assets/icon-180.png">'
            '<link rel="apple-touch-icon" href="assets/icon-180.png">'
            '<meta name="apple-mobile-web-app-title" content="%s">'
            '</head><body>%s' % (
                (title + " · " + BRAND) if title else BRAND,
                BRAND, nav(cur))
            + extra
            + ('<div class="wrap">%s<div class="foot">数据更新于 %s · 本地生成，不上传</div></div>'
               '</body></html>') % (body, datetime.date.today().isoformat()))
    return html.replace("__DBVER__", ver)


NICK = "学生" if os.environ.get("OPEN_SOURCE") else "同学"
FINAL = datetime.date(2027, 1, 15)


DYN_JS = """
<div class="meta" id="dyn_note" style="text-align:center;color:#C9BDC3;font-size:0.767rem;margin-top:12px"></div>
<script src="assets/cloud-sdk.js?v=__DBVER__"></script>
<script src="assets/db.js?v=__DBVER__"></script>
<script src="assets/engine.js?v=__DBVER__"></script>
<script>(function(){
  var D = window.DB || {};
  function pad(n){ return String(n).padStart(2, "0"); }
  function subName(s){ return {"数":"数学","语":"语文","英":"英语"}[s] || s; }
  var today = Engine.todayStr();

  function renderHero(ck){
    var el = document.getElementById("hero"); if (!el) return;
    // 星星规则只在这里讲一次，下面的「今日答题」不再重复
    var maxStar = ck.todayMax + 5;
    var tip = ck.checkedToday
      ? ("今天已经打卡 · 得了 " + ck.todayStar + " 颗")
      : ("今天做完最多 " + maxStar + " 颗：连续 " + ck.todayMax + " + 全对 5<br>"
         + "答对率低于 80% 打折，低于 60% 倒扣 1 颗");
    // 连打档位：和打卡页同一套分档（0/1/3/5/7/10），但配色走主题粉
    var _tier = ck.streak === 0 ? 0 : ck.streak < 3 ? 1 : ck.streak < 5 ? 3
      : ck.streak < 7 ? 5 : ck.streak < 10 ? 7 : 10;
    var _crown = _tier >= 10
      ? '<svg class="crown" viewBox="0 0 64 40" xmlns="http://www.w3.org/2000/svg">'
        + '<defs><linearGradient id="cgp" x1="0" y1="0" x2="1" y2="1">'
        + '<stop offset="0" stop-color="#FFB3C7"/><stop offset=".5" stop-color="#FFE6EE"/>'
        + '<stop offset="1" stop-color="#E85E86"/></linearGradient></defs>'
        + '<path d="M5 33 L9 9 L21 21 L32 4 L43 21 L55 9 L59 33 Z" fill="url(#cgp)"/>'
        + '<rect x="5" y="33" width="54" height="4" rx="2" fill="#E85E86"/></svg>'
      : "";
    var _sparks = _tier >= 7
      ? '<span class="spark a"></span><span class="spark b"></span><span class="spark c"></span>'
      : "";

    el.innerHTML = '<a class="hero" href="checkin2.html" style="display:block;margin:14px 0 16px">'
      + '<div class="row" style="align-items:center">'
      + '<div class="streak s' + _tier + '">' + _crown + _sparks
      + '<span class="num">' + ck.streak + '</span>'
      + '<span class="unit">天连续打卡</span></div>'
      + '<div class="pill">★ ' + ck.available + ' 颗'
      + (ck.withdrawn > 0 ? '（已兑 ' + ck.withdrawn + '）' : '') + '</div></div>'
      + '<div class="tip">' + tip + '</div></a>';
  }

  function renderToday(plan, ck, tax){
    var el = document.getElementById("today"); if (!el) return;
    var byId = {};
    (D.variants || []).forEach(function(v){ byId[v.id] = v; });
    (D.outline || []).forEach(function(v){ byId[v.id] = v; });
    (tax || []).forEach(function(v){ byId[v.id] = v; });

    var sub = {"数":0,"语":0,"英":0}, total = 0;
    plan.groups.forEach(function(g){
      g.ids.forEach(function(id){
        var v = byId[id];
        if (v && sub[v.subject] !== undefined) { sub[v.subject]++; total++; }
      });
    });

    var m = parseInt(today.slice(5, 7), 10), dd = parseInt(today.slice(8, 10), 10);

    // 打卡状态一律看云端记录。以前读 localStorage，换台设备就显示成「还没开始」。
    var doneSet = {};
    (window.__att || []).forEach(function (a) {
      if (a && a.at === today && a.mode === "pad" && a.group) doneSet[a.group] = 1;
    });
    var doneN = Object.keys(doneSet).length;

    // 两组都做完了，显示「今天实际做了多少」，而不是按现在的数据重新算出来的计划题数。
    // 否则会出现「今天做了 37 题，卡片写着 48 题」的矛盾。
    if (doneN >= 2) {
      var realSub = {"数": 0, "语": 0, "英": 0}, realTotal = 0;
      (window.__att || []).forEach(function (a) {
        if (!a || a.at !== today || a.mode !== "pad") return;
        var v = byId[a.item_id];
        if (v && realSub[v.subject] !== undefined) { realSub[v.subject]++; realTotal++; }
      });
      if (realTotal > 0) { total = realTotal; sub = realSub; }
    }

    var btn = doneN >= 2
      ? '<a href="review.html" style="display:inline-block;margin-top:14px;'
        + 'padding:9px 18px;border-radius:999px;text-decoration:none;font-size:0.867rem;'
        + 'background:#E85E86;color:#fff;box-shadow:0 4px 12px rgba(232,94,134,.28)">'
        + '今天两组都做完了，查看错题讲解 →</a>'
      : '<a class="btn" href="drill.html?g=' + (doneSet[1] ? 2 : 1) + '" style="margin-top:18px">'
        + (doneN ? "继续第 " + (doneSet[1] ? 2 : 1) + " 组" : "开始今日答题") + '</a>';

    var CLR = {"数": "#5B8DEF", "语": "#E85E86", "英": "#2E9C87"};
    var BGC = {"数": "rgba(91,141,239,.10)", "语": "rgba(232,94,134,.10)", "英": "rgba(46,156,135,.10)"};
    var subs = '<div class="tc-subs">' + ["数","语","英"].filter(function(k){ return sub[k]; })
      .map(function(k){
        return '<span style="color:' + CLR[k] + ';background:' + BGC[k] + '">'
             + subName(k) + ' ' + sub[k] + '</span>';
      }).join("") + '</div>';

    el.innerHTML = '<h2>今日答题</h2>'
      + '<div class="card tc-card">'
      + '<div class="tc-badge"><b>15</b><i>分钟</i></div>'
      + '<div class="tc-num"><b>2</b><i>组</i><em>·</em><b>' + total + '</b><i>题</i></div>'
      + subs
      + btn + '</div>'
      + renderWhy(plan, ck, byId);
  }

  /* 今天这 20 题是怎么来的：题量、科目、难度、逐题来源 */
  function renderWhy(plan, ck, byId) {
    var groups = plan.groups || [];
    var q = plan.quota || {};
    var judge = plan.judge || "起步";

    // 每组按科目数一遍：直接数题，不信 quota（quota 是两组合计）
    function subLine(ids) {
      var c = { "数": 0, "语": 0, "英": 0 };
      (ids || []).forEach(function (id) {
        var v = byId[id];
        if (v && c[v.subject] !== undefined) c[v.subject]++;
      });
      return "数 " + c["数"] + " · 语 " + c["语"] + " · 英 " + c["英"];
    }

    var note = {
      "快而错": "十几秒一道对五年级太快了——不是题太简单就是没读透",
      "太快": "又快又对，题数加满、难度往上走",
      "偏快": "比目标快，题数略加",
      "正好": "节奏合适，不动",
      "偏慢": "比目标慢，题数略减",
      "太慢": "会做但耗时太久，减题保时间",
      "又慢又错": "又慢又错，说明超纲了，减题并降难度",
      "起步": "还没有足够数据，先按标准配置"
    }[judge] || "";

    var g1 = groups[0] || { ids: [] };
    var g2 = groups[1] || { ids: [] };

    return '<details class="flowbox" style="margin:16px 0 8px">'
      + '<summary>今天两组是怎么分的（点开看）</summary>'
      + '<div style="padding:14px 4px 4px;line-height:1.8">'

      + '<div style="margin-bottom:18px">'
      + '<b style="color:#3E3037;font-size:0.933rem">第一组 · 先还账</b>'
      + '<div class="meta" style="margin-top:4px">'
      + (g1.ids || []).length + ' 道 · ' + subLine(g1.ids) + ' · 偏简单</div>'
      + '<div class="meta" style="margin-top:3px;opacity:.72">'
      + '到期的复测先做完，旧账不清会一直滚；分低的点出简单题，先做对再提速</div>'
      + '</div>'

      + '<div style="margin-bottom:18px">'
      + '<b style="color:#3E3037;font-size:0.933rem">第二组 · 再推进</b>'
      + '<div class="meta" style="margin-top:4px">'
      + (g2.ids || []).length + ' 道 · ' + subLine(g2.ids) + ' · 中档</div>'
      + '<div class="meta" style="margin-top:3px;opacity:.72">'
      + '没测过的点优先，往前摸新东西；难度提一档，太浅练不出东西</div>'
      + '</div>'

      + '<div class="meta" style="padding-top:14px;border-top:1px solid #F4E7EC">'
      + '最近几组 ' + (plan.perSec ? Math.round(plan.perSec) : "—") + ' 秒/题 · 正确率 '
      + (plan.acc ? Math.round(plan.acc * 100) : "—") + '%'
      + (note ? '　' + note : '') + '</div>'

      + '</div></details>';
  }

  (async function(){
    var rows = [], wd = [], pp = [], cloud = null;
    try { cloud = WorkBuddyCloud.createWorkBuddyCloud({endpoint: D.cloud.endpoint, publishableKey: D.cloud.key}); } catch(e) {}
    if (cloud) {
      try { var r = await cloud.database.from("drill_submissions").select("*"); if (!r.error) rows = r.data || []; } catch(e) {}
      try { var w = await cloud.database.from("star_withdrawals").select("*"); if (!w.error) wd = w.data || []; } catch(e) {}
      try { var q = await cloud.database.from("paper_records").select("*"); if (!q.error) pp = q.data || []; } catch(e) {}
    }
    var _fs = ["tax-math.json", "tax-cn.json", "tax-en.json"];
    var _rs = await Promise.all(_fs.map(function (f) {
      return fetch("assets/" + f + location.search).then(function (r) { return r.ok ? r.json() : []; }).catch(function () { return []; });
    }));
    var tax = [].concat.apply([], _rs);

    // 知识树的 1053 个点：评分和抽题都要用，全局存一份
    var _tf = ["tree-math.json", "tree-cn.json", "tree-en.json"];
    var _tr = await Promise.all(_tf.map(function (f) {
      return fetch("assets/" + f + location.search).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
    }));
    window.__tree = { math: _tr[0], cn: _tr[1], en: _tr[2] };

    var att = Engine.toAttempts(rows, pp);
    window.__att = att;          // 小老师要用同一份作答记录，避免再查一次库

    // 首页「看近 30 天节奏」：DOM 要等 renderToday 才出来，这里轮询等它
    (function () {
      var tries = 0;
      (function wait() {
        var box = document.getElementById("pace_30_home");
        if (!box) {
          if (++tries > 60) return;
          return setTimeout(wait, 100);
        }
        var byDay = {};
        att.forEach(function (a) {
          if (!a || !a.at || a.mode !== "pad") return;
          var v = byDay[a.at] || (byDay[a.at] = { n: 0, ok: 0, sec: 0, secN: 0 });
          v.n++; if (a.ok) v.ok++;
          if (a.sec) { v.sec += a.sec; v.secN++; }
        });
        var back = new Date(); back.setDate(back.getDate() - 29);
        var cutStr = back.getFullYear() + "-" + String(back.getMonth() + 1).padStart(2, "0")
                   + "-" + String(back.getDate()).padStart(2, "0");
        var days = Object.keys(byDay).filter(function (d) { return d >= cutStr; }).sort().reverse();
        if (!days.length) { box.innerHTML = '<div class="meta">近 30 天还没有记录</div>'; return; }
        box.innerHTML = days.map(function (d) {
          var v = byDay[d];
          var per = v.secN ? Math.round(v.sec / v.secN) : 0;
          return '<div class="row" style="padding:6px 0;border-bottom:1px solid #F8EFF2">'
            + '<span class="meta">' + d.slice(5).replace("-", "/") + '</span>'
            + '<span class="meta">' + v.n + ' 题' + (per ? ' · ' + per + ' 秒/题' : '') + '</span>'
            + '<b style="font-size:0.833rem;color:#3E3037">' + Math.round(v.ok * 100 / v.n) + '%</b></div>';
        }).join("");
      })();
    })();

    var kp = Engine.scoreKps(att);
    var pace = Engine.paceOf(att);
    var ck = Engine.checkin(att, wd);
    window.__ck = ck;
    renderHero(ck);
    var ld = document.getElementById("lead");
    if (ld) ld.textContent = ck.checkedToday ? "今天已经做完啦" : "今天也要加油";

    var dz = Engine.dueOf(att);
    var ed = document.getElementById("kpi_due");
    if (ed) { ed.textContent = dz.due; ed.style.color = dz.due ? "#E85E86" : "#3E3037"; }
    var el2 = document.getElementById("kpi_late");
    if (el2) el2.textContent = dz.late ? ("逾期 " + dz.late + " 道") : "";
    document.querySelectorAll("[data-avg]").forEach(function(el){
      var v = Engine.subAvg(kp, el.dataset.avg);
      el.textContent = "均分 " + Math.round(v);
    });
    // ---- KPI：全站唯一口径，从这里算 ----
    // 错题 = 自动提取的 errors ∪ 手动录入的 wrong（按 id 去重）
    var _all = {}, _allN = 0, _errSeen = {}, _errN = 0;
    function _addAll(x) {
      if (x && x.id && !_all[x.id]) { _all[x.id] = 1; _allN++; }
    }
    function _addErr(x) {
      if (x && x.id && !_errSeen[x.id]) { _errSeen[x.id] = 1; _errN++; }
    }
    (D.errors || []).forEach(function (x) { _addAll(x); _addErr(x); });
    (D.variants || []).forEach(_addAll);
    (D.outline || []).forEach(_addAll);
    (tax || []).forEach(_addAll);
    Object.keys(D.wrong || {}).forEach(function (k) {
      (D.wrong[k] || []).forEach(function (x) { _addAll(x); _addErr(x); });
    });

    var eErr = document.getElementById("kpi_err");
    if (eErr) eErr.textContent = _errN;
    var eQ = document.getElementById("kpi_q");
    if (eQ) eQ.textContent = _allN;
    var eVar = document.getElementById("kpi_var");
    if (eVar) eVar.textContent = (D.variants || []).length;
    try {
      var od = [];
      Object.keys(dz.byId).forEach(function (id) {
        var x = dz.byId[id];
        if (x.due && x.due <= today && x.status !== "已巩固") od.push(id);
      });
      renderToday(Engine.planDay(today, 1, kp, pace, Engine.recentOf(att, 7), od, tax, att), ck, tax);
    } catch (e) {
      var box = document.getElementById("today");
      if (box) box.innerHTML = '<div class="card"><b>题目没排出来</b><div class="meta">'
        + (e && e.message ? e.message : e) + '</div></div>';
    }

    /* 近 7 天 + 最近动态：本地 attempts.json 已删，改由云端记录现算 */
    (function () {
      // 题目自带知识点名字，直接查题目；查考点字典会漏掉大纲题
      var qById = {};
      (D.errors || []).concat(D.variants || [], D.outline || []).forEach(function (v) {
        qById[v.id] = v;
      });
      var kpOf = D.kpOf || {};

      var tb = document.getElementById("ck_trend");
      if (tb) {
        var days = [], cnt = {}, okn = {};
        for (var i = 6; i >= 0; i--) {
          var d = new Date(); d.setDate(d.getDate() - i);
          var ds = d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0")
                 + "-" + String(d.getDate()).padStart(2, "0");
          days.push({ ds: ds, label: (d.getMonth() + 1) + "/" + d.getDate() });
          cnt[ds] = 0; okn[ds] = 0;
        }
        (att || []).forEach(function (a) {
          if (cnt[a.at] === undefined) return;
          cnt[a.at]++; if (a.ok) okn[a.at]++;
        });
        var mx = 1;
        days.forEach(function (d) { if (cnt[d.ds] > mx) mx = cnt[d.ds]; });
        var bars = days.map(function (d) {
          var n = cnt[d.ds];
          return '<div style="flex:1;text-align:center">'
            + '<div style="height:64px;display:flex;align-items:flex-end;justify-content:center">'
            + '<div style="width:60%;height:' + (n ? Math.round(n * 100 / mx) : 3) + '%;background:'
            + (n ? "#5B8DEF" : "#F1E3E8") + ';border-radius:4px 4px 0 0;min-height:3px"></div></div>'
            + '<div class="meta" style="font-size:.733rem;margin-top:4px">' + d.label + '</div>'
            + '<div class="meta" style="font-size:.733rem">' + n + '</div></div>';
        }).join("");
        var tot = 0, totOk = 0;
        days.forEach(function (d) { tot += cnt[d.ds]; totOk += okn[d.ds]; });
        tb.innerHTML = '<div style="display:flex;gap:6px">' + bars + '</div>'
          + '<div class="meta" style="margin-top:8px">累计 ' + tot + ' 题，其中答对 ' + totOk + ' 题</div>';
      }

      var rb = document.getElementById("ck_recent");
      if (rb) {
        var latest = (att || []).slice().sort(function (a, b) {
          return a.at < b.at ? 1 : a.at > b.at ? -1 : 0;
        }).slice(0, 5);
        rb.innerHTML = latest.length ? latest.map(function (a) {
          var v = qById[a.item_id] || {};
          var kp = (v.kps && v.kps[0]) || "—";
          return '<div style="padding:8px 0;border-bottom:1px solid #F8EFF2">'
            + '<b>' + a.item_id + '</b>　'
            + (a.ok ? '<span class="tag ok">对</span>' : '<span class="tag warn">错</span>')
            + '　<span class="meta">' + kp + '</span></div>';
        }).join("") : '<div class="meta">暂无</div>';
      }
    })();
  })();
})();</script>
"""


def build_index(items, due):
    today = datetime.date.today()
    sc = load_scores()
    ck = load_checkin()

    errs = [i for i in items if i["kind"] == "error"]
    vars_ = [i for i in items if i["kind"] == "variant"]
    today_s = today.isoformat()
    due_n = len([e for e in errs if e["due"] and e["due"] <= today_s])
    late_n = len([e for e in errs if e["late"]])
    mastered = len([e for e in errs if e["status"] == "已巩固"])

    kps = sc["知识点"] if sc else []
    measured = [k for k in kps if k["score"] is not None]
    bands = {"熟练": 0, "掌握": 0, "待巩固": 0, "薄弱": 0, "未测": 0}
    for k in kps:
        bands[k["band"]] += 1

    left = (FINAL - today).days

    def kpi(num, label, color="#3E3037", sub=""):
        return ('<div class="card kpi"><div class="big" style="color:%s">%s</div>'
                '<div class="meta">%s</div>%s</div>') % (color, num, label,
                ('<div class="meta" style="color:#B9ACB2;font-size:0.8rem">%s</div>' % sub) if sub else "")

    # KPI 全部留给前端算：同一个指标只认 window.DB 一份数据，
    # 不在构建时再算一遍，避免跟题目库页口径分叉（曾出现 4412 vs 4383）。
    kpis = (kpi('<span id="kpi_err">—</span>', "在库错题") +
            kpi('<span id="kpi_due">—</span>', "待复测", "#E85E86",
                '<span id="kpi_late"></span>') +
            kpi('<span id="kpi_q">—</span>', "题库总数") +
            kpi('<span id="kpi_var">—</span>', "变式题"))

    # 三科卡
    cards = []
    for key, name, color in SUBJECTS:
        sub_err = [i for i in errs if i["subject"] == key]
        sub_var = [i for i in vars_ if i["subject"] == key]
        sub_due = [e for e in sub_err if e["due"] and e["due"] <= today_s]
        g = [k["score"] for k in measured if k["sub"] == key]
        avg = (sum(g) / len(g)) if g else None
        bar = 0 if avg is None else max(4, avg)
        cards.append(
            '<a class="card" href="bank.html#%s"><div class="row">'
            '<b><span class="dot" style="background:%s"></span>%s</b>'
            '<span class="meta" data-avg="%s">均分 %s</span></div>'
            '<div class="bar" style="margin-top:10px"><i style="width:%d%%;background:%s"></i></div>'
            '<div class="meta" style="margin-top:8px">错题 %d · 变式 %d · 待复测 %d</div></a>'
            % (key, color, name, key, ("%.0f" % avg) if avg is not None else "—",
               bar, color, len(sub_err), len(sub_var), len(sub_due)))

    # 今日两组：题目在浏览器里按当天数据现算，不用构建时预生成
    today_block = '<div id="today"></div>'

    # 最近考试
    ex = load_exams()
    ex_block = ""
    if ex:
        by_sub = {}
        for e in ex:
            by_sub.setdefault(e["subject"], []).append(e)
        lines = []
        for key, nm, color in SUBJECTS:
            rows = sorted(by_sub.get(key, []), key=lambda x: x["date"])
            if not rows:
                continue
            last = rows[-1]
            delta = ""
            if len(rows) > 1:
                d = last["score"] - rows[-2]["score"]
                if d > 0:
                    delta = ' <span class="tag ok">↑%d</span>' % d
                elif d < 0:
                    delta = ' <span class="tag warn">↓%d</span>' % abs(d)
            lines.append('<div class="row" style="padding:9px 0;border-bottom:1px solid #F8EFF2">'
                         '<span><span class="dot" style="background:%s"></span>%s</span>'
                         '<span><b>%d</b><span class="meta">/%d</span>%s</span></div>'
                         % (color, nm, last["score"], last["full"], delta))
        ex_block = ('<h2>最近考试</h2><div class="card">%s</div>'
                    '<div style="margin-top:-4px;margin-bottom:16px">'
                    '<a class="meta" href="exams.html">查看考试档案 →</a></div>') % "".join(lines)

    # 知识点五档分布
    total_kp = max(1, sum(bands.values()))
    cols = {"熟练": "#1f8a5f", "掌握": "#5B8DEF", "待巩固": "#C9820F", "薄弱": "#D2604F", "未测": "#E0D3D8"}
    segs = "".join('<i style="display:block;height:100%%;width:%.2f%%;background:%s"></i>'
                   % (bands[k] * 100.0 / total_kp, cols[k]) for k in ["熟练", "掌握", "待巩固", "薄弱", "未测"])
    legend = "　".join('<span class="dot" style="background:%s"></span>%s %d'
                       % (cols[k], k, bands[k]) for k in ["熟练", "掌握", "待巩固", "薄弱", "未测"])
    band_block = ('<h2>知识点分布</h2><div class="card">'
                  '<div style="display:flex;height:14px;border-radius:7px;overflow:hidden">%s</div>'
                  '<div class="meta" style="margin-top:10px;line-height:2">%s</div></div>') % (segs, legend)

    # 近 7 天做题趋势
    att = _load_json(os.path.join(ROOT, "题库", "attempts.json"), "记录", [])
    days = [(today - datetime.timedelta(days=i)) for i in range(6, -1, -1)]
    cnt = {dd: 0 for dd in days}
    okn = {dd: 0 for dd in days}
    for r in att:
        try:
            dd = datetime.date.fromisoformat(r["at"])
        except Exception:
            continue
        if dd in cnt:
            cnt[dd] += 1
            okn[dd] += 1 if r["ok"] else 0
    mx = max(1, max(cnt.values()))
    bars = "".join(
        '<div style="flex:1;text-align:center">'
        '<div style="height:64px;display:flex;align-items:flex-end;justify-content:center">'
        '<div style="width:60%%;height:%d%%;background:%s;border-radius:4px 4px 0 0;min-height:3px"></div></div>'
        '<div class="meta" style="font-size:0.733rem;margin-top:4px">%s</div>'
        '<div class="meta" style="font-size:0.733rem">%d</div></div>'
        % (int(cnt[dd] * 100 / mx) if cnt[dd] else 3,
           "#5B8DEF" if cnt[dd] else "#F1E3E8",
           dd.strftime("%m/%d")[1:] if False else "%d/%d" % (dd.month, dd.day),
           cnt[dd]) for dd in days)
    trend_block = ('<h2>近 7 天做题</h2><div class="card" id="ck_trend"><div style="display:flex;gap:6px">%s</div>'
                   '<div class="meta" style="margin-top:8px">累计 %d 题，其中答对 %d 题</div></div>'
                   % (bars, sum(cnt.values()), sum(okn.values())))

    # 最近动态
    by = {i["id"]: i for i in items}
    recent = sorted(att, key=lambda r: (r["at"], r["id"]), reverse=True)[:5]
    rows = []
    for r in recent:
        it = by.get(r["item_id"], {})
        rows.append('<div style="padding:8px 0;border-bottom:1px solid #F8EFF2">'
                    '<b>%s</b>　%s　<span class="meta">%s</span></div>'
                    % (r["item_id"],
                       '<span class="tag ok">对</span>' if r["ok"] else '<span class="tag warn">错</span>',
                       "、".join(it.get("kps", [])[:1]) or "—"))
    recent_block = '<h2>最近动态</h2><div class="card" id="ck_recent">%s</div>' % ("".join(rows) or '<div class="meta">暂无</div>')

    lead = "今天已经做完啦" if (ck and ck.get("今日已打卡")) else "今天也要加油"
    hh = datetime.datetime.now().hour
    greet = "早上好" if hh < 11 else ("中午好" if hh < 14 else ("下午好" if hh < 19 else "晚上好"))
    head = ('<div style="display:flex;justify-content:space-between;align-items:flex-end;margin:20px 0 2px">'
            '<div><div class="greeting" id="greet">%s</div>'
            '<h1 style="margin:0"><span id="who">%s</span>，<span id="lead">%s</span></h1>'
            '<div class="meta" style="margin-top:2px">五年级上册 · 人教版三科</div></div>'
            '<div style="text-align:right;padding-bottom:2px">'
            '<div style="font-size:2rem;font-weight:600;letter-spacing:-1.5px;color:#E85E86;line-height:1.1">%d</div>'
            '<div class="meta">天后期末</div></div></div>') % (greet, NICK, lead, max(0, left))

    # 打卡条交给前端算：云端有记录就能实时更新，不必等重新构建
    strip = '<div id="hero"></div>' 

    body = (head + strip + today_block +
            '<div class="kpi-grid" style="margin-top:16px">%s</div>' % kpis +
            '<h2>三科概况</h2><div class="grid">' + "".join(cards) + '</div>' +
            ex_block +
            band_block + trend_block + recent_block + DYN_JS)


    return page("看板 · %s" % NICK, "index.html", body)

TAG_RE = re.compile(r"<[^>]+>")


def clip_html(s, n=60):
    """按可见字符截断，保留并补全内联标签——直接切片会把 <u> 切一半，整块 DOM 会错位。"""
    if len(TAG_RE.sub("", s)) <= n:
        return s
    out, cnt, i, opened = [], 0, 0, []
    while i < len(s) and cnt < n:
        m = TAG_RE.match(s, i)
        if m:
            tag = m.group(0)
            out.append(tag)
            if tag.startswith("</"):
                if opened:
                    opened.pop()
            elif not tag.endswith("/>"):
                opened.append(tag[1:].split()[0])
            i = m.end()
        else:
            out.append(s[i])
            cnt += 1
            i += 1
    out.append("…")
    for t in reversed(opened):
        out.append("</%s>" % t)
    return "".join(out)


def sub_rows(items, s):
    errs = [i for i in items if i["subject"] == s and i["kind"] == "error"]
    vars_ = [i for i in items if i["subject"] == s and i["kind"] == "variant"]
    if not errs:
        return ('<div class="card empty">这一科还没入库错题。拍照发我，识别后入库。</div>', 0, len(vars_))
    rows = []
    for e in errs:
        cls = {"数": "q", "语": "c", "英": "e"}[s]
        rt = (e.get("retests") or [])
        last_rt = rt[-1] if rt else None
        if last_rt and last_rt.get("结果") == "未通过":
            tag = '<span class="tag warn">复测未过 %s</span>' % last_rt.get("日期", "")[5:]
        elif e["late"]:
            tag = '<span class="tag warn">逾期%d天</span>' % e["late"]
        elif e["status"] == "已巩固":
            tag = '<span class="tag ok">已巩固</span>'
        else:
            tag = '<span class="tag">%s %s</span>' % (e["status"], e["due"] or "")

        rt_html = ""
        if last_rt:
            rt_html = ('<div style="margin-top:10px;padding-top:9px;border-top:1px dashed #F0E3E8">'
                       '<div><span class="k">%s 复测</span>　<b style="color:#D2604F">%s</b>'
                       '　<span class="meta">%s · %s 秒</span></div>'
                       '<div style="margin-top:6px"><span class="k">这次错在</span>　%s</div>'
                       '<div style="margin-top:6px"><span class="k">下次这样做</span>　%s</div></div>') % (
                last_rt.get("日期", "")[5:], last_rt.get("结果", ""),
                last_rt.get("题号", ""), last_rt.get("用时秒", "—"),
                last_rt.get("本次错因", "—"), last_rt.get("下次提示", "—"))
        n_var = len([v for v in vars_ if v.get("from") == e["id"]])
        rows.append((
            '<div class="item %s"><div class="row"><div class="stem">%s</div>%s</div>'
            '<div class="meta">%s · %s · 变式 %d 道</div>'
            '<details><summary>错在哪、怎么讲</summary><div class="detail">'
            '<div><span class="k">孩子写的</span>　%s</div>'
            '<div><span class="k">正确</span>　%s</div>'
            '<div style="margin-top:6px"><span class="k">错因</span>　%s</div>'
            '<div style="margin-top:6px"><span class="k">讲法</span>　%s</div>%s'
            '</div></details></div>') % (
                cls, clip_html(e["stem"], 60), tag,
                e["id"], "、".join(e["kps"]), n_var,
                e.get("wrong", "—"), e.get("answer", "—"),
                e.get("cause_note", "—"), e.get("explain", "—"), rt_html))
    return ("".join(rows), len(errs), len(vars_))


def write_tree():
    """为三科各生成一份树数据：节点 + 先修边 + 题目挂载。"""
    tax = os.path.join(ROOT, "知识库", "taxonomy")
    tp = os.path.join(tax, "topics-primary.json")
    if not os.path.exists(tp):
        return
    topics = json.load(open(tp, encoding="utf-8"))
    deps = json.load(open(os.path.join(tax, "deps-primary.json"), encoding="utf-8"))
    mp = json.load(open(os.path.join(tax, "map-math.json"), encoding="utf-8"))

    for sub, tag, qfile in (("数", "math", "questions-math.json"),
                            ("语", "cn", "questions-cn.json"),
                            ("英", "en", "questions-en.json")):
        items = [x for x in topics if x["sub"] == sub]
        ids = {x["id"] for x in items}
        by_topic = {}

        # 我们自己的题（目前只有数学有映射）
        if sub == "数":
            for _name, v in mp.items():
                if v.get("topic") and v["topic"] in ids:
                    by_topic.setdefault(v["topic"], []).extend(v.get("题", []))

        # 开源题库
        qp = os.path.join(tax, qfile)
        if os.path.exists(qp):
            for x in json.load(open(qp, encoding="utf-8")):
                if x.get("kp") in ids:
                    by_topic.setdefault(x["kp"], []).append(x["id"])

        # 我们补的题（目前只有数学）
        sup_p = os.path.join(tax, "supplement.json")
        if sub == "数" and os.path.exists(sup_p):
            for x in json.load(open(sup_p, encoding="utf-8")):
                if x.get("kp") in ids:
                    by_topic.setdefault(x["kp"], []).append(x["id"])

        data = {
            "sub": sub,
            "topics": [{"id": x["id"], "name": x["name"], "g": x["grade"], "s": x["sem"],
                        "ch": x.get("chapter", ""), "ty": x.get("type", ""),
                        "d": x.get("desc", ""), "c": x.get("crit", []),
                        "q": by_topic.get(x["id"], [])} for x in items],
            "edges": [e for e in deps if e["t"] in ids and e["p"] in ids],
        }
        json.dump(data, open(os.path.join(OUT, "assets", "tree-%s.json" % tag), "w",
                             encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))


def write_tax():
    """把开源题库和我们补的题合并成 assets/tax-*.json。"""
    tax = os.path.join(ROOT, "知识库", "taxonomy")
    sup_p = os.path.join(tax, "supplement.json")
    sup = json.load(open(sup_p, encoding="utf-8")) if os.path.exists(sup_p) else []

    for sub, tag in (("数", "math"), ("语", "cn"), ("英", "en")):
        src = os.path.join(tax, "questions-%s.json" % tag)
        if not os.path.exists(src):
            continue
        items = json.load(open(src, encoding="utf-8"))
        if sub == "数":
            items = items + sup
        json.dump(items, open(os.path.join(OUT, "assets", "tax-%s.json" % tag), "w",
                              encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))


def build_tree():
    body = """<h1>知识树</h1>
<div class="sub" id="t_stat">读取中…</div>
<div class="card" style="padding:13px 15px;margin-bottom:20px">
  <div id="subs" style="display:flex;gap:7px;margin-bottom:9px"></div>
  <div id="books" style="display:flex;gap:5px;flex-wrap:wrap"></div>
</div>
<details style="margin:0 2px 12px">
  <summary style="cursor:pointer;font-size:12px;color:#B0A0A8">颜色和分数是什么意思</summary>
  <div class="meta" style="margin:7px 0 0;line-height:1.85">
  分数是她对这个点的掌握度（满分 100），会随时间下降，久不练就掉档。<br>
  <span style="color:#1D9E75">绿 ≥85 熟练</span> ·
  <span style="color:#5B8DEF">蓝 70–85 掌握</span> ·
  <span style="color:#EF9F27">黄 50–70 待巩固</span> ·
  <span style="color:#E24B4A">红 &lt;50 薄弱</span> ·
  灰 = 还没测
  </div>
</details>
<div id="tree"></div>
<script src="assets/cloud-sdk.js?v=__DBVER__"></script>
<script src="assets/db.js?v=__DBVER__"></script>
<script src="assets/engine.js?v=__DBVER__"></script>
<script src="assets/tree.js?v=__DBVER__"></script>"""
    return page("知识树", "tree.html", body)


def build_review():
    body = """<h1>错题讲解</h1>
<div class="sub" id="rv_sub">读取中…</div>
<div id="rv_today"></div>
<div class="sub" id="rv_hist_title" style="margin-top:30px;display:none">历史讲解</div>
<div id="rv_history"></div>
<script src="assets/cloud-sdk.js?v=__DBVER__"></script>
<script src="assets/db.js?v=__DBVER__"></script>
<script src="assets/engine.js?v=__DBVER__"></script>
<script src="assets/review.js?v=__DBVER__"></script>"""
    return page("错题讲解", "review.html", body)


def build_bank(items):
    n_err = sum(1 for i in items if i["kind"] == "error")
    n_var = sum(1 for i in items if i["kind"] == "variant")
    ol = os.path.join(ROOT, "大纲题库", "题库.json")
    n_out = len(json.load(open(ol, encoding="utf-8"))["题目"]) if os.path.exists(ol) else 0

    body = """<h1>题目库</h1>
<div class="sub" id="bank_sub">共 %d 道 · 错题 %d / 变式 %d / 大纲 %d</div>
<div class="card" style="padding:12px 14px">
  <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
    <button class="chip on" data-src="全部">全部</button>
    <button class="chip" data-src="错题">错题</button>
    <button class="chip" data-src="变式">变式</button>
    <button class="chip" data-src="大纲">大纲</button>
    <button class="chip" data-src="开源">开源</button>
    <span style="flex:1"></span>
    <input id="kw" placeholder="搜题干或编号"
      style="border:1px solid #EFE3E8;border-radius:999px;padding:7px 14px;font-size:0.867rem;
             font-family:inherit;outline:none;width:150px">
  </div>
  <div style="display:flex;gap:8px;margin-top:10px">
    <button class="chip on" data-sub="全部">全科</button>
    <button class="chip" data-sub="数">数学</button>
    <button class="chip" data-sub="语">语文</button>
    <button class="chip" data-sub="英">英语</button>
  </div>
</div>
<div class="meta" id="stat" style="margin:0 4px 10px"></div>
<div id="list"></div>
<div id="pager" style="text-align:center;margin:18px 0 8px"></div>
<style>
.chip{border:1px solid #EFE3E8;background:#fff;color:#8B7B83;font-size:0.833rem;
  font-family:inherit;padding:6px 13px;border-radius:999px;cursor:pointer}
.chip.on{background:#FFE7EE;border-color:#FFC9D8;color:#E85E86;font-weight:500}
.qsrc{font-size:0.733rem;padding:2px 7px;border-radius:6px;margin-left:6px}
.pg{border:1px solid #EFE3E8;background:#fff;color:#8B7B83;font-size:0.867rem;
  font-family:inherit;min-width:34px;height:34px;border-radius:10px;margin:0 3px;cursor:pointer}
.pg.on{background:#E85E86;border-color:#E85E86;color:#fff}
.pg[disabled]{opacity:.35;cursor:default}
</style>
<script src="assets/db.js?v=__DBVER__"></script>
<script src="assets/bank.js?v=__DBVER__"></script>""" % (n_err + n_var + n_out, n_err, n_var, n_out)

    return page("题目库", "bank.html", body)


def build_listen(items):
    """英语听力专项：录音在线播放，原文与答案默认折叠。"""
    ls = [i for i in items if i.get("type") == "listening"]
    if not ls:
        return ""
    rows = []
    for it in ls:
        opts = "".join("<div>%s. %s</div>" % ("ABCD"[k], o) for k, o in enumerate(it.get("options", [])))
        ans = it.get("answer", -1)
        ans_txt = ("%s. %s" % ("ABCD"[ans], it["options"][ans])
                   if isinstance(ans, int) and 0 <= ans < len(it.get("options", [])) else str(ans))
        script = it.get("script", "")
        rows.append(
            '<div class="one"><div class="q">%s</div>'
            '<div class="bar2"><button data-src="assets/audio/%s.mp3" type="button">▶ 播放录音</button>'
            '<span class="cnt">可以重听</span></div>'
            '<details><summary>听完再看：原文和答案</summary>'
            '<div class="script">%s</div><div class="opts">%s<div style="margin-top:6px">答案：<b>%s</b></div></div>'
            '</details></div>' % (
                it.get("stem", ""), it["id"], script or "（无原文）", opts, ans_txt))
    return ('<div class="lz"><div class="lh">🎧 听力专项 <em>%d 段</em></div>%s</div>'
            '<script>(function(){document.querySelectorAll(".lz button").forEach(function(b){'
            'var au=new Audio(b.dataset.src+(location.search||""));au.preload="auto";'
            'var c=b.parentNode.querySelector(".cnt"),n=0;'
            'b.onclick=function(){au.currentTime=0;au.play().then(function(){n++;'
            'b.textContent="↻ 再听一遍";c.textContent="已听 "+n+" 遍";}).catch(function(){'
            'c.textContent="音频加载失败，检查网络";});};'
            'au.onerror=function(){c.textContent="音频加载失败，检查网络";};});})();</script>') % (len(ls), "".join(rows))


def build_subject(items, s):
    name = dict((k, n) for k, n, _ in SUBJECTS).get(s, "数学")
    html, n_err, n_var = sub_rows(items, s)
    extra = build_listen(items) if s == "英" else ""
    if not n_err:
        body = ('<h1>%s</h1><div class="sub">还没有错题</div>%s%s') % (name, extra, html)
    else:
        body = ('<h1>%s</h1><div class="sub">%d 道错题 · %d 道变式</div>%s%s') % (name, n_err, n_var, extra, html)
    return page(name, "subject-%s.html" % s, body)


def build_progress(items, attempts, due):
    body = """<h1>练习记录</h1>
<div class="sub" id="p_stat">读取中…</div>
<div class="card" style="padding:12px 14px">
  <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:9px">
    <button class="chip on" data-fsub="全部">全部</button>
    <button class="chip" data-fsub="M">数学</button>
    <button class="chip" data-fsub="C">语文</button>
    <button class="chip" data-fsub="E">英语</button>
  </div>
  <div style="display:flex;gap:8px">
    <button class="chip on" data-fok="全部">全部</button>
    <button class="chip" data-fok="对">只看对</button>
    <button class="chip" data-fok="错">只看错</button>
  </div>
</div>
<div id="plist"></div>
<div id="ppager" style="text-align:center;margin:18px 0 8px"></div>
<style>
.chip{border:1px solid #EFE3E8;background:#fff;color:#8B7B83;font-size:0.833rem;
  font-family:inherit;padding:6px 13px;border-radius:999px;cursor:pointer}
.chip.on{background:#FFE7EE;border-color:#FFC9D8;color:#E85E86;font-weight:500}
.pg{border:1px solid #EFE3E8;background:#fff;color:#8B7B83;font-size:0.867rem;
  font-family:inherit;min-width:34px;height:34px;border-radius:10px;margin:0 3px;cursor:pointer}
.pg.on{background:#E85E86;border-color:#E85E86;color:#fff}
.pg[disabled]{opacity:.35;cursor:default}
</style>
<script src="assets/cloud-sdk.js?v=__DBVER__"></script>
<script src="assets/db.js?v=__DBVER__"></script>
<script src="assets/engine.js?v=__DBVER__"></script>
<script src="assets/progress.js?v=__DBVER__"></script>"""
    return page("记录", "progress.html", body)


BAND = {"熟练": "#54C9B3", "掌握": "#5B8DEF", "待巩固": "#FFC24B", "薄弱": "#FF7FA3", "未测": "#DCD5D8"}



def load_exams():
    f = os.path.join(ROOT, "题库", "exams.json")
    if not os.path.exists(f):
        return []
    return json.load(open(f, encoding="utf-8"))["考试"]


def spark(rows, color, full):
    w, h, pad = 170, 46, 5
    n = len(rows)
    pts = []
    for i, r in enumerate(rows):
        x = (w - 2 * pad) / 2 + pad if n == 1 else pad + i * (w - 2 * pad) / (n - 1)
        y = h - pad - (r["score"] / max(1, full)) * (h - 2 * pad)
        pts.append((round(x, 1), round(y, 1)))
    dots = "".join('<circle cx="%s" cy="%s" r="3" fill="%s"/>' % (x, y, color) for x, y in pts)
    line = ""
    if n > 1:
        line = '<polyline points="%s" fill="none" stroke="%s" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" opacity=".55"/>' % (
            " ".join("%s,%s" % xy for xy in pts), color)
    return '<svg viewBox="0 0 %d %d" width="%d" height="%d" style="display:block">%s%s</svg>' % (
        w, h, w, h, line, dots)


def build_exams():
    ex = load_exams()
    if not ex:
        return page("考试档案", "exams.html",
                    '<h1>考试档案</h1><div class="card empty">还没有考试记录</div>')

    by = {}
    for e in ex:
        by.setdefault(e["subject"], []).append(e)
    for k in by:
        by[k].sort(key=lambda x: x["date"])

    cards = []
    for key, name, color in SUBJECTS:
        rows = by.get(key, [])
        if not rows:
            continue
        last = rows[-1]
        prev = rows[-2] if len(rows) > 1 else None
        if prev:
            d = last["score"] - prev["score"]
            arrow = ('<span class="tag ok">↑ %d</span>' % d) if d > 0 else (
                ('<span class="tag warn">↓ %d</span>' % abs(d)) if d < 0 else '<span class="tag">持平</span>')
        else:
            arrow = '<span class="tag">首次</span>'
        cards.append(
            '<div class="card"><div class="row"><b><span class="dot" style="background:%s"></span>%s</b>%s</div>'
            '<div style="display:flex;align-items:flex-end;gap:14px;margin-top:8px">'
            '<div><div class="big">%d</div><div class="meta">最新得分 / %d</div></div>'
            '<div style="flex:1">%s</div></div>'
            '<div class="meta" style="margin-top:6px">%s　%s%s</div></div>'
            % (color, name, arrow, last["score"], last["full"],
               spark(rows, color, last["full"]), last["date"], last["name"],
               "" if last.get("confident", True) else '　<span class="tag warn">估算</span>'))

    rows_html = []
    for e in sorted(ex, key=lambda x: x["date"], reverse=True):
        nm = {"数": "数学", "语": "语文", "英": "英语"}[e["subject"]]
        learn = ""
        if e.get("learned_full"):
            learn = '<span class="meta">（已学 %d/%d）</span>' % (e["learned_score"], e["learned_full"])
        rows_html.append(
            '<div style="padding:11px 0;border-bottom:1px solid #F8EFF2">'
            '<div class="row"><b>%s</b><span class="meta">%s</span></div>'
            '<div class="meta" style="margin-top:3px">%s · %s · <b style="color:#3E3037">%d/%d</b> %s'
            '%s</div></div>'
            % (e["name"], e["date"], nm, e["subject"], e["score"], e["full"], learn,
               ('' if e.get("confident", True) else ' <span class="tag warn">估算</span>')
               + ('<div class="meta" style="margin-top:2px">%s</div>' % e["note"] if e.get("note") else '')))

    body = ('<h1>考试档案</h1><div class="sub">共 %d 次 · 看的是趋势，不是单次分数</div>%s'
            '<h2>全部记录</h2><div class="card">%s</div>'
            '<div class="card"><div class="meta">只记有卷子、有分数的考试。'
            '日常刷题在「记录」页，不混进来——两者口径不同，混在一起看不出升降。</div></div>'
            ) % (len(ex), "".join(cards), "".join(rows_html))
    return page("考试档案", "exams.html", body)


BAND = {"熟练": "#54C9B3", "掌握": "#5B8DEF", "待巩固": "#FFC24B", "薄弱": "#FF7FA3", "未测": "#DCD5D8"}


def load_checkin():
    f = os.path.join(ROOT, "题库", "checkin.json")
    if not os.path.exists(f):
        return None
    return json.load(open(f, encoding="utf-8"))


def load_pace_ledger():
    f = os.path.join(ROOT, "题库", "pace.json")
    if not os.path.exists(f):
        return None
    try:
        return json.load(open(f, encoding="utf-8"))
    except Exception:
        return None


def fmt_min(sec):
    sec = int(sec)
    return "%d'%02d\"" % (sec // 60, sec % 60)


CLOUD_ENDPOINT = "https://ai-tutor-77727.app.workbuddy.host"
CLOUD_KEY = "wbpk_AnAki3ens41hxihbkS0nXl_5PbED0De7hfmLJihGR8rsssZ39ejCp2u"


def build_checkin():
    c = load_checkin()
    if not c:
        return page("打卡", "checkin2.html",
                    '<h1>打卡</h1><div class="card empty">还没生成，先跑 python 题库/checkin.py</div>')

    streak = c["连续天数"]
    today_star = c.get("今日可得", 0)
    total = c["累计获得"]
    got = c["已提取"]
    avail = c["可提取"]

    tcell = next((d for d in c["本月"] if d["is_today"]), None)
    if tcell and tcell.get("rate") is not None:
        today_line = "今天 %d 题，对 %d 题，正确率 <b>%d%%</b>" % (
            tcell["pad_n"], tcell["pad_ok"], round(tcell["rate"] * 100))
    elif c["今日已打卡"]:
        today_line = "今天已经打完卡了。"
    else:
        today_line = "今天还没打卡——做完一组才算数。"

    tier = 0 if streak == 0 else 1 if streak < 3 else 3 if streak < 5 else 5 if streak < 7 else 7 if streak < 10 else 10
    crown = ('<svg class="crown" viewBox="0 0 64 40" xmlns="http://www.w3.org/2000/svg">'
             '<defs><linearGradient id="cg" x1="0" y1="0" x2="1" y2="1">'
             '<stop offset="0" stop-color="#FFC24B"/><stop offset=".5" stop-color="#ffe9a8"/>'
             '<stop offset="1" stop-color="#C9820F"/></linearGradient></defs>'
             '<path d="M5 33 L9 9 L21 21 L32 4 L43 21 L55 9 L59 33 Z" fill="url(#cg)"/>'
             '<rect x="5" y="33" width="54" height="4" rx="2" fill="#C9820F"/>'
             '</svg>') if tier >= 10 else ""
    sparks = ('<span class="spark a"></span><span class="spark b"></span><span class="spark c"></span>'
              if tier >= 7 else "")

    top = ('<h1>打卡</h1><div class="sub">做完一组才算打卡 · 连第 N 天得 N 颗星，答对率低会打折</div>'
           '<div class="card"><div class="row" style="align-items:flex-start">'
           '<div class="streak s%d" id="ck_streakbox">%s%s<div class="num" id="ck_streak">%d</div>'
           '<div class="meta">天连续打卡</div></div>'
           '<div style="text-align:right;padding-top:6px"><div class="stars" id="ck_soon">+%d</div>'
           '<div class="meta" id="ck_soon_lbl">最多可得</div></div></div>'
           '<div class="meta" style="margin-top:12px" id="ck_today">%s</div></div>') % (
        tier, crown, sparks, streak, today_star, today_line)

    # 星星账本
    # 按钮常驻：能提几颗要等云端数据算完才知道，构建时 0 颗就藏死的话永远长不出来
    btn = ('<button class="btn" id="wd" data-stars="%d" style="margin-top:14px;%s">'
           '全部提取 %d 颗</button>'
           '<div class="meta" id="wd_out" style="margin-top:8px"></div>'
           '<div class="meta" id="wd_none" style="margin-top:12px;color:#B9ACB2;%s">暂无可提取的星星</div>') % (
        avail, "" if avail > 0 else "display:none", avail,
        "display:none" if avail > 0 else "")

    ledger = ('<h2>星星</h2><div class="card" style="text-align:center">'
              '<div class="big" id="ck_avail" style="font-size:3.067rem;line-height:1.1;color:#C9820F">%d</div>'
              '<div class="meta">当前拥有 · 颗</div>'
              '<div class="row" style="margin-top:16px;padding-top:12px;border-top:1px solid #F8EFF2">'
              '<span class="meta">累计获得 <b id="ck_total" style="color:#3E3037">%d</b> 颗</span>'
              '<span class="meta">已提取 <b id="ck_got" style="color:#3E3037">%d</b> 颗</span></div>'
              '%s'
              '%s</div>') % (avail, total, got,
                             ('<div class="meta" style="margin-top:6px">其中全对奖励 %d 颗</div>'
                              % c.get("全对奖励合计", 0)) if c.get("全对奖励合计") else "",
                             btn)

    # 做题节奏：静态快照 pace.json 停在 11-09，和云端对不上。
    # 这里只留骨架，数字全部由前端用 Engine.paceOf(att) 现算。
    pace_block = ('<h2>做题节奏</h2><div class="card" id="ck_pace">'
                  '<div id="pace_head"><div class="row"><b>目标 15 分钟</b>'
                  '<span class="tag">读取中</span></div></div>'
                  '<div id="pace_list" style="margin-top:10px"></div>'
                  '<details class="mini" style="margin-top:12px"><summary>看近 30 天</summary>'
                  '<div id="pace_30" style="margin-top:6px"></div></details></div>')

    flow = c.get("流水", [])
    if flow:
        def frow(f):
            up = f["type"] == "in"
            return ('<div class="row" style="padding:9px 0;border-bottom:1px solid #F8EFF2">'
                    '<span class="meta">%s　%s</span>'
                    '<b style="color:%s">%s%d ★</b></div>') % (
                f["date"], f["note"], "#2E9C87" if up else "#D2604F",
                "+" if up else "−", f["stars"])
        flow_block = ('<details class="flowbox" id="ck_flowbox"><summary id="ck_flowsum">星星流水 · %d 条</summary>'
                      '<div id="ck_flow">%s</div></details>'
                      % (len(flow), "".join(frow(f) for f in flow)))
    else:
        flow_block = ('<details class="flowbox" id="ck_flowbox"><summary id="ck_flowsum">星星流水 · 0 条</summary>'
                      '<div id="ck_flow"><div class="meta" style="padding-top:10px">'
                      '还没有记录。做完第一组会出现一条「+1 ★」。</div></div></details>')

    # 日历（外层带 id，前端会用云端数据整块重画）
    cal = []
    for w in "一二三四五六日":
        cal.append('<div class="hd">%s</div>' % w)
    for d in c["本月"]:
        if d["date"].endswith("-01"):
            cal.extend(['<div></div>'] * d["dow"])
        cls = "fut" if d["future"] else d.get("band", "none")
        if d["is_today"]:
            cls += " td"
        inner = "%d" % int(d["date"][-2:])
        if d.get("rate") is not None:
            inner += "<i>%d%%</i>" % round(d["rate"] * 100)
        elif d.get("band") == "perfect":
            inner += "<i>★</i>"
        elif d.get("star"):
            inner += "<i>+%d★</i>" % d["star"]
        cal.append('<div class="%s">%s</div>' % (cls, inner))

    legend = ('<div class="legend">'
              '<span><b style="background:#fff2cc;box-shadow:inset 0 0 0 1.5px #FFC24B"></b>全对</span>'
              '<span><b style="background:#c9ecdb"></b>≥95%</span>'
              '<span><b style="background:#ddf2e6"></b>≥90%</span>'
              '<span><b style="background:#ecf5dc"></b>≥80%</span>'
              '<span><b style="background:#fcf0d7"></b>≥70%</span>'
              '<span><b style="background:#fae1df"></b>&lt;70%</span>'
              '<span><b style="background:#ececE6"></b>只交过纸笔</span>'
              '</div>')
    month = c["本月"][0]["date"][:7]
    cal_block = ('<h2 id="ck_month">%s 年 %d 月</h2><div class="card">'
                 '<div class="cal" id="ck_cal">%s</div>%s</div>') % (
        month[:4], int(month[5:]), "".join(cal), legend)

    rules = ('<div class="card"><div class="meta">'
             '节奏：刷题每天两组（每组目标 15 分钟，题量按实际用时自动在 6–12 题之间调），纸笔综合卷每周一次、不计入打卡。<br>'
             '规则：当天至少完成一组（%d 题以上）才算打卡；连第 N 天得 N 颗星，单日最多 %d 颗；'
             '答对率 ≥80%% 全拿，60–80%% 减半，低于 60%% 倒扣 1 颗（可为负）；'
             '中断一天，第二天从 1 颗重新开始。<br>'
             '全对再加：一组全对 +2 颗，两组都全对 +5 颗（当日取高的，不叠加）。<br>'
             '星星在另一个 App 里兑礼品，这里只记账。提取后记录日期与颗数，明早自动同步。'
             '</div></div>') % (c["规则"]["每组最少题数"], c["规则"]["单日上限"])

    foot = '<div style="margin-top:6px"><a class="meta" href="progress.html">查看逐题作答记录 →</a></div>'

    script = ("""<script src="assets/cloud-sdk.js?v=__DBVER__"></script>
<script src="assets/db.js?v=__DBVER__"></script>
<script src="assets/engine.js?v=__DBVER__"></script>
<script>(async function(){
  var cloud = null;
  try { cloud = WorkBuddyCloud.createWorkBuddyCloud({endpoint: DB.cloud.endpoint, publishableKey: DB.cloud.key}); } catch(e) {}
  if (!cloud) return;

  var rows = [], wd = [], pp = [];
  try { var r = await cloud.database.from("drill_submissions").select("*"); if (!r.error) rows = r.data || []; } catch(e) {}
  try { var w = await cloud.database.from("star_withdrawals").select("*"); if (!w.error) wd = w.data || []; } catch(e) {}
  try { var q = await cloud.database.from("paper_records").select("*"); if (!q.error) pp = q.data || []; } catch(e) {}

  var att = Engine.toAttempts(rows, pp);
  var ck = Engine.checkin(att, wd);

  var el = function(id){ return document.getElementById(id); };
  if (el("ck_streak")) el("ck_streak").textContent = ck.streak;

  // 近 30 天节奏：按天汇总屏幕作答，展开才渲染。
  // 注意：上面 paceBox.innerHTML 会重建整张卡片，所以这里等一拍再取节点。
  setTimeout(function(){
    var box = document.getElementById("pace_30");
    if (!box) return;
    var byDay = {};
    att.forEach(function(a){
      if (!a || !a.at || a.mode !== "pad") return;
      var v = byDay[a.at] || (byDay[a.at] = { n: 0, ok: 0, sec: 0, secN: 0 });
      v.n++; if (a.ok) v.ok++;
      if (a.sec) { v.sec += a.sec; v.secN++; }
    });
    var back = new Date(); back.setDate(back.getDate() - 29);
    var cutStr = back.getFullYear() + "-" + String(back.getMonth() + 1).padStart(2, "0")
               + "-" + String(back.getDate()).padStart(2, "0");
    var days = Object.keys(byDay).filter(function(d){ return d >= cutStr; }).sort().reverse();
    if (!days.length) { box.innerHTML = '<div class="meta">近 30 天还没有记录</div>'; return; }
    box.innerHTML = days.map(function(d){
      var v = byDay[d];
      var per = v.secN ? Math.round(v.sec / v.secN) : 0;
      return '<div class="row" style="padding:7px 0;border-bottom:1px solid #F8EFF2">'
        + '<span class="meta">' + d.slice(5).replace("-", "/") + '</span>'
        + '<span class="meta">' + v.n + ' 题' + (per ? ' · 每题 ' + per + ' 秒' : '') + '</span>'
        + '<b style="font-size:0.867rem;color:#3E3037">' + Math.round(v.ok * 100 / v.n) + '%</b></div>';
    }).join("");
  }, 0);
  // 打完卡就显示「今天已得多少」，没打卡才显示「最多可得」
  if (el("ck_soon")) {
    var ts = ck.checkedToday ? ck.todayStar : (ck.todayMax + 5);
    el("ck_soon").textContent = (ts >= 0 ? "+" : "") + ts;
  }
  if (el("ck_soon_lbl")) {
    el("ck_soon_lbl").textContent = ck.checkedToday
      ? ("今天已得 · 上限 " + (ck.todayMax + 5))
      : "最多可得";
  }
  if (el("ck_today")) {
    el("ck_today").innerHTML = ck.checkedToday
      ? ("今天 " + ck.todayN + " 题，对 " + ck.todayOk + " 题，正确率 <b>" + Math.round((ck.todayRate||0) * 100) + "%</b>")
      : "今天还没打卡——做完一组才算数。";
  }
  if (el("ck_avail")) {
    el("ck_avail").textContent = ck.available;
    el("ck_avail").style.color = ck.available < 0 ? "#D2604F" : "#C9820F";
  }
  if (el("ck_total")) el("ck_total").textContent = ck.totalEarned;
  if (el("ck_got")) el("ck_got").textContent = ck.withdrawn;

  // 连打档位只影响配色，跨档时跟着换
  var tier = ck.streak === 0 ? 0 : ck.streak < 3 ? 1 : ck.streak < 5 ? 3 : ck.streak < 7 ? 5 : ck.streak < 10 ? 7 : 10;
  if (el("ck_streakbox")) el("ck_streakbox").className = "streak s" + tier;

  /* ---------- 做题节奏：今天做完当场就该有记录 ---------- */
  var paceBox = el("ck_pace");
  if (paceBox) {
    var pc = Engine.paceOf(att);
    function mmss(sec) {
      sec = Math.round(sec);
      return Math.floor(sec / 60) + "'" + String(sec % 60).padStart(2, "0") + '"';
    }
    var grows = (pc.groups || []).slice(-3).reverse().map(function (g) {
      return '<div class="row" style="padding:8px 0;border-bottom:1px solid #F8EFF2">' +
        '<span class="meta">' + String(g.date).slice(5).replace("-", "/") +
        "　第 " + g.group + " 组 · " + g.n + " 题</span>" +
        '<b style="font-size:0.867rem;color:#3E3037">' + mmss(g.sec) + "　对 " + g.ok + "/" + g.n + "</b></div>";
    }).join("");
    paceBox.innerHTML = '<div class="row"><b>目标 15 分钟 · ' + pc.n + " 题</b>" +
      '<span class="tag">' + pc.judge + "</span></div>" +
      '<div class="meta" style="margin-top:8px;line-height:1.75">' + pc.why + "</div>" +
      '<div style="margin-top:10px">' + grows + "</div>" +
      '<details class="mini" style="margin-top:12px"><summary>看近 30 天</summary>' +
      '<div id="pace_30" style="margin-top:6px"></div></details>';
  }

  /* ---------- 日历：整块按云端数据重画 ---------- */
  function bandOf(st) {
    if (!st || !st.n) return (st && st.paperN) ? "record" : "none";
    if (st.n >= 3 && st.ok === st.n) return "perfect";
    var r = st.rate || 0;
    if (r >= 0.95) return "b95";
    if (r >= 0.90) return "b90";
    if (r >= 0.80) return "b80";
    if (r >= 0.70) return "b70";
    return "b0";
  }
  var calBox = el("ck_cal");
  if (calBox) {
    var todayStr = Engine.todayStr();
    var ym = todayStr.slice(0, 7), yy = +ym.slice(0, 4), mm = +ym.slice(5, 7);
    var firstDow = (new Date(yy, mm - 1, 1).getDay() + 6) % 7;   // 周一当第一列
    var daysInMonth = new Date(yy, mm, 0).getDate();
    var h = "", wds = "一二三四五六日";
    for (var i = 0; i < 7; i++) h += '<div class="hd">' + wds.charAt(i) + '</div>';
    for (var i = 0; i < firstDow; i++) h += "<div></div>";
    for (var dd = 1; dd <= daysInMonth; dd++) {
      var ds = ym + "-" + (dd < 10 ? "0" : "") + dd;
      var st = ck.dayStat[ds], cls, inner = String(dd);
      if (ds > todayStr) { cls = "fut"; }
      else {
        cls = bandOf(st);
        if (st && st.rate != null) inner += "<i>" + Math.round(st.rate * 100) + "%</i>";
        else if (st && st.perfect) inner += "<i>★</i>";
        else if (st && st.star) inner += "<i>" + (st.star > 0 ? "+" : "") + st.star + "★</i>";
      }
      if (ds === todayStr) cls += " td";
      h += '<div class="' + cls + '">' + inner + "</div>";
    }
    calBox.innerHTML = h;
    if (el("ck_month")) el("ck_month").textContent = yy + " 年 " + mm + " 月";
  }

  /* ---------- 星星流水：按云端账目重画 ---------- */
  var flowBox = el("ck_flow");
  if (flowBox) {
    var flow = [];
    Object.keys(ck.earned || {}).forEach(function (d) {
      var st = ck.dayStat[d] || {};
      flow.push({ date: d, type: "in", stars: ck.earned[d], note: "连续第 " + (st.streak || 1) + " 天" });
    });
    Object.keys(ck.perfectByDay || {}).forEach(function (d) {
      flow.push({ date: d, type: "in", stars: ck.perfectByDay[d],
                  note: "全对奖励（" + ((ck.perfectGroups && ck.perfectGroups[d]) || 1) + " 组全对）" });
    });
    (wd || []).forEach(function (w) {
      flow.push({ date: String(w.created_at || "").slice(0, 10), type: "out",
                  stars: w.stars, note: w.note || "提取" });
    });
    flow.sort(function (a, b) {
      if (a.date !== b.date) return a.date < b.date ? 1 : -1;
      return a.type === "out" ? -1 : 1;
    });
    if (flow.length) {
      flowBox.innerHTML = flow.map(function (f) {
        var up = f.type === "in";
        return '<div class="row" style="padding:9px 0;border-bottom:1px solid #F8EFF2">' +
          '<span class="meta">' + f.date + "　" + f.note + "</span>" +
          '<b style="color:' + (up ? "#2E9C87" : "#D2604F") + '">' + (up ? "+" : "−") + f.stars + " ★</b></div>";
      }).join("");
    } else {
      flowBox.innerHTML = '<div class="meta" style="padding-top:10px">还没有记录。做完第一组会出现一条「+1 ★」。</div>';
    }
    if (el("ck_flowsum")) el("ck_flowsum").textContent = "星星流水 · " + flow.length + " 条";
  }

  /* ---------- 提取按钮 ---------- */
  var b = el("wd"), none = el("wd_none");
  if (b) {
    if (ck.available > 0) {
      b.style.display = "";
      b.disabled = false;
      b.dataset.stars = ck.available;
      b.textContent = "全部提取 " + ck.available + " 颗";
      if (none) none.style.display = "none";
    } else {
      b.style.display = "none";
      if (none) {
        none.style.display = "";
        none.textContent = ck.available < 0
          ? ("欠着 " + (-ck.available) + " 颗，先做题补上")
          : "暂无可提取的星星";
      }
    }
  }

  if (b) {
    b.onclick = async function(){
      var n = parseInt(b.dataset.stars, 10);
      if (!confirm("确认提取 " + n + " 颗星？提取后去另一个 App 兑奖。")) return;
      b.disabled = true; b.textContent = "提交中…";
      try {
        var r2 = await cloud.database.from("star_withdrawals").insert({stars: n, note: "网页提取"});
        if (r2.error) throw r2.error;
        var d = new Date();
        var ds = d.getFullYear() + "-" + String(d.getMonth()+1).padStart(2,"0") + "-" + String(d.getDate()).padStart(2,"0");
        if (el("wd_out")) el("wd_out").innerHTML = "已提取 <b>" + n + " 颗</b> · " + ds +
          "<br>记录已上传，现在可以去另一个 App 兑奖。";
        // 不清空页面：把账面就地改掉，比让她刷新更直观
        ck.withdrawn += n;
        ck.available -= n;
        if (el("ck_avail")) { el("ck_avail").textContent = ck.available; }
        if (el("ck_got")) el("ck_got").textContent = ck.withdrawn;
        b.style.display = "none";
        if (none) {
          none.style.display = "";
          none.textContent = ck.available < 0
            ? ("欠着 " + (-ck.available) + " 颗，先做题补上")
            : "星星已全部提取，等下一次打卡";
        }
      } catch(e) {
        b.disabled = false; b.textContent = "全部提取 " + n + " 颗";
        if (el("wd_out")) el("wd_out").textContent = "提交失败，稍后再试或告诉家长。";
      }
    };
  }
})();</script>""")

    return page("打卡", "checkin2.html",
                top + ledger + pace_block + cal_block + rules + foot + flow_block + script)


def load_exams():
    f = os.path.join(ROOT, "题库", "exams.json")
    if not os.path.exists(f):
        return []
    return json.load(open(f, encoding="utf-8"))["考试"]


def spark(rows, color, full):
    w, h, pad = 170, 46, 5
    n = len(rows)
    pts = []
    for i, r in enumerate(rows):
        x = (w - 2 * pad) / 2 + pad if n == 1 else pad + i * (w - 2 * pad) / (n - 1)
        y = h - pad - (r["score"] / max(1, full)) * (h - 2 * pad)
        pts.append((round(x, 1), round(y, 1)))
    dots = "".join('<circle cx="%s" cy="%s" r="3" fill="%s"/>' % (x, y, color) for x, y in pts)
    line = ""
    if n > 1:
        line = '<polyline points="%s" fill="none" stroke="%s" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" opacity=".55"/>' % (
            " ".join("%s,%s" % xy for xy in pts), color)
    return '<svg viewBox="0 0 %d %d" width="%d" height="%d" style="display:block">%s%s</svg>' % (
        w, h, w, h, line, dots)


def build_exams():
    ex = load_exams()
    if not ex:
        return page("考试档案", "exams.html",
                    '<h1>考试档案</h1><div class="card empty">还没有考试记录</div>')

    by = {}
    for e in ex:
        by.setdefault(e["subject"], []).append(e)
    for k in by:
        by[k].sort(key=lambda x: x["date"])

    cards = []
    for key, name, color in SUBJECTS:
        rows = by.get(key, [])
        if not rows:
            continue
        last = rows[-1]
        prev = rows[-2] if len(rows) > 1 else None
        if prev:
            d = last["score"] - prev["score"]
            arrow = ('<span class="tag ok">↑ %d</span>' % d) if d > 0 else (
                ('<span class="tag warn">↓ %d</span>' % abs(d)) if d < 0 else '<span class="tag">持平</span>')
        else:
            arrow = '<span class="tag">首次</span>'
        cards.append(
            '<div class="card"><div class="row"><b><span class="dot" style="background:%s"></span>%s</b>%s</div>'
            '<div style="display:flex;align-items:flex-end;gap:14px;margin-top:8px">'
            '<div><div class="big">%d</div><div class="meta">最新得分 / %d</div></div>'
            '<div style="flex:1">%s</div></div>'
            '<div class="meta" style="margin-top:6px">%s　%s%s</div></div>'
            % (color, name, arrow, last["score"], last["full"],
               spark(rows, color, last["full"]), last["date"], last["name"],
               "" if last.get("confident", True) else '　<span class="tag warn">估算</span>'))

    rows_html = []
    for e in sorted(ex, key=lambda x: x["date"], reverse=True):
        nm = {"数": "数学", "语": "语文", "英": "英语"}[e["subject"]]
        learn = ""
        if e.get("learned_full"):
            learn = '<span class="meta">（已学 %d/%d）</span>' % (e["learned_score"], e["learned_full"])
        rows_html.append(
            '<div style="padding:11px 0;border-bottom:1px solid #F8EFF2">'
            '<div class="row"><b>%s</b><span class="meta">%s</span></div>'
            '<div class="meta" style="margin-top:3px">%s · %s · <b style="color:#3E3037">%d/%d</b> %s'
            '%s</div></div>'
            % (e["name"], e["date"], nm, e["subject"], e["score"], e["full"], learn,
               ('' if e.get("confident", True) else ' <span class="tag warn">估算</span>')
               + ('<div class="meta" style="margin-top:2px">%s</div>' % e["note"] if e.get("note") else '')))

    body = ('<h1>考试档案</h1><div class="sub">共 %d 次 · 看的是趋势，不是单次分数</div>%s'
            '<h2>全部记录</h2><div class="card">%s</div>'
            '<div class="card"><div class="meta">只记有卷子、有分数的考试。'
            '日常刷题在「记录」页，不混进来——两者口径不同，混在一起看不出升降。</div></div>'
            ) % (len(ex), "".join(cards), "".join(rows_html))
    return page("考试档案", "exams.html", body)


CUR_JS = """
<script src="assets/db.js?v=__DBVER__"></script>
<script src="assets/engine.js?v=__DBVER__"></script>
<script>(function(){
  var el = document.getElementById("cur");
  if (!el || !window.Engine) return;
  var today = Engine.todayStr();
  var rows = Engine.curriculumProgress(today);
  if (!rows.length) return;
  function subName(s){ return {"数":"数学","语":"语文","英":"英语"}[s] || s; }

  var stat = {"已学": 0, "进行中": 0, "未学": 0};
  rows.forEach(function(r){ stat[r.status]++; });

  var cur = rows.filter(function(r){ return r.status === "进行中"; });
  var curHtml = "";
  if (cur.length) {
    var g = {};
    cur.forEach(function(r){
      var k = r.sub + "|" + r.book + "|" + r.unit;
      (g[k] || (g[k] = [])).push(r);
    });
    var lines = Object.keys(g).map(function(k){
      var arr = g[k];
      return '<div style="padding:7px 0;border-bottom:1px solid #F8EFF2">'
        + '<b>' + subName(arr[0].sub) + ' · ' + arr[0].book + ' 第 ' + arr[0].unit + ' 单元</b>'
        + '<span class="meta">　' + arr[0].unitName + '</span>'
        + '<div class="meta" style="margin-top:3px">'
        + arr.map(function(x){ return x.name; }).join("、") + '</div></div>';
    });
    curHtml = '<div class="card"><div class="row"><b>本周在学</b>'
      + '<span class="tag">' + cur.length + ' 个知识点</span></div>'
      + lines.join("") + '</div>';
  }

  var byBook = {};
  rows.forEach(function(r){
    var k = r.sub + "|" + r.book;
    (byBook[k] || (byBook[k] = [])).push(r);
  });
  var order = ["一上","一下","二上","二下","三上","三下","四上","四下","五上","五下","六上","六下"];
  var keys = Object.keys(byBook).sort(function(a, b){
    var A = byBook[a][0], B = byBook[b][0];
    var d = order.indexOf(A.book) - order.indexOf(B.book);
    if (d) return d;
    return A.sub < B.sub ? -1 : 1;
  });
  var bars = keys.map(function(k){
    var arr = byBook[k];
    var done = arr.filter(function(x){ return x.status === "已学"; }).length;
    var doing = arr.filter(function(x){ return x.status === "进行中"; }).length;
    var pct = Math.round(done / arr.length * 100);
    var col = done === arr.length ? "#54C9B3" : (doing ? "#FF7FA3" : "#E6DFE2");
    return '<div style="display:flex;align-items:center;gap:10px;padding:5px 0">'
      + '<span class="meta" style="width:92px;flex:none">' + subName(arr[0].sub) + ' ' + arr[0].book + '</span>'
      + '<div class="bar" style="flex:1;margin:0"><i style="width:' + Math.max(2, pct)
      + '%;background:' + col + '"></i></div>'
      + '<span class="meta" style="width:54px;text-align:right;flex:none">' + done + '/' + arr.length + '</span></div>';
  });

  el.innerHTML = '<div class="card"><div class="row"><b>小学知识点 ' + rows.length + ' 个</b>'
    + '<span class="meta">已学 ' + stat["已学"] + ' · 进行中 ' + stat["进行中"]
    + ' · 未学 ' + stat["未学"] + '</span></div>'
    + '<div class="meta" style="margin-top:6px">按学期起点和单元周次自动推算，不用手改</div></div>'
    + curHtml
    + '<div class="card"><div class="row"><b>各册进度</b><span class="meta">已学 / 总数</span></div>'
    + bars.join("") + '</div>';
})();</script>
"""


def build_knowledge(sc):
    if not sc:
        return page("知识点", "knowledge.html",
                    '<h1>知识点地图</h1><div class="card empty">还没生成评分，先跑 python 知识库/score.py</div>')
    rows = sc["知识点"]
    measured = [r for r in rows if r["score"] is not None]

    head = ['<h1>知识点地图</h1><div class="sub">教材进度与掌握情况都在这页</div>',
            '<div id="cur"></div>']
    avg = []
    for s in ("数", "语", "英"):
        g = [r for r in measured if r["sub"] == s]
        if g:
            avg.append("%s %.0f" % ({"数": "数学", "语": "语文", "英": "英语"}[s],
                                   sum(r["score"] for r in g) / len(g)))
    if avg:
        head.append('<div class="card"><div class="meta">已测平均分：%s　'
                    '<span class="k">（目前只有错题证据，分数天然偏低；做对一次就会回升）</span></div></div>'
                    % "　".join(avg))

    head.append('<h2>考点掌握</h2>'
                '<div class="meta" style="margin:-6px 0 10px">'
                '上面是按教材单元排的「学到哪」，这里是按考点记的「掌握得怎样」。'
                '一次练习会同时影响两边：单元负责进度，考点负责分数。</div>')

    body = []
    for s in ("数", "语", "英"):
        sub = [r for r in rows if r["sub"] == s]
        if not sub:
            continue
        name = {"数": "数学", "语": "语文", "英": "英语"}[s]
        n_ok = len([r for r in sub if r["score"] is not None])
        body.append('<h2>%s　<span class="meta">%d 个知识点 · 已测 %d</span></h2>' % (name, len(sub), n_ok))
        domains = []
        for r in sub:
            if r["domain"] not in domains:
                domains.append(r["domain"])
        for d in domains:
            body.append('<div class="card"><div class="row"><b>%s</b></div>' % d)
            for r in sorted([x for x in sub if x["domain"] == d],
                            key=lambda r: (r["score"] is None, r["score"] or 0)):
                sc_ = r["score"]
                w = 0 if sc_ is None else max(3, min(100, sc_))
                band = r["band"]
                body.append(
                    '<div style="display:flex;align-items:center;gap:10px;padding:7px 0;border-bottom:1px solid #F8EFF2">'
                    '<div style="flex:1;font-size:0.933rem;%s">%s</div>'
                    '<div style="width:120px"><div class="bar" style="margin:0;background:%s"><i style="width:%d%%;background:%s"></i></div></div>'
                    '<div style="width:34px;text-align:right;font-size:0.867rem;color:%s">%s</div>'
                    '<div style="width:52px;text-align:right"><span class="tag" style="background:%s22;color:%s">%s</span></div>'
                    '</div>' % (
                        "" if sc_ is not None else "color:#B9ACB2",
                        r["name"], "#F6F2F3" if sc_ is None else "#F8EFF2", w, BAND[band],
                        "#3E3037" if sc_ is not None else "#B9ACB2",
                        ("%.0f" % sc_) if sc_ is not None else "—",
                        BAND[band], BAND[band], band))
            body.append('</div>')
    return page("知识点", "knowledge.html", "".join(head) + "".join(body) + CUR_JS)


def fix_links():
    """站点靠 ?sharecode= 才能访问，内部链接与静态资源都必须带上。"""
    import re
    if not Q:
        return
    for fn in os.listdir(OUT):
        if not fn.endswith(".html"):
            continue
        fp = os.path.join(OUT, fn)
        s = open(fp, encoding="utf-8").read()
        s = re.sub(r'href="([^"?]+\.html)"', lambda m: 'href="%s%s"' % (m.group(1), Q), s)
        s = re.sub(r'(href|src)="(assets/[^"?]+)"', lambda m: '%s="%s%s"' % (m.group(1), m.group(2), Q), s)
        open(fp, "w", encoding="utf-8").write(s)


def write_db(items):
    """前端引擎的题库包。页面打开时用它 + 云端记录，自己算排期和评分，
    这样题库和数据更新就不必等重新构建了。"""
    kps = json.load(open(os.path.join(ROOT, "知识库", "kps.json"), encoding="utf-8"))["知识点"]
    variants = json.load(open(os.path.join(ROOT, "题库", "variants.json"), encoding="utf-8"))["题目"]

    alias = {}
    for k in kps:
        for a in [k["name"]] + k.get("alias", []):
            a = (a or "").strip()
            if a:
                alias[a] = k["id"]

    def match(text):
        if not text:
            return None
        if text in alias:
            return alias[text]
        best = None
        for a, kid in alias.items():
            if a in text and (best is None or len(a) > best[0]):
                best = (len(a), kid)
        return best[1] if best else None

    kp_of = {}
    for v in variants:
        kp_of[v["id"]] = [i for i in (match(x) for x in v.get("kps", [])) if i]
    for it in items:
        if it["kind"] == "error":
            kp_of[it["id"]] = [i for i in (match(x) for x in it.get("kps", [])) if i]

    att = _load_json(os.path.join(QB, "attempts.json"), "记录", [])
    cut = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    recent = sorted({r["item_id"] for r in att if r.get("at", "") >= cut})

    # 小学知识点库（359 个，带册次与单元周次），进度在浏览器里按当天日期算
    cur_path = os.path.join(ROOT, "知识库", "curriculum.json")
    curriculum = {"terms": {}, "items": []}
    if os.path.exists(cur_path):
        cd = json.load(open(cur_path, encoding="utf-8"))
        curriculum = {
            "terms": cd["学期起点"],
            "weeks": cd.get("每周课时", 5),
            "items": [{"id": x["id"], "sub": x["sub"], "book": x["book"],
                       "unit": x["unit"], "unitName": x["unitName"],
                       "name": x["name"], "week": x["week"]} for x in cd["知识点"]],
        }

    # 大纲题库：转成和变式一样的结构，前端就不用准备两套渲染
    ol_path = os.path.join(ROOT, "大纲题库", "题库.json")
    outline = []
    ol_kp = {}
    if os.path.exists(ol_path):
        od = json.load(open(ol_path, encoding="utf-8"))
        ol_kp = {k["id"]: k for k in od["知识点"]}

        CODE_BOOK = {"1A": "一上", "1B": "一下", "2A": "二上", "2B": "二下",
                     "3A": "三上", "3B": "三下", "4A": "四上", "4B": "四下",
                     "5A": "五上", "5B": "五下", "6A": "六上", "6B": "六下"}

        for q in od["题目"]:
            kid = q["知识点"][0] or "M-5A-U1-01"
            parts = kid.split("-")           # M / 5A / U1 / 01
            sub_code = parts[0] if parts else "M"
            book_code = parts[1] if len(parts) > 1 else ""
            unit_code = parts[2] if len(parts) > 2 else ""
            outline.append({
                "id": q["id"],
                "subject": {"M": "数", "C": "语", "E": "英"}.get(sub_code, "数"),
                "book": CODE_BOOK.get(book_code, ""),
                "unit": int(unit_code[1:]) if unit_code.startswith("U") else 0,
                "kps": [q["名称"]] if q.get("名称") else
                       [ol_kp[k]["名称"] for k in q["知识点"] if k in ol_kp],
                "type": q["类型"],
                "stem": q["题干"],
                "options": q.get("选项", []),
                "answer": q["答案"],
                "hint": q.get("提示", ""),
                "explain": q.get("解析", ""),
                "难度": q.get("难度", 2),
                "难度分": q.get("难度分", 4),
                "slow": bool(q.get("慢题")),   # 必须读完材料才能答的题
                "source": "outline",
            })
        ol_sub = {k["id"]: k["科"] for k in od["知识点"]}
        for q in od["题目"]:
            kp_of[q["id"]] = list(q["知识点"])

    if not os.path.exists(ol_path):
        ol_sub = {}

    db = {
        "built": datetime.date.today().isoformat(),
        # 开源版构建时设 OPEN_SOURCE=1，把真实姓名换掉，避免发布出去带个人信息
        "student": ("小学生" if os.environ.get("OPEN_SOURCE") else "学生"),
        # 纸笔记录不会进云端表，只能构建时打进来，否则前端算出来的复测排期会偏
        "paper": [{"item_id": r["item_id"], "ok": bool(r.get("ok")),
                   "at": r.get("at", ""), "context": r.get("context", "")}
                  for r in att if r.get("mode") == "paper" and r.get("at")],
        "variants": variants,
        "outline": outline,
        "curriculum": curriculum,
        "errors": [i for i in items if i["kind"] == "error"],
        "kps": [{"id": k["id"], "sub": k["sub"], "name": k["name"]} for k in kps],
        "kpOf": kp_of,
        "kpSub": dict(dict({k["id"]: k["sub"] for k in kps}, **ol_sub),
                      **{x["id"]: x["sub"] for x in curriculum["items"]}),
        "recentIds": recent,
        "wrong": _load_wrong(),
        "tuning": json.load(open(os.path.join(ROOT, "题库", "tuning.json"), encoding="utf-8")),
        "shareCode": SHARE_CODE,
        "cloud": {"endpoint": CLOUD_ENDPOINT, "key": CLOUD_KEY},
    }
    open(os.path.join(OUT, "assets", "db.js"), "w", encoding="utf-8").write(
        "window.DB = " + json.dumps(db, ensure_ascii=False) + ";")


def _load_wrong():
    """读三科错题库，给「错题库」页用。字段名不统一，统一成同一套。"""
    out = {}
    for key, path in [("math", "数学错题库/错题库.json"),
                      ("cn", "语文错题库/错题库.json"),
                      ("en", "英语错题库/错题库.json")]:
        try:
            d = json.load(open(os.path.join(ROOT, path), encoding="utf-8"))
        except Exception:
            out[key] = []
            continue
        items = d.get("题目") or d.get("items") or []
        out[key] = items
    return out


def main():
    items, att, due = load()
    items = analyse(items, att)

    os.makedirs(os.path.join(OUT, "assets"), exist_ok=True)
    for old in os.listdir(OUT):
        fp = os.path.join(OUT, old)
        # 保留提前生成的一周练习（d-*.html）与刷题页，只清理本脚本产出的页面
        if os.path.isfile(fp) and old.endswith(".html") and not old.startswith("drill"):
            os.remove(fp)

    open(os.path.join(OUT, "assets", "style.css"), "w", encoding="utf-8").write(CSS)
    src_audio = os.path.join(HERE, "assets", "audio")
    if os.path.isdir(src_audio):
        dst = os.path.join(OUT, "assets", "audio")
        os.makedirs(dst, exist_ok=True)
        for fn in os.listdir(src_audio):
            shutil.copy(os.path.join(src_audio, fn), os.path.join(dst, fn))

    for fn in ("logo.svg", "icon-180.png", "icon-512.png", "engine.js", "cloud-sdk.js", "bank.js", "progress.js", "tree.js", "review.js"):
        srcf = os.path.join(HERE, "assets", fn)
        if os.path.exists(srcf):
            shutil.copy(srcf, os.path.join(OUT, "assets", fn))
    write_db(items)
    write_tree()
    write_tax()

    pages = {
        "index.html": build_index(items, due),
        "progress.html": build_progress(items, att, due),
        "exams.html": build_exams(),
        "bank.html": build_bank(items),
        "tree.html": build_tree(),
        "checkin2.html": build_checkin(),
        "review.html": build_review(),
    }
    for fn, html in pages.items():
        open(os.path.join(OUT, fn), "w", encoding="utf-8").write(html)

    # 科目页已并入题目库，旧链接跳过去（静态托管不会删文件，只能覆盖）
    for key, _name, _c in SUBJECTS:
        open(os.path.join(OUT, "subject-%s.html" % key), "w", encoding="utf-8").write(
            '<!DOCTYPE html><html><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1"><title>正在跳转</title></head>'
            '<body style="font-family:-apple-system,\'PingFang SC\',sans-serif;padding:40px 24px;color:#4A3B42">'
            '<p>这一科已经并进「题目库」了，正在带你过去…</p>'
            '<script>location.replace("bank.html" + location.search);</script></body></html>')

    # 刷题页：沿用现有产物
    for fn in ("drill.html",):
        src = os.path.join(ROOT, "刷题", fn)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(OUT, fn))

    # 知识点页已并入知识树，旧链接跳过去
    open(os.path.join(OUT, "knowledge.html"), "w", encoding="utf-8").write(
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>正在跳转</title></head>'
        '<body style="font-family:-apple-system,\'PingFang SC\',sans-serif;padding:40px 24px;color:#4A3B42">'
        '<p>知识点已经并进「知识树」了，正在带你过去…</p>'
        '<script>location.replace("tree.html" + location.search);</script></body></html>')

    fix_links()

    print("已生成 %s" % OUT)
    for f in sorted(os.listdir(OUT)):
        p = os.path.join(OUT, f)
        print("  %-14s %6.1f KB" % (f, os.path.getsize(p) / 1024) if os.path.isfile(p) else "  %-14s <dir>" % f)


if __name__ == "__main__":
    main()
