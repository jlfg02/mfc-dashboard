#!/usr/bin/env python3
"""Tres PDFs por partido, uno por destinatario (Mateo, Raúl, Gonzalo).
Uso: python3 tools/match_reports.py <match_log.csv> <textos.json> <carpeta_salida>
- CSV: exportación de MATCH_LOG (temporada MLS 25-26 + España 26-27).
- textos.json: textos de interpretación por destinatario (los escribe el analista cada semana).
Los números salen del CSV con el mismo criterio que el dashboard: todo por minuto jugado,
promedios ponderados por minutos, España = partidos desde 1-jul-2026 anteriores al partido."""
import csv, json, sys, asyncio, html, base64, pathlib
from playwright.async_api import async_playwright

CSV, TXT, OUTDIR = sys.argv[1:4]
T = json.load(open(TXT))
ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = pathlib.Path(OUTDIR); OUT.mkdir(parents=True, exist_ok=True)
G, A, R, N, NAVY = "#1a9e6b", "#d99a00", "#d64545", "#5b6b82", "#0d1b2e"
es = lambda v, d=1: "—" if v is None else f"{v:.{d}f}".replace(".", ",")
E = html.escape

rows = [r for r in csv.DictReader(open(CSV)) if r.get("Minutes Played")]
num = lambda r, k: float(r[k]) if r.get(k) not in ("", None) else None
cur = next(r for r in rows if r["Date"] == T["date"])
spain = [r for r in rows if "2026-07-01" <= r["Date"] < T["date"]]
mls = [r for r in rows if r["Date"] < "2026-07-01"]
prev = spain[-1] if spain else None
KEYS = {"td": "Total Distance (m)", "hid": "HID (m)", "hsr": "HSR (m)", "sprint": "Sprint Distance (m)",
        "sprints": "Sprints (#)", "acc": "Accelerations (#)", "dec": "Decelerations (#)"}
def per_min(r, k): return num(r, KEYS[k]) / num(r, "Minutes Played")
def wavg(rs, k): return sum(num(r, KEYS[k]) for r in rs) / sum(num(r, "Minutes Played") for r in rs)
def vmax_avg(rs): return sum(num(r, "Max Speed (m/s)") for r in rs) / len(rs) * 3.6
M = {k: {"hoy": per_min(cur, k), "prev": per_min(prev, k) if prev else None, "esp": wavg(spain, k), "mls": wavg(mls, k)} for k in KEYS}
M["vmax"] = {"hoy": num(cur, "Max Speed (m/s)") * 3.6, "prev": num(prev, "Max Speed (m/s)") * 3.6 if prev else None,
             "esp": vmax_avg(spain), "mls": vmax_avg(mls)}
best_esp_hid = max(per_min(r, "hid") for r in spain + [cur])
rec_vmax = max(num(r, "Max Speed (m/s)") for r in rows) * 3.6
def band(d): a = abs(d); return G if a <= 8 else A if a <= 20 else R

