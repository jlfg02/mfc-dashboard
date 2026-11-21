#!/usr/bin/env python3
"""PDF resumen de 1 página por partido (lo que sale del dashboard, para WhatsApp/correo).
Uso: python3 tools/match_pdf.py <match_log.csv> <textos.json> <salida.pdf>
El CSV es la exportación de MATCH_LOG; textos.json trae fecha, lectura y mensajes."""
import csv, json, sys, asyncio, html
from playwright.async_api import async_playwright
CSV, TXT, OUT = sys.argv[1:4]
T = json.load(open(TXT))
rows = [r for r in csv.DictReader(open(CSV)) if r["Date"] >= "2026-07-01" and r["Minutes Played"]]
f = lambda r, k: float(r[k]) if r.get(k, "") not in ("", None) else None
cur = next(r for r in rows if r["Date"] == T["date"])
prior = [r for r in rows if r["Date"] < T["date"]]
mins = lambda r: f(r, "Minutes Played")
def wavg(k):  # promedio ponderado por minutos (metros totales / minutos totales)
    return sum(f(r, k) for r in prior) / sum(mins(r) for r in prior)
m = mins(cur)
pm = lambda k: f(cur, k) / m
metrics = [  # etiqueta, hoy, promedio España, formato
    ("Ritmo (metros por minuto)", f(cur, "Total Distance (m)") / m, wavg("Total Distance (m)"), "{:.0f}"),
    ("Corriendo fuerte (HID, m/min)", pm("HID (m)"), wavg("HID (m)"), "{:.1f}"),
    ("Alta velocidad (HSR, m/min)", pm("HSR (m)"), wavg("HSR (m)"), "{:.1f}"),
    ("Metros de sprint por min", pm("Sprint Distance (m)"), wavg("Sprint Distance (m)"), "{:.1f}"),
    ("Sprints por minuto", pm("Sprints (#)"), wavg("Sprints (#)"), "{:.2f}"),
    ("Aceleraciones por min", pm("Accelerations (#)"), wavg("Accelerations (#)"), "{:.2f}"),
    ("Frenadas por min", pm("Decelerations (#)"), wavg("Decelerations (#)"), "{:.2f}"),
    ("Velocidad máxima (km/h)", f(cur, "Max Speed (m/s)") * 3.6, sum(f(r, "Max Speed (m/s)") for r in prior) / len(prior) * 3.6, "{:.1f}"),
]
es = lambda v, d: f"{v:.{d}f}".replace(".", ",")
G, A, R, N = "#1a9e6b", "#d99a00", "#d64545", "#5b6b82"
def band(d): a = abs(d); return G if a <= 8 else A if a <= 20 else R
bars = ""
for lab, v, av, fmt in metrics:
    d = (v - av) / av * 100; w = min(abs(d), 50) / 50 * 50
    left = 50 - w if d < 0 else 50
    bars += f'''<div class="row"><div class="lab">{lab}</div><div class="track"><div class="mid"></div>
<div class="bar" style="left:{left}%;width:{w}%;background:{band(d)}"></div></div>
<div class="val"><b>{fmt.format(v).replace(".",",")}</b> <span>vs {fmt.format(av).replace(".",",")}</span></div><div class="pct" style="color:{band(d)}">{d:+.0f}%</div></div>'''
# tendencia HID/min (todos los partidos de la temporada)
pts = [(r["Date"], f(r, "HID (m)") / mins(r), r["Opponent"]) for r in rows if r["Date"] <= T["date"]]
avg_all = sum(f(r, "HID (m)") for r in prior) / sum(mins(r) for r in prior)
W, H, lo, hi = 330, 120, 14, 26
xs = [20 + i * (W - 40) / (len(pts) - 1) for i in range(len(pts))]
ys = [H - 18 - (p[1] - lo) / (hi - lo) * (H - 36) for p in pts]
ya = H - 18 - (avg_all - lo) / (hi - lo) * (H - 36)
svg = f'<svg viewBox="0 0 {W} {H}" width="100%"><line x1="10" x2="{W-10}" y1="{ya}" y2="{ya}" stroke="{R}" stroke-dasharray="4 3"/><text x="12" y="{ya+11}" font-size="9" fill="{R}">promedio España {es(avg_all,1)}</text>'
svg += '<polyline fill="none" stroke="#0d1b2e" stroke-width="2" points="' + " ".join(f"{x:.0f},{y:.0f}" for x, y in zip(xs, ys)) + '"/>'
for i, (x, y) in enumerate(zip(xs, ys)):
    last = i == len(pts) - 1
    svg += f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{5 if last else 3}" fill="{band((pts[i][1]-avg_all)/avg_all*100) if last else "#0d1b2e"}"/>'
    svg += f'<text x="{x:.0f}" y="{y-8:.0f}" text-anchor="middle" font-size="9" fill="#0d1b2e">{es(pts[i][1],1)}</text>'
    d = pts[i][0][8:10] + "/" + pts[i][0][5:7]
    svg += f'<text x="{x:.0f}" y="{H-4}" text-anchor="middle" font-size="8" fill="{N}">{d}</text>'
