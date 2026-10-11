#!/usr/bin/env python3
"""Construye el dashboard autocontenido y el área técnica, y los cifra con StatiCrypt (AES-256).
Uso:  MFC_PASS='<clave>' python3 tools/build_encrypted.py <ruta_repo_mateofavela>
Salida: <repo>/dashboard.html y <repo>/at-9k2x7m4q.html (cifrados). La clave NUNCA se guarda en el repo."""
import base64, json, os, subprocess, sys, pathlib
root = pathlib.Path(__file__).resolve().parent.parent
out = pathlib.Path(sys.argv[1]); pw = os.environ["MFC_PASS"]
cfg = root/"tools/.staticrypt.json"          # solo contiene la sal (no secreta); misma sal => "recordar" sirve en ambas páginas
work = pathlib.Path("/tmp/mfc_plain"); work.mkdir(exist_ok=True)

html = (root/"index.html").read_text()
hm = json.loads((root/"heatmaps/heatmaps.json").read_text())
for it in hm:
    for h in it.get("halves", []):
        if h.get("img"):
            h["img"] = "data:image/webp;base64," + base64.b64encode((root/h["img"]).read_bytes()).decode()
dataurl = "data:application/json;base64," + base64.b64encode(json.dumps(hm).encode()).decode()
assert 'const HEATMAP_URL = "heatmaps/heatmaps.json";' in html
html = html.replace('const HEATMAP_URL = "heatmaps/heatmaps.json";', f'const HEATMAP_URL = "{dataurl}";')
html = html.replace('fetch(HEATMAP_URL + "?cb=" + Date.now())', 'fetch(HEATMAP_URL)')
(work/"dashboard.html").write_text(html)
(work/"at-9k2x7m4q.html").write_text((root/"tools/at-9k2x7m4q.src.html").read_text())

for f in ("dashboard.html", "at-9k2x7m4q.html"):
    subprocess.check_call(["/tmp/sc/node_modules/.bin/staticrypt",str(work/f),"-p",pw,"--short","-d",str(out),"-c",".staticrypt.json",
      "--remember","30","--template-title","Mateo Favela — acceso con código",
      "--template-instructions","Contenido privado. Introduce el código de acceso.",
      "--template-button","Entrar","--template-placeholder","Código",
      "--template-color-primary","#16b58f","--template-color-secondary","#0d1b2e",
      "--template-error","Código incorrecto","--template-remember","Recordar en este dispositivo"], cwd=str(root/"tools"))
    (work/f).unlink()
print("ok")