CSS = f"""@page {{ size: A4; margin: 10mm 11mm; }}
body {{ font-family: -apple-system, "Helvetica Neue", Arial, sans-serif; color:{NAVY}; font-size:11.5px; margin:0; line-height:1.4; }}
.hd {{ background:{NAVY}; color:#fff; border-radius:10px; padding:12px 16px; display:flex; justify-content:space-between; align-items:center; }}
.hd h1 {{ font-size:19px; margin:0 0 3px; }} .hd .sub {{ color:#9fb3cc; font-size:10.5px; }}
.res {{ text-align:right; }} .res .sc {{ font-size:26px; font-weight:800; color:#16b58f; }} .res .m {{ color:#9fb3cc; font-size:10px; }}
.verdict {{ margin:10px 0 8px; padding:10px 14px; background:#eef6f2; border-left:5px solid {A}; border-radius:6px; font-size:14px; font-weight:700; }}
h2 {{ font-size:10px; letter-spacing:1.5px; text-transform:uppercase; color:{N}; margin:12px 0 6px; }}
.cards {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; }}
.card {{ border:1px solid #dde3ea; border-radius:8px; padding:9px 11px; }} .card .q {{ font-weight:800; font-size:12px; margin-bottom:4px; }} .card .q:before {{ content:"“"; color:{A}; font-size:18px; margin-right:2px; }}
.ladder {{ position:relative; height:84px; margin:2px 14px 2px; }} .ladder .line {{ position:absolute; top:38px; left:0; right:0; height:6px; border-radius:3px; background:linear-gradient(90deg,#dfe5ec,#b9dccd); }}
.mk {{ position:absolute; top:0; height:84px; transform:translateX(-50%); text-align:center; font-size:9.5px; width:104px; }} .mk .dot {{ position:absolute; top:32px; left:45px; width:14px; height:14px; border-radius:7px; border:2px solid #fff; box-shadow:0 0 0 1px #9aa7b8; }}
.mk.top .lb {{ position:absolute; bottom:56px; left:0; right:0; line-height:1.2; }} .mk.bot .lb {{ position:absolute; top:52px; left:0; right:0; line-height:1.2; }}
.lad-t {{ font-weight:800; font-size:11.5px; margin-top:8px; }}
.two {{ display:grid; grid-template-columns:1fr 1fr; gap:12px; }}
.box {{ border-radius:8px; padding:9px 13px; margin-top:8px; }} .box h3 {{ margin:0 0 4px; font-size:12px; }}
.yes {{ background:#eef6f2; border:1px solid #bfe3d2; }} .no {{ background:#f4f5f7; border:1px solid #dde1e6; }} .warm {{ background:#fff7e6; border:1px solid #f3d38a; }} .cool {{ background:#eef2f8; border:1px solid #cdd7e6; }}
ul {{ margin:3px 0; padding-left:17px; }} li {{ margin:3px 0; }}
.pitches {{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }} .pc img {{ width:100%; border-radius:6px; display:block; }} .ph {{ font-weight:800; font-size:12px; margin-bottom:4px; }} .arrow {{ font-size:9px; color:{N}; margin:3px 0 4px; }}
.zb {{ display:grid; grid-template-columns:52px 1fr 34px; gap:6px; align-items:center; font-size:10px; margin:2px 0; }} .zbt {{ background:#f1f4f7; height:9px; border-radius:3px; }} .zbt div {{ height:9px; border-radius:3px; }}
.pn {{ font-size:10.5px; margin-top:5px; }}
table.t {{ border-collapse:collapse; width:100%; font-size:10.5px; }} .t td, .t th {{ border-bottom:1px solid #e3e8ee; padding:3px 6px; text-align:right; }} .t td:first-child, .t th:first-child {{ text-align:left; }} .t th {{ color:{N}; font-weight:600; font-size:9.5px; }}
.z {{ display:grid; grid-template-columns:20px 1fr 42px; gap:6px; align-items:center; margin:2px 0; font-size:10px; }} .zt {{ background:#f1f4f7; height:8px; border-radius:3px; }} .zt div {{ height:8px; border-radius:3px; }}
.light {{ display:inline-block; padding:3px 10px; border-radius:12px; color:#fff; font-weight:800; font-size:11px; }}
.ft {{ margin-top:10px; font-size:8.5px; color:{N}; display:flex; justify-content:space-between; }}
.pb {{ break-before:page; }}"""

def header(title, sub):
    return f'<div class="hd"><div><h1>{E(title)}</h1><div class="sub">{sub}</div></div><div class="res"><div class="sc">{T["score"]}</div><div class="m">{T["mins_txt"]}</div></div></div>'
def ul(xs): return "<ul>" + "".join(f"<li>{x}</li>" for x in xs) + "</ul>"
def footer(who): return f'<div class="ft"><span>Datos: GPS + pulsómetro StatSports · Análisis MFC · {who}</span><span>Dashboard completo: mateofavela.com</span></div>'

def ladder(title, pts, lo, hi):
    """Escala sin números: cada punto se coloca por su valor, pero solo se ve la etiqueta."""
    h = f'<div class="lad-t">{title}</div><div class="ladder"><div class="line"></div>'
    for i, (lab, v, col) in enumerate(sorted(pts, key=lambda p: p[1])):
        x = max(4, min(96, (v - lo) / (hi - lo) * 100))
        pos = "top" if i % 2 == 0 else "bot"
        h += f'<div class="mk {pos}" style="left:{x}%"><div class="lb">{lab}</div><div class="dot" style="background:{col}"></div></div>'
    return h + "</div>"

