"""Interaktywny wykres v4 - TradingView lightweight-charts + styl RAEVEN / GKRVN.

Backend: tylko pandas + biblioteka standardowa (bez Dash/Plotly).
Frontend: jeden plik HTML (lightweight-charts z CDN), wskaźniki liczone w przeglądarce.

Uruchom:  python wykres_app.py   ->   http://127.0.0.1:8050
"""
import gzip
import json
import os
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pandas as pd
from wskazniki import tabela as tabela_wskaznikow

CACHE = Path("cache/yahoo")
PORT = int(os.environ.get("PORT", 8050))
DOMYSLNY = "KGH"

tickery = sorted(p.name.replace('.WA.csv.gz', '') for p in CACHE.glob('*.WA.csv.gz')
                 if not p.name.startswith('ETF'))


def wczytaj(tk):
    p = CACHE / f"{tk}.WA.csv.gz"
    with gzip.open(p, 'rt', encoding='utf-8') as f:
        df = pd.read_csv(f)
    df.columns = [c.lower().strip() for c in df.columns]
    dcol = next(c for c in df.columns if c in ('date', 'data', 'datetime'))
    df[dcol] = pd.to_datetime(df[dcol].astype(str).str[:10], errors='coerce')
    rename = {dcol: 'data', 'close': 'Close', 'high': 'High',
              'low': 'Low', 'open': 'Open', 'volume': 'Volume'}
    df = df.rename(columns=rename).sort_values('data')
    df = df.dropna(subset=['data', 'Open', 'High', 'Low', 'Close'])
    df['Volume'] = df['Volume'].fillna(0)
    df = df.drop_duplicates('data', keep='last')
    return df.reset_index(drop=True)


def dane_json(tk):
    df = wczytaj(tk)

    def sma(n):
        return [None if pd.isna(v) else round(float(v), 4)
                for v in df['Close'].rolling(n).mean()]

    rng = (df['High'] - df['Low']).replace(0, float('nan'))
    mfm = (((df['Close'] - df['Low']) - (df['High'] - df['Close'])) / rng).fillna(0)
    vsum = df['Volume'].rolling(20).sum().replace(0, float('nan'))
    cmf = [None if pd.isna(v) else round(float(v), 4)
           for v in (mfm * df['Volume']).rolling(20).sum() / vsum]

    return {
        'd': df['data'].dt.strftime('%Y-%m-%d').tolist(),
        'o': df['Open'].round(4).tolist(),
        'h': df['High'].round(4).tolist(),
        'l': df['Low'].round(4).tolist(),
        'c': df['Close'].round(4).tolist(),
        'v': df['Volume'].astype('int64').tolist(),
        's20': sma(20), 's50': sma(50), 's200': sma(200), 'cmf': cmf,
    }


HTML = r"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>RAEVEN · ZPAPSG — Wykres</title>
<meta name="theme-color" content="#0b1b3f">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Nunito+Sans:wght@300;400;600;700;800&display=swap" rel="stylesheet">
<script src="https://unpkg.com/lightweight-charts@5.2.1/dist/lightweight-charts.standalone.production.js"></script>
<style>
:root{
  --navy:#0b2150;--navy2:#1f4fa8;--or:#d9650c;--or2:#f08428;--sky:#5da4ee;
  --ink:#1b3058;--mut:#4f6286;--line:#d6e3f3;
  --bg:#eef4fb;--sky1:#e6f1fd;--sky3:#f8fbff;
}
*{box-sizing:border-box}
html{background:var(--bg)}
body{
  margin:0;font:400 16px/1.7 "Nunito Sans","Segoe UI",Frutiger,Tahoma,sans-serif;
  color:var(--ink);background:var(--bg);min-height:100vh;overflow-x:hidden;
  -webkit-font-smoothing:antialiased;
  padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px);
}
h1{color:var(--navy);line-height:1.18;margin:0 0 .35em;letter-spacing:-.015em;font-size:clamp(2.2rem,4.8vw,3.2rem);font-weight:300}
h1 strong{font-weight:800}
h1:after{
  content:"";display:block;width:56px;height:4px;border-radius:4px;margin-top:16px;
  background:linear-gradient(90deg,var(--or2),var(--sky));box-shadow:inset 0 1px 0 rgba(255,255,255,.6);
}
.w{max-width:1280px;margin:0 auto;padding:0 28px}
.sl{color:var(--mut);margin:0 0 32px;max-width:70ch;font-size:1.05rem}