svg += "</svg>"
z = T["hr_zones"]; zmax = max(z); zc = ["#b8c2d0", "#5b8def", G, A, R]
zones = "".join(f'<div class="z"><span>Z{i+1}</span><div class="zt"><div style="width:{v/zmax*100}%;background:{zc[i]}"></div></div><b>{v} min</b></div>' for i, v in enumerate(z))
tiles = "".join(f'<div class="tile" style="border-left-color:{ {"g":G,"a":A,"r":R}[c] }"><div class="tl">{html.escape(l)}</div><div class="tv" style="color:{ {"g":G,"a":A,"r":R}[c] }">{html.escape(v)}</div><div class="ts">{html.escape(s)}</div></div>' for l, v, s, c in T["tiles"])
li = lambda xs: "".join(f"<li>{x}</li>" for x in xs)
doc = f'''<!doctype html><html><head><meta charset="utf-8"><style>
@page {{ size: A4; margin: 10mm 11mm; }}
body {{ font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; color:#0d1b2e; font-size:11.5px; margin:0; }}
.hd {{ background:#0d1b2e; color:#fff; border-radius:10px; padding:12px 16px; display:flex; justify-content:space-between; align-items:center; }}
.hd h1 {{ font-size:19px; margin:0 0 3px; }} .hd .sub {{ color:#9fb3cc; font-size:10.5px; }}
.res {{ text-align:right; }} .res .sc {{ font-size:26px; font-weight:800; color:#16b58f; }} .res .m {{ color:#9fb3cc; font-size:10px; }}
.verdict {{ margin:10px 0 8px; padding:9px 13px; background:#eef6f2; border-left:5px solid {T["verdict_color"]}; border-radius:6px; font-size:13px; font-weight:700; }}
h2 {{ font-size:10px; letter-spacing:1.5px; text-transform:uppercase; color:{N}; margin:10px 0 5px; }}
.tiles {{ display:grid; grid-template-columns:repeat(3,1fr); gap:6px; }}
.tile {{ border:1px solid #dde3ea; border-left:5px solid; border-radius:6px; padding:5px 8px; }}
.tl {{ font-size:8.5px; text-transform:uppercase; color:{N}; letter-spacing:.5px; }} .tv {{ font-size:17px; font-weight:800; }} .ts {{ font-size:8.5px; color:{N}; }}
.row {{ display:grid; grid-template-columns:185px 1fr 92px 36px; align-items:center; gap:6px; margin:2px 0; }}
.track {{ position:relative; height:10px; background:#f1f4f7; border-radius:3px; }} .mid {{ position:absolute; left:50%; top:-2px; bottom:-2px; border-left:1.5px solid #0d1b2e; }}
.bar {{ position:absolute; top:1px; height:8px; border-radius:2px; }} .val span {{ color:{N}; font-size:9px; }} .pct {{ font-weight:800; text-align:right; }}
.cols {{ display:grid; grid-template-columns:1.15fr 1fr; gap:12px; }}
.z {{ display:grid; grid-template-columns:20px 1fr 42px; gap:6px; align-items:center; margin:2px 0; font-size:9.5px; }} .zt {{ background:#f1f4f7; height:8px; border-radius:3px; }} .zt div {{ height:8px; border-radius:3px; }}
ul {{ margin:3px 0; padding-left:16px; }} li {{ margin:2px 0; line-height:1.4; }}
.box {{ border-radius:8px; padding:8px 12px; margin-top:8px; }} .mateo {{ background:#fff7e6; border:1px solid #f3d38a; }} .staff {{ background:#eef2f8; border:1px solid #cdd7e6; }}
.box h3 {{ margin:0 0 3px; font-size:11.5px; }}
.ft {{ margin-top:8px; font-size:8.5px; color:{N}; display:flex; justify-content:space-between; }}
</style></head><body>
<div class="hd"><div><h1>Mateo Favela · vs {html.escape(T["opp"])}</h1><div class="sub">{T["sub"]}</div></div>
<div class="res"><div class="sc">{T["score"]}</div><div class="m">{T["mins_txt"]}</div></div></div>
<div class="verdict">{T["verdict"]}</div>
<h2>El partido en 6 señales</h2><div class="tiles">{tiles}</div>
<h2>Hoy vs su promedio en España (por minuto jugado)</h2>
{bars}
<div style="font-size:8.5px;color:{N};margin-top:2px">Barra = diferencia con su propio promedio de la temporada en España ({len(prior)} partidos, ponderado por minutos). Verde hasta ±8% · ámbar ±8-20% · rojo más de ±20%.</div>
<div class="cols"><div><h2>Tendencia: corriendo fuerte por minuto (HID)</h2>{svg}</div>
<div><h2>Pulso: minutos en cada zona (Z5 = al límite)</h2>{zones}<div style="font-size:8.5px;color:{N};margin-top:3px">{T["hr_note"]}</div></div></div>
<h2>Lectura</h2><ul>{li(T["reading"])}</ul>
<div class="box staff"><h3>{T["staff_title"]}</h3><ul>{li(T["staff"])}</ul></div>
<div class="box mateo"><h3>{T["mateo_title"]}</h3>{T["mateo"]}</div>
<div class="ft"><span>Datos: GPS + pulsómetro StatSports · Análisis MFC</span><span>Dashboard completo: mateofavela.com</span></div>
</body></html>'''
open(OUT.replace(".pdf", ".html"), "w").write(doc)
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        pg = await b.new_page(); await pg.set_content(doc); await pg.pdf(path=OUT, format="A4", print_background=True)
        await b.close()
asyncio.run(main())
print("ok", OUT)