hm = next((x for x in json.load(open(ROOT / "heatmaps/heatmaps.json")) if x["date"] == T["date"]), None)
def pitches(notes):
    if not hm: return ""
    out = '<div class="pitches">'
    for hf in hm["halves"]:
        img = base64.b64encode((ROOT / hf["img"]).read_bytes()).decode()
        zb = "".join(f'<div class="zb"><span>{lab}</span><div class="zbt"><div style="width:{hf[k]}%;background:{c}"></div></div><b>{hf[k]}%</b></div>'
                     for lab, k, c in [("Ataque", "att", "#e8743b"), ("Medio", "mid", "#38bdf8"), ("Defensa", "def", "#5b8def")])
        out += (f'<div class="pc"><div class="ph">{hf["half"]}ª parte · {T["positions"][str(hf["half"])]}</div><img src="data:image/webp;base64,{img}">'
                f'<div class="arrow">{"Ataca hacia arriba ↑" if hf["half"] == 1 else "Ataca hacia abajo ↓"}</div>{zb}<div class="pn">{notes[str(hf["half"])]}</div></div>')
    return out + "</div>"

def comp_table():
    rows_ = [("Ritmo (m/min)", "td", 0), ("Corriendo fuerte, HID (m/min)", "hid", 1), ("Alta velocidad, HSR (m/min)", "hsr", 1),
             ("Sprint (m/min)", "sprint", 1), ("Sprints por min", "sprints", 2), ("Aceleraciones por min", "acc", 2),
             ("Frenadas por min", "dec", 2), ("Velocidad máxima (km/h)", "vmax", 1)]
    t = '<table class="t"><tr><th></th><th>Hoy</th><th>Anterior</th><th>Prom. España</th><th>vs España</th><th>Prom. MLS 25-26</th></tr>'
    for lab, k, d in rows_:
        m = M[k]; dd = (m["hoy"] - m["esp"]) / m["esp"] * 100
        t += f'<tr><td>{lab}</td><td><b>{es(m["hoy"], d)}</b></td><td>{es(m["prev"], d)}</td><td>{es(m["esp"], d)}</td><td style="color:{band(dd)};font-weight:800">{dd:+.0f}%</td><td>{es(m["mls"], d)}</td></tr>'
    return t + "</table>"

H = T.get("halves")
def halves_table():
    if not H: return ""
    mm = H["mins"]; t = '<table class="t"><tr><th>Por minuto</th><th>1ª parte</th><th>2ª parte</th><th>Cambio</th></tr>'
    for lab, k, d in [("Distancia (m/min)", "td", 0), ("Corriendo fuerte, HID", "hid", 1), ("Alta velocidad, HSR", "hsr", 1), ("Sprint (m)", "sprintDist", 1)]:
        a, b = H["h1"].get(k), H["h2"].get(k)
        if a is None or b is None: continue
        a, b = a / mm[0], b / mm[1]; dd = (b - a) / a * 100
        t += f'<tr><td>{lab}</td><td>{es(a, d)}</td><td>{es(b, d)}</td><td style="color:{band(dd)};font-weight:800">{dd:+.0f}%</td></tr>'
    return t + "</table>"

def zones():
    z = T["hr_zones"]; zmax = max(z); zc = ["#b8c2d0", "#5b8def", G, A, R]
    return "".join(f'<div class="z"><span>Z{i+1}</span><div class="zt"><div style="width:{v/zmax*100}%;background:{zc[i]}"></div></div><b>{v} min</b></div>' for i, v in enumerate(z))

# ───────── MATEO ─────────
TM = T["mateo"]
hid_pts = [("Tu partido medio en MLS", M["hid"]["mls"], "#9aa7b8"), ("Hoy", M["hid"]["hoy"], A),
           ("Tu partido medio en España", M["hid"]["esp"], G), ("Tu mejor partido en España", best_esp_hid, "#0f7a52")]