/* header */
header{
  position:sticky;top:0;z-index:50;
  background:linear-gradient(rgba(255,255,255,.96),rgba(234,243,253,.92));
  border-bottom:1px solid var(--line);
  box-shadow:inset 0 1px 0 #fff,0 4px 18px rgba(20,60,120,.08);
  backdrop-filter:blur(12px);
}
header .w{display:flex;align-items:center;gap:28px;height:72px}
.logo{display:flex;align-items:center;gap:12px;font-weight:800;color:var(--navy);text-decoration:none}
.logo b{display:block;font-size:1.25rem;font-weight:800;letter-spacing:.1em;line-height:1.05}
.logo small{display:block;color:var(--or);font-weight:700;font-size:.7rem;letter-spacing:.06em;line-height:1.2;margin-top:2px}
.orb-mini{
  position:relative;width:42px;height:42px;border-radius:50%;flex:none;
  background:radial-gradient(circle at 32% 25%,#fff 0,#ffd9b0 16%,var(--or2) 52%,#a24800 100%);
  box-shadow:inset -5px -7px 12px rgba(120,60,0,.3),0 3px 8px rgba(20,40,90,.18);
}
.orb-mini:after{
  content:"";position:absolute;left:14%;top:6%;width:62%;height:36%;border-radius:50%;
  background:linear-gradient(rgba(255,255,255,.7),rgba(255,255,255,0));
}
.hnav{flex:1;display:flex;justify-content:flex-end;color:var(--mut);font-weight:700;font-size:.78rem;letter-spacing:.09em;text-transform:uppercase}

main{padding:30px 0 40px}
.wide{width:94vw;max-width:2800px;margin:0 auto;padding:0}
main h1{margin-bottom:.15em}.sl{margin:0 0 22px}

/* surfaces */
.glass{
  background:linear-gradient(#fff,#f5f9fe);border:1px solid var(--line);border-radius:26px;
  box-shadow:0 1px 2px rgba(20,60,120,.06),0 18px 36px rgba(20,60,120,.11);
  padding:30px;position:relative;overflow:hidden;
}
.glass:before{content:"";position:absolute;left:0;right:0;top:0;height:42%;background:linear-gradient(rgba(255,255,255,.75),rgba(255,255,255,0));pointer-events:none}
.glass>*{position:relative}

/* notowania */
.up{color:#1f8a4c!important}.dn{color:#c93b3b!important}
.qtop{display:flex;justify-content:space-between;align-items:flex-start;gap:22px;flex-wrap:wrap;margin-bottom:8px}
.qs{font-size:.78rem;font-weight:700;letter-spacing:.09em;text-transform:uppercase;color:var(--or)}
.qpx{font-size:3rem;font-weight:300;color:var(--navy);line-height:1.1;margin:4px 0 8px}
.qpx small{font-size:1rem;color:var(--mut);font-weight:600;margin-left:8px}
.bd{display:inline-block;padding:4px 12px;border-radius:999px;font-weight:700;font-size:.84rem;margin-right:8px;background:#e6f0fb}
.bd small{color:var(--mut);font-weight:600}
.bd.up{background:#e0f5e9}.bd.dn{background:#fbe6e6}
.qctl{display:grid;gap:10px;justify-items:end}
.row{display:flex;gap:10px;flex-wrap:wrap;justify-content:flex-end;align-items:center}
.seg{display:inline-flex;padding:3px;border-radius:999px;background:#dde9f8;box-shadow:inset 0 1px 3px rgba(20,60,120,.18)}
.seg button{border:0;background:transparent;padding:7px 14px;border-radius:999px;font:inherit;font-weight:700;font-size:.8rem;color:var(--mut);cursor:pointer;transition:background .2s,color .2s,box-shadow .2s}
.seg button[aria-pressed="true"]{background:linear-gradient(#fff,#e9f2fd);color:var(--navy);box-shadow:0 1px 3px rgba(20,60,120,.3)}
.pill{display:inline-block;padding:7px 16px;border-radius:999px;border:1px solid #b9cfe9;background:linear-gradient(#fff,#e3eefb);color:var(--navy);font:700 .8rem "Nunito Sans",sans-serif;cursor:pointer;box-shadow:inset 0 1px 0 #fff}
.pill:hover{border-color:var(--navy2)}
.pill.on{background:linear-gradient(#f9a965,var(--or));color:#fff;border-color:#a8480a;text-shadow:0 1px 0 rgba(120,50,0,.3)}
.sym{
  width:150px;padding:8px 16px;border-radius:999px;border:1px solid #b9cfe9;background:linear-gradient(#fff,#e3eefb);
  color:var(--navy);font:800 .86rem "Nunito Sans",sans-serif;letter-spacing:.06em;text-transform:uppercase;
  box-shadow:inset 0 1px 0 #fff;outline:none;
}
.sym:focus{border-color:var(--navy2);box-shadow:0 0 0 3px rgba(93,164,238,.35)}
:focus-visible{outline:3px solid rgba(93,164,238,.7);outline-offset:2px}

.qwrap{display:flex;gap:12px;align-items:flex-start;margin-top:14px}
.cw{position:relative;flex:1;min-width:0}
.tb{display:flex;flex-direction:column;gap:3px;padding:6px;border-radius:16px;background:linear-gradient(#fff,#eaf3fd);border:1px solid var(--line);box-shadow:inset 0 1px 0 #fff,0 6px 16px rgba(20,60,120,.1);flex:none;position:sticky;top:84px;z-index:6}
.tb button{width:38px;height:38px;border-radius:12px;border:0;background:transparent;color:var(--navy);display:grid;place-items:center;cursor:pointer;transition:background .15s,color .15s}
.tb button:hover{background:#dbe9f9}
.tb button[aria-pressed="true"]{background:linear-gradient(#f9a965,var(--or));color:#fff;box-shadow:inset 0 1px 0 rgba(255,255,255,.55),0 3px 8px rgba(200,100,10,.3)}
.tb hr{width:26px;border:0;border-top:1px solid #cfe0f4;margin:5px auto}
.fbar{position:absolute;top:10px;left:50%;transform:translateX(-50%);display:none;align-items:center;gap:12px;padding:6px 12px;border-radius:14px;background:rgba(255,255,255,.96);border:1px solid var(--line);box-shadow:0 10px 24px rgba(20,60,120,.18);z-index:7}
.fbar .seg button{padding:4px 10px;min-width:30px}
#chart{width:100%;height:90vh;min-height:560px}
#chart.c-draw *{cursor:crosshair!important}
#chart.c-pt *{cursor:pointer!important}
#chart.c-mv *{cursor:move!important}
.glass:fullscreen{overflow:auto;border-radius:0;padding:22px 28px}
.glass:fullscreen #chart{height:calc(100vh - 300px);min-height:360px}
.sw{width:22px;height:22px;border-radius:50%;border:2px solid #fff;padding:0;cursor:pointer;box-shadow:0 0 0 1px #b9cfe9,0 1px 3px rgba(20,60,120,.25);transition:transform .15s}
.sw:hover{transform:scale(1.12)}
.sw[aria-pressed="true"]{box-shadow:0 0 0 2px var(--navy),0 1px 3px rgba(20,60,120,.25)}
.sws{display:inline-flex;gap:8px;align-items:center;padding:0 6px}
.pill[disabled]{opacity:.45;cursor:default}
@media (max-width:760px){.qwrap{flex-direction:column}.tb{flex-direction:row;flex-wrap:wrap;position:static}.tb hr{display:none}.fbar{flex-wrap:wrap;width:92%;justify-content:center}#chart{min-height:520px}.qctl{justify-items:start}.row{justify-content:flex-start}}
.qtip{position:absolute;top:6px;left:0;pointer-events:none;opacity:0;transform:translateY(4px);transition:opacity .15s,transform .15s;min-width:150px;padding:9px 13px;border-radius:12px;background:rgba(11,33,80,.95);color:#fff;font-size:.8rem;line-height:1.45;box-shadow:0 12px 26px rgba(0,20,70,.35);white-space:nowrap;z-index:5}
.qtip.on{opacity:1;transform:none}
.qtip small{display:block;color:#b9cdf0;font-weight:600}
.qtip .r{display:flex;justify-content:space-between;gap:16px;font-weight:600}
.qtip .r b{font-weight:800}
.lgd{display:flex;gap:10px 16px;flex-wrap:wrap;align-items:center;margin:12px 0 0;font-size:.84rem;font-weight:700;color:var(--navy)}
.lgd button{display:inline-flex;align-items:center;border:0;background:none;padding:2px 4px;font:inherit;color:inherit;cursor:pointer;border-radius:8px}
.lgd button i{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px}
.lgd button[aria-pressed="false"]{opacity:.38;text-decoration:line-through}
.lgd em{margin-left:auto;font-style:normal;font-weight:600;color:var(--mut)}
.sstrip{display:grid;grid-template-columns:repeat(4,1fr);margin-top:14px;border-top:1px solid #dbe7f6}
.sstrip div{padding:14px 10px 4px;border-right:1px solid #dbe7f6}.sstrip div:last-child{border:0}
.sstrip small{display:block;color:var(--mut);font-weight:600;font-size:.76rem}
.sstrip b{color:var(--navy);font-size:1.05rem}
@media (max-width:980px){.sstrip{grid-template-columns:repeat(2,1fr)}}
.note{color:var(--mut);font-size:.86rem;margin:14px 0 0}
.err{padding:40px 0;text-align:center;color:var(--mut);font-weight:600}
#panel{margin-top:22px}
#panel-reko{font-size:2.2rem;font-weight:300;color:var(--navy);
  line-height:1.1;margin-top:6px}
#panel-reko.mk{color:#0d5a2a;font-weight:800}
#panel-reko.k{color:#1f8a4c;font-weight:800}
#panel-reko.r{color:#a02a2a;font-weight:800}
#panel-reko.s{color:#7a1515;font-weight:800}
#panel-sum{font-size:1rem;font-weight:700;color:var(--mut);text-align:right}
#panel-sum b{color:var(--navy);font-size:1.4rem}
.sig-table{width:100%;border-collapse:separate;border-spacing:0;
  font-size:.86rem;margin-top:18px}
.sig-table th{text-align:left;padding:10px 12px;background:#e6f1fd;
  color:var(--navy);font-weight:800;font-size:.7rem;letter-spacing:.07em;
  text-transform:uppercase;border-bottom:1px solid var(--line)}
.sig-table th:first-child{border-radius:12px 0 0 0}
.sig-table th:last-child{border-radius:0 12px 0 0}
.sig-table td{padding:9px 12px;border-bottom:1px solid #eaf0fa;
  color:var(--ink);vertical-align:middle}
.sig-table tr:hover td{background:#f5f9fe}
.sig-table .grp{font-weight:700;color:var(--mut);font-size:.74rem;
  text-transform:uppercase;letter-spacing:.05em}
.sig-table .ind{font-weight:700;color:var(--navy)}
.sig-table .val{font-family:ui-monospace,SFMono-Regular,monospace;
  font-size:.82rem;color:var(--ink)}
.sig-badge{display:inline-block;padding:3px 10px;border-radius:999px;
  font-weight:800;font-size:.7rem;letter-spacing:.04em}
.sig-mk{background:#c9ebd6;color:#0d5a2a}
.sig-k{background:#e0f5e9;color:#1f8a4c}
.sig-n{background:#eaeef6;color:#4f6286}
.sig-r{background:#fbe6e6;color:#a02a2a}
.sig-s{background:#f8d4d4;color:#7a1515}
</style>
</head>
<body>
<header>
  <div class="w">
    <a class="logo" href="/"><span class="orb-mini"></span><span><b>RAEVEN</b><small>ZPAPSG</small></span></a>
    <div class="hnav">Interactive Chart</div>
  </div>
</header>

<main>
  <div class="wide">
    <h1>Wykres <strong>interaktywny</strong></h1>
    <p class="sl">Notowania spółek z GPW: świece lub linia, średnie kroczące, wolumen, RSI i MACD. Przeciągaj, aby przewijać, kółko powiększa. Rysunki: lewy pasek narzędzi; zaznaczony kształt chwytasz, uchwyty zmieniają rozmiar, Delete usuwa.</p>

    <div class="glass" id="card">
      <div class="qtop">
        <div>
          <div class="qs" id="qs">—</div>
          <div class="qpx"><span id="px">—</span><small>PLN</small></div>
          <div id="badges"></div>
        </div>
        <div class="qctl">
          <div class="row">
            <input class="sym" id="sym" list="tickers" autocomplete="off" spellcheck="false" aria-label="Spółka" placeholder="Spółka">
            <datalist id="tickers"></datalist>
            <div class="seg" id="seg-view"></div>
            <button class="pill" id="fs" type="button">Pełny ekran</button>
          </div>
          <div class="seg" id="seg-rng"></div>
        </div>
      </div>

      <div class="qwrap">
        <div class="tb" id="tb"></div>
        <div class="cw">
          <div id="chart"></div>
          <div class="fbar" id="fbar"></div>
          <div class="qtip" id="tip" role="status" aria-live="polite"></div>
        </div>
      </div>

      <div class="lgd" id="lgd"></div>
      <div class="sstrip" id="sstrip"></div>
      <p class="note" id="note"></p>
    </div>

    <div class="glass" id="panel">
      <div class="qtop">
        <div>
          <div class="qs">Panel sygnałów</div>
          <div id="panel-reko">—</div>
        </div>
        <div id="panel-sum"></div>
      </div>
      <table class="sig-table">
        <thead><tr>
          <th>Grupa</th><th>Wskaźnik</th><th>Wartość</th>
          <th>Sygnał</th><th>Waga</th><th>Opis</th>
        </tr></thead>
        <tbody id="sig-body"></tbody>
      </table>
    </div>
  </div>
</main>

<script>
(function(){
"use strict";
var LW = window.LightweightCharts;
var NAVY="#0b2150", NAVY2="#1f4fa8", OR="#d9650c", OR2="#f08428", SKY="#5da4ee",
    RED="#c93b3b", GREEN="#1f8a4c", LINE="#d6e3f3", MUT="#4f6286", VIOLET="#8a5cc7";
var RANGES = [[63,"3M"],[126,"6M"],[252,"1R"],[504,"2R"],[1260,"5R"],[0,"MAX"]];
var VIEWS  = [["cdl","Świece"],["line","Linia"]];
var MAS    = [["sma20",20,SKY,"SMA 20"],["sma50",50,OR2,"SMA 50"],["sma200",200,RED,"SMA 200"]];

var S = { tk:null, rng:252, view:"cdl", tool:"cur", D:null, idx:{}, ma:{sma20:true,sma50:true,sma200:true} };
var $ = function(id){ return document.getElementById(id); };

/* ---------- format ---------- */
function fN(v, d){ return v==null||isNaN(v) ? "—" : v.toLocaleString("pl-PL",{minimumFractionDigits:d,maximumFractionDigits:d}); }
function fP(v){ return (v>=0?"+":"−")+Math.abs(v*100).toLocaleString("pl-PL",{minimumFractionDigits:2,maximumFractionDigits:2})+"%"; }
function fD(s){ var p=s.split("-"); return +p[2]+"."+p[1]+"."+p[0]; }
function ts(s){ var p=s.split("-"); return Date.UTC(+p[0],+p[1]-1,+p[2])/1000; }
function fV(v){ return v>=1e6 ? fN(v/1e6,2)+" mln" : (v>=1e3 ? fN(v/1e3,1)+" tys." : fN(v,0)); }

/* ---------- wskaźniki (jak w pandas) ---------- */
function ema(x,alpha){ var o=new Array(x.length), y=x[0]; o[0]=y; for(var i=1;i<x.length;i++){ y=(1-alpha)*y+alpha*x[i]; o[i]=y; } return o; }
function rsi(c,p){
  var g=[0],l=[0]; for(var i=1;i<c.length;i++){ var d=c[i]-c[i-1]; g.push(d>0?d:0); l.push(d<0?-d:0); }
  var ag=ema(g,1/p), al=ema(l,1/p);
  return ag.map(function(a,i){ return al[i]===0 ? 100 : 100-100/(1+a/al[i]); });
}
function macd(c){
  var ef=ema(c,2/13), es=ema(c,2/27), m=ef.map(function(v,i){ return v-es[i]; }), sg=ema(m,2/10);
  return { m:m, s:sg, h:m.map(function(v,i){ return v-sg[i]; }) };
}

/* ---------- chart ---------- */
var chart = LW.createChart($("chart"), {
  autoSize:true,
  layout:{
    background:{ type:"solid", color:"transparent" }, textColor:MUT,
    fontFamily:'"Nunito Sans","Segoe UI",sans-serif', fontSize:11,
    panes:{ separatorColor:LINE, separatorHoverColor:"rgba(93,164,238,.3)", enableResize:true }
  },
  grid:{ vertLines:{ visible:false }, horzLines:{ color:LINE, style:LW.LineStyle.Dashed } },
  crosshair:{
    mode:LW.CrosshairMode.Normal,
    vertLine:{ color:"rgba(31,79,168,.4)", style:LW.LineStyle.Dashed, width:1, labelBackgroundColor:NAVY },
    horzLine:{ color:"rgba(31,79,168,.4)", style:LW.LineStyle.Dashed, width:1, labelBackgroundColor:NAVY }
  },
  rightPriceScale:{ borderColor:LINE },
  timeScale:{ borderColor:LINE, rightOffset:6, timeVisible:false, secondsVisible:false },
  localization:{ locale:"pl-PL", dateFormat:"dd MMM yyyy" }
});

var candle = chart.addSeries(LW.CandlestickSeries, {
  upColor:GREEN, downColor:RED, borderVisible:false, wickUpColor:GREEN, wickDownColor:RED,
  lastValueVisible:false, priceLineVisible:false,
  priceFormat:{ type:"price", precision:2, minMove:0.01 }
}, 0);
var area = chart.addSeries(LW.AreaSeries, {
  lineColor:NAVY2, lineWidth:2, topColor:"rgba(93,164,238,.35)", bottomColor:"rgba(93,164,238,0)",
  lastValueVisible:false, priceLineVisible:false, visible:false,
  priceFormat:{ type:"price", precision:2, minMove:0.01 }
}, 0);
candle.priceScale().applyOptions({ scaleMargins:{ top:0.06, bottom:0.24 } });

var vol = chart.addSeries(LW.HistogramSeries, {
  priceFormat:{ type:"volume" }, priceScaleId:"vol", lastValueVisible:false, priceLineVisible:false
}, 0);
chart.priceScale("vol", 0).applyOptions({ scaleMargins:{ top:0.82, bottom:0 } });

var maS = {};
MAS.forEach(function(m){
  maS[m[0]] = chart.addSeries(LW.LineSeries, {
    color:m[2], lineWidth:1.5, lastValueVisible:false, priceLineVisible:false,
    crosshairMarkerVisible:false, priceFormat:{ type:"price", precision:2, minMove:0.01 }
  }, 0);
});

var rsiS = chart.addSeries(LW.LineSeries, {
  color:VIOLET, lineWidth:1.5, lastValueVisible:true, priceLineVisible:false,
  priceFormat:{ type:"price", precision:1, minMove:0.1 },
  autoscaleInfoProvider:function(){ return { priceRange:{ minValue:0, maxValue:100 } }; }
}, 1);
[[70,RED,LW.LineStyle.Dashed],[50,"#aab8d0",LW.LineStyle.Dotted],[30,GREEN,LW.LineStyle.Dashed]].forEach(function(l){
  rsiS.createPriceLine({ price:l[0], color:l[1], lineWidth:1, lineStyle:l[2], axisLabelVisible:false, title:"" });
});

var mL = chart.addSeries(LW.LineSeries, { color:NAVY2, lineWidth:1.5, lastValueVisible:false, priceLineVisible:false, crosshairMarkerVisible:false }, 2);
var mS = chart.addSeries(LW.LineSeries, { color:OR2,   lineWidth:1.5, lastValueVisible:false, priceLineVisible:false, crosshairMarkerVisible:false }, 2);
var mH = chart.addSeries(LW.HistogramSeries, { lastValueVisible:false, priceLineVisible:false, priceFormat:{ type:"price", precision:3, minMove:0.001 } }, 2);
mH.createPriceLine({ price:0, color:"#8896b0", lineWidth:1, lineStyle:LW.LineStyle.Solid, axisLabelVisible:false, title:"" });

var cmfS = chart.addSeries(LW.BaselineSeries, {
  baseValue:{ type:"price", price:0 },
  topLineColor:GREEN, topFillColor1:"rgba(31,138,76,.28)", topFillColor2:"rgba(31,138,76,.03)",
  bottomLineColor:RED, bottomFillColor1:"rgba(201,59,59,.03)", bottomFillColor2:"rgba(201,59,59,.28)",
  lineWidth:1.5, lastValueVisible:true, priceLineVisible:false, priceFormat:{ type:"price", precision:3, minMove:0.001 }
}, 3);
cmfS.createPriceLine({ price:0, color:"#8896b0", lineWidth:1, lineStyle:LW.LineStyle.Solid, axisLabelVisible:false, title:"" });

function setPanes(){
  var p = chart.panes();
  if (p[0]) p[0].setStretchFactor(3.6);
  if (p[1]) p[1].setStretchFactor(1);
  if (p[2]) p[2].setStretchFactor(1.1);
  if (p[3]) p[3].setStretchFactor(1);
}
setPanes();

/* etykiety paneli (tekst w lewym górnym rogu) */
function PaneLabel(txt){ this.t = txt; }
PaneLabel.prototype.paneViews = function(){
  var t = this.t;
  return [{ renderer:function(){ return { draw:function(target){
    target.useMediaCoordinateSpace(function(s){
      var c = s.context; c.font = '800 11px "Nunito Sans","Segoe UI",sans-serif'; c.fillStyle = MUT; c.textBaseline = "top"; c.fillText(t, 10, 8);
    });
  } }; } }];
};
rsiS.attachPrimitive(new PaneLabel("RSI (14)"));
mH.attachPrimitive(new PaneLabel("MACD (12, 26, 9)"));
cmfS.attachPrimitive(new PaneLabel("CMF (20)"));

/* ---------- rysowanie (styl TradingView) ---------- */
var COLORS = [OR2, NAVY2, GREEN, RED, VIOLET, "#1aa3a3"];
var FIB = [[0,"#7a8aa8"],[0.236,RED],[0.382,OR2],[0.5,GREEN],[0.618,"#1aa3a3"],[0.786,NAVY2],[1,"#7a8aa8"]];
var curColor = OR2, curW = 2, curLs = 0, magnet = true, lastPriceLine = null;
var shapes = [], pending = null, pendDown = null, selected = null, drag = null, meas = null, swallow = false;
var chartEl = $("chart");
var FONT = '700 11px "Nunito Sans","Segoe UI",sans-serif';

function hexA(h,a){ var n = parseInt(h.slice(1),16); return "rgba("+(n>>16)+","+((n>>8)&255)+","+(n&255)+","+a+")"; }
function X(i){ return chart.timeScale().logicalToCoordinate(i); }
function Y(p){ return candle.priceToCoordinate(p); }
function rr(c,x,y,w,h,r){ c.beginPath(); c.moveTo(x+r,y); c.arcTo(x+w,y,x+w,y+h,r); c.arcTo(x+w,y+h,x,y+h,r); c.arcTo(x,y+h,x,y,r); c.arcTo(x,y,x+w,y,r); c.closePath(); }
function pill(c,txt,cx,cy,bg,fg){
  c.font = '800 11px "Nunito Sans","Segoe UI",sans-serif';
  var w = c.measureText(txt).width + 16, h = 20, x = cx - w/2, y = cy - h/2;
  c.fillStyle = bg; rr(c,x,y,w,h,10); c.fill();
  c.fillStyle = fg; c.textBaseline = "middle"; c.textAlign = "center"; c.fillText(txt, cx, cy + 0.5); c.textAlign = "left";
}
function segDist(px,py,x1,y1,x2,y2,ray){
  var dx = x2-x1, dy = y2-y1, l2 = dx*dx+dy*dy;
  if (l2 === 0) return Math.hypot(px-x1, py-y1);
  var t = ((px-x1)*dx + (py-y1)*dy)/l2; t = Math.max(0, ray ? t : Math.min(1,t));
  return Math.hypot(px-(x1+t*dx), py-(y1+t*dy));
}
function pct(a,b){ return fP(b/a-1); }
function dateOf(i){ var D = S.D, k = Math.round(i); return (!D || k < 0 || k >= D.d.length) ? "" : fD(D.d[k]); }

function Shape(kind,a,b,color,w,ls){
  this.kind = kind; this.a = {i:a.i,p:a.p}; this.b = b ? {i:b.i,p:b.p} : {i:a.i,p:a.p};
  this.color = color || curColor; this.w = w || curW; this.ls = ls == null ? curLs : ls;
  this.sel = false; this.prev = false; this.req = null;
}
Shape.prototype.attached = function(a){ this.req = a.requestUpdate; };
Shape.prototype.detached = function(){ this.req = null; };
Shape.prototype.updateAllViews = function(){};
Shape.prototype.geom = function(){ return { x1:X(this.a.i), y1:Y(this.a.p), x2:X(this.b.i), y2:Y(this.b.p) }; };
Shape.prototype.handles = function(){
  var g = this.geom(), k = this.kind, h;
  if (k === "rect" || k === "ellipse"){
    var mx = (g.x1+g.x2)/2, my = (g.y1+g.y2)/2, x0 = Math.min(g.x1,g.x2), x9 = Math.max(g.x1,g.x2), y0 = Math.min(g.y1,g.y2), y9 = Math.max(g.y1,g.y2);
    h = [{id:"c0",x:g.x1,y:g.y1},{id:"c1",x:g.x2,y:g.y1},{id:"c2",x:g.x2,y:g.y2},{id:"c3",x:g.x1,y:g.y2},
         {id:"et",x:mx,y:y0,s:1},{id:"eb",x:mx,y:y9,s:1},{id:"el",x:x0,y:my,s:1},{id:"er",x:x9,y:my,s:1}];
  } else if (k === "hline"){ h = [{id:"a",x:g.x1,y:g.y1}]; }
  else if (k === "vline"){ h = [{id:"a",x:g.x1,y:chart.paneSize(0).height/2}]; }
  else h = [{id:"a",x:g.x1,y:g.y1},{id:"b",x:g.x2,y:g.y2},{id:"m",x:(g.x1+g.x2)/2,y:(g.y1+g.y2)/2,s:1}];
  return h.filter(function(q){ return q.x != null && q.y != null; });
};
Shape.prototype.rayEnd = function(g, W){
  var xe = g.x2 >= g.x1 ? W : 0, k = g.x2 === g.x1 ? 0 : (g.y2-g.y1)/(g.x2-g.x1);
  return { x:xe, y:g.y1 + k*(xe-g.x1) };
};
Shape.prototype.fibY = function(){
  var sh = this; return FIB.map(function(f){ var p = sh.b.p + (sh.a.p-sh.b.p)*f[0]; return { f:f[0], col:f[1], p:p, y:Y(p) }; });
};
Shape.prototype.hit = function(px,py,W){
  var g = this.geom(), k = this.kind, i, hs;
  if (this.sel){
    hs = this.handles();
    for (i=0;i<hs.length;i++) if (Math.hypot(px-hs[i].x, py-hs[i].y) <= (hs[i].s ? 8 : 10)) return hs[i].id === "m" ? "body" : hs[i].id;
  }
  if (k === "hline") return g.y1 != null && Math.abs(py-g.y1) <= 6 ? "body" : null;
  if (k === "vline") return g.x1 != null && Math.abs(px-g.x1) <= 6 ? "body" : null;
  if (g.x1 == null || g.y1 == null || g.x2 == null || g.y2 == null) return null;
  if (k === "trend" || k === "arrow") return segDist(px,py,g.x1,g.y1,g.x2,g.y2,false) <= 6 ? "body" : null;
  if (k === "ray"){ var e = this.rayEnd(g,W); return segDist(px,py,g.x1,g.y1,e.x,e.y,false) <= 6 ? "body" : null; }
  if (k === "fib"){
    if (segDist(px,py,g.x1,g.y1,g.x2,g.y2,false) <= 6) return "body";
    var xa = Math.min(g.x1,g.x2), xb = Math.max(g.x1,g.x2);
    if (px >= xa-6 && px <= xb+6){ var ys = this.fibY(); for (i=0;i<ys.length;i++) if (ys[i].y != null && Math.abs(py-ys[i].y) <= 6) return "body"; }
    return null;
  }
  if (k === "ellipse"){
    var cx = (g.x1+g.x2)/2, cy = (g.y1+g.y2)/2, rx = Math.abs(g.x2-g.x1)/2 || 1, ry = Math.abs(g.y2-g.y1)/2 || 1;
    var d = Math.hypot((px-cx)/rx, (py-cy)/ry);
    return (Math.abs(d-1)*Math.min(rx,ry) <= 6 || (this.sel && d <= 1)) ? "body" : null;
  }
  var x0 = Math.min(g.x1,g.x2), x9 = Math.max(g.x1,g.x2), y0 = Math.min(g.y1,g.y2), y9 = Math.max(g.y1,g.y2);
  if (!(px >= x0-6 && px <= x9+6 && py >= y0-6 && py <= y9+6)) return null;
  var edge = Math.min(Math.abs(px-x0), Math.abs(px-x9), Math.abs(py-y0), Math.abs(py-y9)) <= 6;
  return (edge || this.sel) ? "body" : null;
};
Shape.prototype.paint = function(c,W,H){
  var g = this.geom(), col = this.color, k = this.kind, lw = this.w + (this.sel ? 0.6 : 0), bars = Math.round(Math.abs(this.b.i - this.a.i));
  var da = this.ls === 1 ? [lw*4+2, lw*2+2] : (this.ls === 2 ? [0.1, lw*2+3] : []);
  if (this.prev && !da.length) da = [6,4];
  c.save(); c.lineJoin = "round"; c.lineCap = "round"; c.lineWidth = lw; c.strokeStyle = col; c.fillStyle = col; c.setLineDash(da);
  if (k === "hline"){
    if (g.y1 != null){ c.beginPath(); c.moveTo(0,g.y1); c.lineTo(W,g.y1); c.stroke(); }
  } else if (k === "vline"){
    if (g.x1 != null){ c.beginPath(); c.moveTo(g.x1,0); c.lineTo(g.x1,H); c.stroke(); }
  } else if (g.x1 != null && g.y1 != null && g.x2 != null && g.y2 != null){
    if (k === "measure"){
      var up = this.b.p >= this.a.p, mc = up ? GREEN : RED;
      var mx = Math.min(g.x1,g.x2), my = Math.min(g.y1,g.y2), mw = Math.abs(g.x2-g.x1), mh = Math.abs(g.y2-g.y1);
      c.fillStyle = hexA(mc,.12); c.fillRect(mx,my,mw,mh);
      c.strokeStyle = hexA(mc,.55); c.lineWidth = 1; c.setLineDash([4,4]); c.strokeRect(mx,my,mw,mh);
      c.setLineDash([]); c.strokeStyle = mc; c.lineWidth = 1.8;
      c.beginPath(); c.moveTo(g.x1,g.y1); c.lineTo(g.x2,g.y2); c.stroke();
      var dp = this.b.p - this.a.p, txt = pct(this.a.p,this.b.p)+"  ("+(dp>=0?"+":"−")+fN(Math.abs(dp),2)+")  ·  "+bars+" sesji";
      pill(c, txt, g.x2, g.y2 + (up ? -18 : 18), mc, "#fff");
    } else if (k === "rect"){
      var rx = Math.min(g.x1,g.x2), ry = Math.min(g.y1,g.y2), rw = Math.abs(g.x2-g.x1), rh = Math.abs(g.y2-g.y1);
      c.fillStyle = hexA(col, this.sel ? .2 : .13); c.fillRect(rx,ry,rw,rh); c.strokeRect(rx,ry,rw,rh);
    } else if (k === "ellipse"){
      c.beginPath(); c.ellipse((g.x1+g.x2)/2, (g.y1+g.y2)/2, Math.abs(g.x2-g.x1)/2, Math.abs(g.y2-g.y1)/2, 0, 0, 6.2832);
      c.fillStyle = hexA(col, this.sel ? .2 : .13); c.fill(); c.stroke();
    } else if (k === "fib"){
      var xa = Math.min(g.x1,g.x2), xb = Math.max(g.x1,g.x2); if (xb-xa < 4) xb = xa+4;
      var ys = this.fibY(), prevY = null; c.setLineDash([]);
      ys.forEach(function(f){
        if (f.y == null) return;
        if (prevY != null){ c.fillStyle = hexA(f.col,.07); c.fillRect(xa, Math.min(f.y,prevY), xb-xa, Math.abs(f.y-prevY)); }
        c.strokeStyle = f.col; c.lineWidth = this.sel ? 1.6 : 1.2; c.beginPath(); c.moveTo(xa,f.y); c.lineTo(xb,f.y); c.stroke();
        c.font = FONT; c.fillStyle = f.col; c.textBaseline = "bottom"; c.fillText(f.f + " (" + fN(f.p,2) + ")", xa+4, f.y-3);
        prevY = f.y;
      }, this);
      c.textBaseline = "alphabetic"; c.strokeStyle = "#7a8aa8"; c.lineWidth = 1; c.setLineDash([5,4]);
      c.beginPath(); c.moveTo(g.x1,g.y1); c.lineTo(g.x2,g.y2); c.stroke();
    } else {
      var e = k === "ray" ? this.rayEnd(g,W) : { x:g.x2, y:g.y2 };
      c.beginPath(); c.moveTo(g.x1,g.y1); c.lineTo(e.x,e.y); c.stroke();
      if (k === "arrow"){
        var an = Math.atan2(g.y2-g.y1, g.x2-g.x1), hl = 9 + lw*2;
        c.setLineDash([]); c.beginPath(); c.moveTo(g.x2,g.y2);
        c.lineTo(g.x2 - hl*Math.cos(an-0.42), g.y2 - hl*Math.sin(an-0.42));
        c.lineTo(g.x2 - hl*Math.cos(an+0.42), g.y2 - hl*Math.sin(an+0.42)); c.closePath(); c.fill();
      }
    }
  }
  c.setLineDash([]);
  if (this.sel || this.prev){
    this.handles().forEach(function(q){
      c.beginPath(); c.arc(q.x,q.y,q.s ? 3.8 : (this.sel ? 5.6 : 4.2),0,6.2832); c.fillStyle = "#fff"; c.fill();
      c.lineWidth = 2.2; c.strokeStyle = col; c.stroke();
    }, this);
  }
  c.restore();
};
Shape.prototype.paneViews = function(){
  var sh = this;
  return [{ zOrder:function(){ return "top"; }, renderer:function(){ return { draw:function(target){
    target.useMediaCoordinateSpace(function(s){ sh.paint(s.context, s.mediaSize.width, s.mediaSize.height); });
  } }; } }];
};
Shape.prototype.priceAxisViews = function(){
  var sh = this, ps = [];
  if (sh.kind === "hline") ps = [sh.a.p];
  else if (sh.sel && sh.kind !== "vline" && sh.kind !== "measure") ps = [sh.a.p, sh.b.p];
  return ps.map(function(p){ return {
    coordinate:function(){ var y = Y(p); return y == null ? -1000 : y; },
    text:function(){ return fN(p,2); }, textColor:function(){ return "#fff"; }, backColor:function(){ return sh.color; },
    visible:function(){ return Y(p) != null; }, tickVisible:function(){ return true; }
  }; });
};
Shape.prototype.timeAxisViews = function(){
  var sh = this, is = [];
  if (sh.kind === "vline") is = [sh.a.i];
  else if (sh.sel && sh.kind !== "hline" && sh.kind !== "measure") is = [sh.a.i, sh.b.i];
  return is.map(function(i){ return {
    coordinate:function(){ var x = X(i); return x == null ? -1000 : x; },
    text:function(){ return dateOf(i); }, textColor:function(){ return "#fff"; }, backColor:function(){ return sh.color; },
    visible:function(){ return X(i) != null && dateOf(i) !== ""; }
  }; });
};

function key(){ return "rv-draw3-" + S.tk; }
function saveShapes(){
  try { localStorage.setItem(key(), JSON.stringify(shapes.map(function(s){ return { k:s.kind, a:s.a, b:s.b, c:s.color, w:s.w, l:s.ls }; }))); } catch(e){}
}
function loadShapes(){
  clearShapes(false);
  try {
    var raw = localStorage.getItem(key()); if (!raw) return;
    JSON.parse(raw).forEach(function(o){ var s = new Shape(o.k, o.a, o.b, o.c, o.w, o.l); candle.attachPrimitive(s); shapes.push(s); });
  } catch(e){}
}
function clearShapes(persist){
  if (pending){ candle.detachPrimitive(pending); pending = null; pendDown = null; }
  if (meas){ candle.detachPrimitive(meas); meas = null; }
  shapes.forEach(function(s){ candle.detachPrimitive(s); });
  shapes = []; select(null); if (persist) saveShapes();
}
function select(s){
  if (selected) selected.sel = false;
  selected = s; if (s) s.sel = true;
  shapes.forEach(function(x){ x.req && x.req(); });
  buildFbar();
}
function removeShape(s){
  var k = shapes.indexOf(s); if (k < 0) return;
  shapes.splice(k,1); candle.detachPrimitive(s);
  if (selected === s) select(null);
  saveShapes();
}

/* współrzędne: indeks (logical) + cena; opcjonalny magnes */
function snapPrice(i,p,y){
  var D = S.D, k = Math.round(i); if (!D || k < 0 || k >= D.d.length) return p;
  var best = p, bd = 1e9;
  [D.o[k],D.h[k],D.l[k],D.c[k]].forEach(function(v){
    var vy = Y(v); if (vy == null) return; var d = Math.abs(vy-y); if (d < bd){ bd = d; best = v; }
  });
  return bd <= 14 ? best : p;
}
function toData(x,y,sn){
  var i = chart.timeScale().coordinateToLogical(x), p = candle.coordinateToPrice(y);
  if (i == null || p == null) return null;
  if (sn && magnet){ i = Math.round(i); p = snapPrice(i,p,y); }
  return { i:i, p:p };
}
function localXY(e){ var r = chartEl.getBoundingClientRect(); return { x:e.clientX-r.left, y:e.clientY-r.top }; }
function inPane(q){ var ps = chart.paneSize(0); return q.x >= 0 && q.y >= 0 && q.x <= ps.width && q.y <= ps.height; }
function lockChart(on){ chart.applyOptions({ handleScroll:!on, handleScale:!on }); }
function hitAny(q){
  var W = chart.paneSize(0).width, list = shapes.slice().reverse();
  if (selected){ list = [selected].concat(list.filter(function(x){ return x !== selected; })); }
  for (var i=0;i<list.length;i++){ var m = list[i].hit(q.x,q.y,W); if (m) return { sh:list[i], mode:m }; }
  return null;
}
function cursorFor(h){
  chartEl.classList.remove("c-pt","c-mv","c-draw");
  if (S.tool !== "cur"){ chartEl.classList.add("c-draw"); return; }
  if (!h) return;
  chartEl.classList.add(h.mode === "body" ? "c-mv" : "c-pt");
}

/* tworzenie: klik-klik albo przeciągnięcie */
function startShape(q){
  if (S.tool === "measure" && meas){ candle.detachPrimitive(meas); meas = null; }
  pending = new Shape(S.tool, q, q); pending.prev = true; candle.attachPrimitive(pending);
}
function endShape(q){
  var s = pending; pending = null; pendDown = null;
  s.b = { i:q.i, p:q.p }; s.prev = false;
  if (s.kind === "measure"){ meas = s; s.req && s.req(); return; }
  shapes.push(s); saveShapes(); setTool("cur"); select(s);
}

chartEl.addEventListener("pointerdown", function(e){
  if (e.button > 0) return;
  var q = localXY(e); if (!inPane(q)) return;
  if (S.tool !== "cur"){
    var d0 = toData(q.x,q.y,true); if (!d0) return;
    swallow = true; e.stopPropagation(); e.preventDefault();
    var t = S.tool;
    if (t === "hline" || t === "vline"){
      var s1 = new Shape(t,d0,d0); candle.attachPrimitive(s1); shapes.push(s1); saveShapes(); setTool("cur"); select(s1); return;
    }
    if (!pending){ startShape(d0); pendDown = { x:e.clientX, y:e.clientY, moved:false }; }
    else endShape(d0);
    return;
  }
  var h = hitAny(q);
  if (!h){ select(null); return; }
  select(h.sh);
  var d = toData(q.x,q.y,false); if (!d) return;
  drag = { sh:h.sh, mode:h.mode, start:d, a:{i:h.sh.a.i,p:h.sh.a.p}, b:{i:h.sh.b.i,p:h.sh.b.p} };
  swallow = true; lockChart(true); e.stopPropagation(); e.preventDefault();
}, true);
["mousedown","touchstart"].forEach(function(n){
  chartEl.addEventListener(n, function(e){ if (swallow) e.stopPropagation(); }, true);
});
window.addEventListener("pointermove", function(e){
  var q = localXY(e);
  if (pending){
    var dp0 = toData(q.x,q.y,true); if (dp0){ pending.b = { i:dp0.i, p:dp0.p }; pending.req && pending.req(); }
    if (pendDown && !pendDown.moved && Math.hypot(e.clientX-pendDown.x, e.clientY-pendDown.y) > 6) pendDown.moved = true;
  }
  if (!drag){
    if (!pending && S.tool === "cur") cursorFor(inPane(q) ? hitAny(q) : null);
    return;
  }
  var sh = drag.sh, m = drag.mode, raw = toData(q.x,q.y,false), cur = toData(q.x,q.y,true);
  if (!raw || !cur) return;
  if (m === "body"){
    var di = raw.i - drag.start.i, dp = raw.p - drag.start.p; if (magnet) di = Math.round(di);
    sh.a = { i:drag.a.i+di, p:drag.a.p+dp }; sh.b = { i:drag.b.i+di, p:drag.b.p+dp };
  } else if (m === "a"){
    if (sh.kind === "hline"){ sh.a = { i:sh.a.i, p:cur.p }; sh.b = { i:sh.a.i, p:cur.p }; }
    else if (sh.kind === "vline"){ sh.a = { i:cur.i, p:sh.a.p }; sh.b = { i:cur.i, p:sh.a.p }; }
    else sh.a = cur;
  }
  else if (m === "b"){ sh.b = cur; }
  else if (m === "et"){ if (sh.a.p >= sh.b.p) sh.a.p = cur.p; else sh.b.p = cur.p; }
  else if (m === "eb"){ if (sh.a.p < sh.b.p) sh.a.p = cur.p; else sh.b.p = cur.p; }
  else if (m === "el"){ if (sh.a.i <= sh.b.i) sh.a.i = cur.i; else sh.b.i = cur.i; }
  else if (m === "er"){ if (sh.a.i >= sh.b.i) sh.a.i = cur.i; else sh.b.i = cur.i; }
  else if (m.charAt(0) === "c"){
    var k = +m.charAt(1);
    if (k === 0 || k === 3) sh.a.i = cur.i; else sh.b.i = cur.i;
    if (k === 0 || k === 1) sh.a.p = cur.p; else sh.b.p = cur.p;
  }
  sh.req && sh.req();
});
window.addEventListener("pointerup", function(e){
  if (pending && pendDown){
    var moved = pendDown.moved; pendDown = null;
    if (moved){ var q = localXY(e), d = toData(q.x,q.y,true); endShape(d || pending.b); }
  }
  if (drag){ drag = null; lockChart(false); saveShapes(); }
  swallow = false;
});

function setTool(t){
  S.tool = t;
  if (pending){ candle.detachPrimitive(pending); pending = null; pendDown = null; }
  if (meas && t !== "measure"){ candle.detachPrimitive(meas); meas = null; }
  cursorFor(null); buildToolbar(); buildFbar();
}
document.addEventListener("keydown", function(e){
  var tg = e.target && e.target.tagName;
  if (tg === "INPUT" || tg === "TEXTAREA") return;
  if (e.key === "Escape"){ if (pending || S.tool !== "cur") setTool("cur"); else select(null); }
  else if ((e.key === "Delete" || e.key === "Backspace") && selected){ e.preventDefault(); removeShape(selected); }
});
function undo(){
  if (pending){ candle.detachPrimitive(pending); pending = null; pendDown = null; return; }
  if (meas){ candle.detachPrimitive(meas); meas = null; return; }
  var s = shapes[shapes.length-1]; if (s) removeShape(s);
}

/* ---------- lewy pasek narzędzi ---------- */
var ICON = {
  cur:'<path d="M5 3l6.5 17 2.5-7 7-2.5z"/>',
  trend:'<circle cx="5.5" cy="18.5" r="2"/><circle cx="18.5" cy="5.5" r="2"/><path d="M7 17L17 7"/>',
  ray:'<circle cx="5.5" cy="17.5" r="2"/><path d="M7.2 16.2L21 6"/>',
  arrow:'<path d="M5 19L19 5M10 5h9v9"/>',
  hline:'<path d="M3 12h18"/><circle cx="12" cy="12" r="2.2"/>',
  vline:'<path d="M12 3v18"/><circle cx="12" cy="12" r="2.2"/>',
  rect:'<rect x="4" y="6.5" width="16" height="11" rx="1"/>',
  ellipse:'<ellipse cx="12" cy="12" rx="8.5" ry="6"/>',
  fib:'<path d="M3 5h18M3 10h18M3 15h18M3 20h18"/>',
  measure:'<path d="M3.5 15.5l12-12 5 5-12 12z"/><path d="M8 11l2.2 2.2M11 8l2.2 2.2M5.8 13.2L7 14.4"/>',
  magnet:'<path d="M6 3v9a6 6 0 0012 0V3h-4v9a2 2 0 01-4 0V3z"/><path d="M6 7h4M14 7h4"/>',
  undo:'<path d="M9 5L4 10l5 5"/><path d="M4 10h10a6 6 0 010 12h-4"/>',
  trash:'<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>'
};
var TOOLS = [["cur","Kursor"],["trend","Linia trendu"],["ray","Promień"],["arrow","Strzałka"],["hline","Linia pozioma"],["vline","Linia pionowa"],["rect","Prostokąt"],["ellipse","Elipsa"],["fib","Fibonacci"],["measure","Miarka"]];
function mkBtn(icon,title,pressed){
  var b = document.createElement("button"); b.type = "button"; b.title = title; b.setAttribute("aria-label", title); b.setAttribute("aria-pressed", String(!!pressed));
  b.innerHTML = '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">'+icon+'</svg>';
  return b;
}
function buildToolbar(){
  var el = $("tb"); el.innerHTML = "";
  TOOLS.forEach(function(t){ var b = mkBtn(ICON[t[0]], t[1], S.tool === t[0]); b.onclick = function(){ setTool(t[0]); }; el.appendChild(b); });
  el.appendChild(document.createElement("hr"));
  var m = mkBtn(ICON.magnet, "Magnes (przyciąganie do świec)", magnet); m.onclick = function(){ magnet = !magnet; buildToolbar(); }; el.appendChild(m);
  var u = mkBtn(ICON.undo, "Cofnij (ostatni rysunek)", false); u.onclick = undo; el.appendChild(u);
  var c = mkBtn(ICON.trash, "Wyczyść wszystkie rysunki", false); c.onclick = function(){ clearShapes(true); }; el.appendChild(c);
}

/* ---------- pływający pasek stylu ---------- */
function setProp(k,v){
  if (k === "color") curColor = v; else if (k === "w") curW = v; else curLs = v;
  if (selected){ if (k === "color") selected.color = v; else if (k === "w") selected.w = v; else selected.ls = v; selected.req && selected.req(); saveShapes(); }
  buildFbar();
}
function buildFbar(){
  var el = $("fbar"), show = selected || (S.tool !== "cur" && S.tool !== "measure");
  el.style.display = show ? "flex" : "none"; if (!show) return;
  var cc = selected ? selected.color : curColor, cw = selected ? selected.w : curW, cl = selected ? selected.ls : curLs;
  el.innerHTML = "";
  var sws = document.createElement("span"); sws.className = "sws";
  COLORS.forEach(function(c){
    var b = document.createElement("button"); b.type = "button"; b.className = "sw"; b.style.background = c;
    b.setAttribute("aria-label", "Kolor " + c); b.setAttribute("aria-pressed", String(c === cc)); b.onclick = function(){ setProp("color", c); };
    sws.appendChild(b);
  });
  el.appendChild(sws);
  function group(items, cur, k){
    var g = document.createElement("div"); g.className = "seg";
    items.forEach(function(it){
      var b = document.createElement("button"); b.type = "button"; b.textContent = it[1]; b.setAttribute("aria-pressed", String(it[0] === cur));
      b.onclick = function(){ setProp(k, it[0]); }; g.appendChild(b);
    });
    el.appendChild(g);
  }
  group([[1,"1"],[2,"2"],[3,"3"],[4,"4"]], cw, "w");
  group([[0,"—"],[1,"╌"],[2,"···"]], cl, "l");
  if (selected){
    var d = document.createElement("button"); d.type = "button"; d.className = "pill"; d.textContent = "Usuń"; d.onclick = function(){ removeShape(selected); };
    el.appendChild(d);
  }
}
$("fs").onclick = function(){
  var c = $("card");
  if (document.fullscreenElement) document.exitFullscreen(); else if (c.requestFullscreen) c.requestFullscreen();
};
buildToolbar(); buildFbar();

/* ---------- tooltip ---------- */
var tip = $("tip"), RS=[], MC=null;
chart.subscribeCrosshairMove(function(param){
  if (drag || pending){ tip.classList.remove("on"); return; }
  if (!S.D || param.time == null || !param.point || param.point.x < 0){ tip.classList.remove("on"); return; }
  var i = S.idx[param.time]; if (i == null){ tip.classList.remove("on"); return; }
  var D = S.D, o = D.o[i], c = D.c[i], prev = i > 0 ? D.c[i-1] : o;
  var row = function(l, v, cls){ return '<div class="r"><span>'+l+'</span><b'+(cls?' class="'+cls+'"':'')+'>'+v+'</b></div>'; };
  tip.innerHTML = '<small>'+fD(D.d[i])+'</small>' +
    row("Otwarcie", fN(o,2)) + row("Maks.", fN(D.h[i],2)) + row("Min.", fN(D.l[i],2)) + row("Zamknięcie", fN(c,2)) +
    row("Zmiana", fP(c/prev-1), c>=prev ? "up2" : "dn2") + row("Wolumen", fN(D.v[i],0)) + row("RSI (14)", fN(RS[i],1)) + row("CMF (20)", fN(S.D.cmf[i],3));
  tip.classList.add("on");
  var w = $("chart").clientWidth, tw = tip.offsetWidth, lx = param.point.x + 16;
  if (lx + tw > w - 70) lx = param.point.x - tw - 16;
  tip.style.left = Math.max(0, lx) + "px";
});

/* ---------- panel sygnałów ---------- */
function loadPanel(tk){
  fetch("/api/signals?t=" + encodeURIComponent(tk))
    .then(function(r){ if (!r.ok) throw 0; return r.json(); })
    .then(function(d){
      if (d.error){
        $("sig-body").innerHTML =
          '<tr><td colspan="6">' + d.error + '</td></tr>';
        return;
      }
      var reko = d.rekomendacja;
      var cls = reko.indexOf('MOCNO KUPUJ') === 0 ? 'mk'
              : reko === 'KUPUJ' ? 'k'
              : reko === 'NEUTRALNIE' ? ''
              : reko === 'REDUKUJ' ? 'r' : 's';
      var el = $("panel-reko");
      el.textContent = reko;
      el.className = cls;
      $("panel-sum").innerHTML = 'Suma ważona: <b>'
        + (d.suma >= 0 ? '+' : '') + d.suma.toFixed(3) + '</b>';
      $("sig-body").innerHTML = d.wiersze.map(function(r){
        var bc = r.punkty >= 2 ? 'mk' : r.punkty >= 1 ? 'k'
               : r.punkty <= -2 ? 's' : r.punkty <= -1 ? 'r' : 'n';
        return '<tr>'
          + '<td class="grp">' + r.grupa + '</td>'
          + '<td class="ind">' + r.nazwa + '</td>'
          + '<td class="val">' + r.wartosc + '</td>'
          + '<td><span class="sig-badge sig-' + bc + '">'
          + r.sygnal + '</span></td>'
          + '<td class="val">' + (r.waga * 100).toFixed(1) + '%</td>'
          + '<td>' + (r.opis || '') + '</td>'
          + '</tr>';
      }).join('');
    })
    .catch(function(){
      $("sig-body").innerHTML =
        '<tr><td colspan="6">Błąd pobierania sygnałów</td></tr>';
    });
}

/* ---------- dane / widok ---------- */
function applyRange(){
  var n = S.D.d.length, cnt = S.rng === 0 ? n : Math.min(S.rng, n);
  chart.timeScale().setVisibleLogicalRange({ from:n - cnt - 0.5, to:n + 5 });
}
function render(){
  var D = S.D, n = D.d.length, T = D.d.map(ts), i;
  S.idx = {}; T.forEach(function(t,k){ S.idx[t] = k; });
  candle.setData(T.map(function(t,k){ return { time:t, open:D.o[k], high:D.h[k], low:D.l[k], close:D.c[k] }; }));
  area.setData(T.map(function(t,k){ return { time:t, value:D.c[k] }; }));
  vol.setData(T.map(function(t,k){ return { time:t, value:D.v[k], color: D.c[k] >= D.o[k] ? "rgba(31,138,76,.55)" : "rgba(201,59,59,.55)" }; }));
  MAS.forEach(function(m){
    var a = D["s" + m[1]], out = [];
    for (i=0;i<n;i++) if (a[i] != null) out.push({ time:T[i], value:a[i] });
    maS[m[0]].setData(out);
  });
  RS = rsi(D.c, 14);
  var r = []; for (i=14;i<n;i++) r.push({ time:T[i], value:RS[i] }); rsiS.setData(r);
  var M = macd(D.c), a1=[], a2=[], a3=[];
  for (i=33;i<n;i++){
    a1.push({ time:T[i], value:M.m[i] }); a2.push({ time:T[i], value:M.s[i] });
    a3.push({ time:T[i], value:M.h[i], color: M.h[i] >= 0 ? "rgba(31,138,76,.75)" : "rgba(201,59,59,.75)" });
  }
  mL.setData(a1); mS.setData(a2); mH.setData(a3);
  var cm = []; for (i=0;i<n;i++) if (D.cmf[i] != null) cm.push({ time:T[i], value:D.cmf[i] });
  cmfS.setData(cm);

  if (lastPriceLine) candle.removePriceLine(lastPriceLine);
  lastPriceLine = candle.createPriceLine({
    price:D.c[n-1], color:OR2, lineWidth:1, lineStyle:LW.LineStyle.Dashed,
    axisLabelVisible:true, axisLabelColor:OR2, axisLabelTextColor:"#fff", title:""
  });
  setPanes(); applyRange(); loadShapes(); header();
}
function header(){
  var D = S.D, n = D.d.length, last = D.c[n-1], prev = n > 1 ? D.c[n-2] : D.o[n-1];
  var cnt = S.rng === 0 ? n : Math.min(S.rng, n), base = D.c[Math.max(0, n - cnt)];
  var dCh = last/prev - 1, rCh = last/base - 1;
  var rl = RANGES.filter(function(r){ return r[0] === S.rng; })[0][1];
  $("qs").textContent = S.tk + " · GPW";
  $("px").textContent = fN(last, 2);
  var badge = function(v, l){ return '<span class="bd '+(v>=0?"up":"dn")+'">'+fP(v)+' <small>'+l+'</small></span>'; };
  $("badges").innerHTML = badge(dCh, "dziś") + badge(rCh, rl);
  var lo = Infinity, hi = -Infinity, st = Math.max(0, n-252);
  for (var i=st;i<n;i++){ if (D.l[i] < lo) lo = D.l[i]; if (D.h[i] > hi) hi = D.h[i]; }
  var cells = [["Otwarcie", fN(D.o[n-1],2)], ["Zakres dnia", fN(D.l[n-1],2)+" – "+fN(D.h[n-1],2)],
               ["52 tyg. min – max", fN(lo,2)+" – "+fN(hi,2)], ["Wolumen", fV(D.v[n-1])]];
  $("sstrip").innerHTML = cells.map(function(c){ return '<div><small>'+c[0]+'</small><b>'+c[1]+'</b></div>'; }).join("");
  $("note").textContent = "Dane z cache Yahoo Finance, bez znaczenia inwestycyjnego. Ostatnia sesja: " + fD(D.d[n-1]) + ".";
}
function load(tk){
  fetch("/api/data?t=" + encodeURIComponent(tk)).then(function(r){ if (!r.ok) throw 0; return r.json(); }).then(function(D){
    if (!D.d.length) throw 0;
    S.tk = tk; S.D = D; $("sym").value = tk; render();
    try { history.replaceState(null, "", "#" + tk); } catch(e){}
    loadPanel(tk);
  }).catch(function(){ $("sym").value = S.tk || ""; $("sym").animate([{transform:"translateX(-4px)"},{transform:"translateX(4px)"},{transform:"none"}],{duration:200}); });
}

/* ---------- UI ---------- */
function seg(id, items, cur, fn){
  var el = $(id); el.innerHTML = "";
  items.forEach(function(it){
    var b = document.createElement("button"); b.type = "button"; b.textContent = it[1];
    b.setAttribute("aria-pressed", String(it[0] === cur));
    b.onclick = function(){ fn(it[0]); };
    el.appendChild(b);
  });
}
function setView(v){
  S.view = v; candle.applyOptions({ visible: v === "cdl" }); area.applyOptions({ visible: v === "line" });
  seg("seg-view", VIEWS, v, setView);
}
function setRange(n){ S.rng = n; seg("seg-rng", RANGES, n, setRange); if (S.D){ applyRange(); header(); } }
function legend(){
  var el = $("lgd"); el.innerHTML = "";
  MAS.forEach(function(m){
    var b = document.createElement("button"); b.type = "button"; b.setAttribute("aria-pressed", String(S.ma[m[0]]));
    b.innerHTML = '<i style="background:'+m[2]+'"></i>'+m[3];
    b.onclick = function(){ S.ma[m[0]] = !S.ma[m[0]]; maS[m[0]].applyOptions({ visible:S.ma[m[0]] }); b.setAttribute("aria-pressed", String(S.ma[m[0]])); };
    el.appendChild(b);
  });
  var up = document.createElement("span"); up.innerHTML = '<span style="color:'+GREEN+'">●</span> wzrost &nbsp;<span style="color:'+RED+'">●</span> spadek';
  el.appendChild(up);
  var em = document.createElement("em"); em.textContent = "panele: wolumen, RSI, MACD, CMF"; el.appendChild(em);
}

(function init(){
  var st = document.createElement("style");
  st.textContent = ".qtip .up2{color:#7be3a6}.qtip .dn2{color:#ffa7a7}";
  document.head.appendChild(st);

  seg("seg-rng", RANGES, 252, setRange);
  seg("seg-view", VIEWS, "cdl", setView);
  legend();

  $("sym").addEventListener("change", function(){ var v = this.value.trim().toUpperCase(); if (v) load(v); });
  $("sym").addEventListener("focus", function(){ this.select(); });

  fetch("/api/tickers").then(function(r){ return r.json(); }).then(function(o){
    $("tickers").innerHTML = o.tickers.map(function(t){ return '<option value="'+t+'">'; }).join("");
    var h = location.hash.slice(1).toUpperCase();
    load(o.tickers.indexOf(h) >= 0 ? h : o.default);
  });
})();
})();
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype):
        data = body if isinstance(body, bytes) else body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        u = urlparse(self.path)
        try:
            if u.path == '/':
                self._send(200, HTML, 'text/html; charset=utf-8')
            elif u.path == '/api/tickers':
                dflt = DOMYSLNY if DOMYSLNY in tickery else (tickery[0] if tickery else '')
                self._send(200, json.dumps({'tickers': tickery, 'default': dflt}),
                           'application/json')
            elif u.path == '/api/data':
                tk = (parse_qs(u.query).get('t') or [''])[0].upper()
                if tk not in tickery:
                    self._send(404, '{"error":"unknown ticker"}', 'application/json')
                else:
                    self._send(200, json.dumps(dane_json(tk)), 'application/json')
            elif u.path == '/api/signals':
                tk = (parse_qs(u.query).get('t') or [''])[0].upper()
                if tk not in tickery:
                    self._send(404, '{"error":"unknown ticker"}', 'application/json')
                else:
                    try:
                        df = wczytaj(tk)
                        self._send(200, json.dumps(tabela_wskaznikow(tk, df)), 'application/json')
                    except Exception as e:
                        self._send(500, json.dumps({'error': str(e)}), 'application/json')
            else:
                self._send(404, 'Not found', 'text/plain')
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:  # noqa: BLE001
            self._send(500, json.dumps({'error': str(e)}), 'application/json')

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    if not tickery:
        print(f"Brak plików *.WA.csv.gz w {CACHE.resolve()}")
    url = f"http://127.0.0.1:{PORT}"
    print(f"Otwórz: {url}")
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    ThreadingHTTPServer(('0.0.0.0', PORT), Handler).serve_forever()