lo = min(p[1] for p in hid_pts) * 0.9; hi = max(p[1] for p in hid_pts) * 1.05
vm_pts = [("Tu velocidad punta media en MLS", M["vmax"]["mls"], "#9aa7b8"), ("Hoy", M["vmax"]["hoy"], A), ("Tu récord", rec_vmax, "#0f7a52")]
mateo = f"""{header("Tu partido vs " + T["opp"], T["sub"])}
<div class="verdict">{TM["verdict"]}</div>
<h2>Lo que sentiste y lo que dicen tus datos</h2>
<div class="cards">{"".join(f'<div class="card"><div class="q">{E(c[0])}</div>{c[1]}</div>' for c in TM["feelings"])}</div>
<h2>Dónde estás tú (sin números: cuanto más a la derecha, más)</h2>
{ladder("Cuánto corres fuerte por minuto", hid_pts, lo, hi)}
{ladder("Tu velocidad punta", vm_pts, min(p[1] for p in vm_pts) * 0.97, max(p[1] for p in vm_pts) * 1.02)}
<div class="box cool"><h3>Lo que te tiene que quedar</h3>{TM["anchor"]}</div>
<div class="two"><div class="box yes"><h3>Lo que tú controlas</h3>{ul(TM["control"])}</div><div class="box no"><h3>Lo que no controlas (y no te tiene que quitar energía)</h3>{ul(TM["nocontrol"])}</div></div>
{footer("Para Mateo")}
<div class="pb"></div>{header("Dónde jugaste", "Mapas de calor: rojo = donde más estuviste")}
<h2>Tus mapas por mitad</h2>{pitches(TM["pitch_notes"])}
<h2>Tu reto para el próximo partido</h2>
<div class="box warm">{ul(TM["challenge"])}</div>
<div class="box cool"><h3>Para terminar</h3>{TM["closing"]}</div>
{footer("Para Mateo")}"""

# ───────── RAÚL ─────────
TR = T["raul"]
raul = f"""{header("Mateo Favela · vs " + T["opp"], T["sub"])}
<div class="verdict">{TR["verdict"]}</div>
<div class="two"><div><h2>Estado para la semana</h2><span class="light" style="background:{TR["light_color"]}">{TR["light"]}</span><div style="margin-top:6px">{TR["status"]}</div></div>
<div><h2>Minutos y posición</h2>{TR["minutes"]}</div></div>
<h2>Su rendimiento por minuto: hoy, su promedio en España y en EE.UU.</h2>{comp_table()}
<div style="font-size:9px;color:{N};margin-top:2px">Verde ±8% · ámbar ±8-20% · rojo más de ±20% respecto a su promedio en España (partidos de la temporada, ponderado por minutos).</div>
<h2>Lectura táctica</h2>{ul(TR["tactical"])}
<div class="box cool"><h3>Cómo le podemos ayudar desde los datos</h3>{ul(TR["help"])}</div>
{footer("Para Raúl, entrenador")}
<div class="pb"></div>{header("Dónde jugó · vs " + T["opp"], "Mapas de calor por mitad (StatSports) y % de tiempo por tercio")}
{pitches(TR["pitch_notes"])}
<h2>1ª vs 2ª parte</h2>{halves_table()}
<div class="box warm"><h3>Lo que sintió Mateo</h3>{TR["emotional"]}</div>
{footer("Para Raúl, entrenador")}"""

# ───────── GONZALO ─────────
TG = T["gonzalo"]
gonzalo = f"""{header("Mateo Favela · vs " + T["opp"], T["sub"])}
<div class="verdict">{TG["verdict"]}</div>
<h2>Carga del partido (por minuto) vs su promedio en España y en EE.UU.</h2>{comp_table()}
<div class="two"><div><h2>Pulso: minutos por zona</h2>{zones()}<div style="font-size:9px;color:{N};margin-top:3px">{T["hr_note"]}</div></div>
<div><h2>1ª vs 2ª parte</h2>{halves_table()}</div></div>
<h2>Lectura física</h2>{ul(TG["physical"])}
<div class="box cool"><h3>Sugerencias para la semana (a tu criterio)</h3>{ul(TG["training"])}</div>
<div class="box warm"><h3>Aspecto emocional · para compartir con el psicólogo deportivo</h3>{TG["psych"]}</div>
{footer("Para Gonzalo, preparación física")}"""

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
        for name, body in [("Mateo", mateo), ("Raul", raul), ("Gonzalo", gonzalo)]:
            doc = f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>{body}</body></html>'
            pg = await b.new_page(); await pg.set_content(doc)
            out = OUT / f'MFC_{T["date"]}_{T["slug"]}_{name}.pdf'
            await pg.pdf(path=str(out), format="A4", print_background=True); print(out)
        await b.close()
asyncio.run(main())
print({k: {kk: round(v, 2) if v else v for kk, v in d.items()} for k, d in M.items()}, round(best_esp_hid, 1), round(rec_vmax, 1))
