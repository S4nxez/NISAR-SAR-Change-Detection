#!/usr/bin/env python3
"""
nisar_informe.py - Genera los informes de un par ya procesado por nisar_cambio.py.

Lee <carpeta>/cambio.json y escribe en la misma carpeta:
  informe.html   informe imprimible (se puede guardar como PDF desde el navegador)
  informe.md     el mismo contenido en Markdown
  zonas.geojson  contorno de cada zona con todos sus atributos (QGIS, geojson.io, Google Earth...)
  zonas.csv      tabla de zonas para Excel / pandas

Uso:
  python nisar_informe.py ../frontend/public/data/nisar/peru_oct2026_simulado
"""
import argparse
import csv
import html
import json
import math
import os

COLS_CSV = ["id", "clase", "nombre", "confianza", "area_km2", "perimetro_km", "compacidad", "cambio_dB",
            "cambio_max_dB", "dB_antes", "dB_despues", "pct_agua_antes", "pct_agua_despues",
            "cobertura_antes", "cobertura_despues", "lat", "lng"]
E = html.escape


def fnum(v, d=1, signo=False):
    if v is None:
        return "—"
    try:
        s = f"{v:+,.{d}f}" if signo else f"{v:,.{d}f}"
    except (TypeError, ValueError):
        return str(v)
    return s.replace(",", " ").replace(".", ",")


# ---------------------------------------------------------------- SVG
def svg_histograma(series, bordes, ancho=640, alto=220, lineas=(), titulo_x="dB"):
    """series: lista de (nombre, color, conteos, 'barra'|'linea'); bordes: [ini, fin, paso]."""
    ini, fin, paso = bordes
    n = len(series[0][2])
    ml, mr, mt, mb = 46, 12, 12, 34
    w, h = ancho - ml - mr, alto - mt - mb
    tot = [max(1, sum(s[2])) for s in series]
    vmax = max(max(c / t for c in s[2]) for s, t in zip(series, tot)) or 1
    X = lambda v: ml + (v - ini) / (fin - ini) * w  # noqa: E731
    Y = lambda f: mt + h - f / vmax * h  # noqa: E731
    p = [f'<svg viewBox="0 0 {ancho} {alto}" width="100%" role="img" xmlns="http://www.w3.org/2000/svg" '
         'style="font:11px system-ui,sans-serif">']
    for i in range(5):
        y = mt + h * i / 4
        p.append(f'<line x1="{ml}" x2="{ml + w}" y1="{y:.1f}" y2="{y:.1f}" stroke="#ddd"/>')
        p.append(f'<text x="{ml - 6}" y="{y + 4:.1f}" text-anchor="end" fill="#666">{fnum(100 * vmax * (4 - i) / 4, 1)} %</text>')
    salto = next(k for k in (0.5, 1, 2, 2.5, 5, 10, 20, 50) if k >= (fin - ini) / 8)
    v = math.ceil(ini / salto) * salto
    while v <= fin + 1e-9:
        p.append(f'<text x="{X(v):.1f}" y="{alto - 16}" text-anchor="middle" fill="#666">{fnum(v, 0)}</text>')
        v += salto
    p.append(f'<text x="{ml + w / 2:.1f}" y="{alto - 2}" text-anchor="middle" fill="#444">{E(titulo_x)}</text>')
    for (nombre, color, c, modo), t in zip(series, tot):
        if modo == "barra":
            for i, val in enumerate(c):
                x0 = X(ini + i * paso)
                p.append(f'<rect x="{x0 + .5:.1f}" y="{Y(val / t):.1f}" width="{max(.5, w / n - 1):.1f}" '
                         f'height="{mt + h - Y(val / t):.1f}" fill="{color}"/>')
        else:
            pts = " ".join(f"{X(ini + (i + .5) * paso):.1f},{Y(val / t):.1f}" for i, val in enumerate(c))
            p.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2"/>')
    for v, color, etiqueta in lineas:
        p.append(f'<line x1="{X(v):.1f}" x2="{X(v):.1f}" y1="{mt}" y2="{mt + h}" stroke="{color}" stroke-dasharray="4 3"/>')
        p.append(f'<text x="{X(v) + 3:.1f}" y="{mt + 10}" fill="{color}">{E(etiqueta)}</text>')
    yy = mt + 4
    for nombre, color, _, _ in series:
        p.append(f'<rect x="{ml + w - 110}" y="{yy}" width="10" height="10" fill="{color}"/>'
                 f'<text x="{ml + w - 95}" y="{yy + 9}" fill="#333">{E(nombre)}</text>')
        yy += 15
    p.append("</svg>")
    return "".join(p)


# ---------------------------------------------------------------- informe
def construir(r):
    e, par = r["estadisticas"], r["parametros"]
    clases, cob = r["clases"], r["coberturas"]
    U = par["umbral_dB"]
    cambio_km2 = sum(v["km2"] for v in e["por_clase"].values())
    kpis = [
        ("Área analizada", f"{fnum(e['area_valida_km2'], 0)} km²", "con datos válidos en las dos fechas"),
        ("Área con cambio", f"{fnum(cambio_km2, 1)} km²", f"{fnum(100 - e.get('estable_pct', 100), 2)} % del área, |Δ| > {U:g} dB"),
        ("Zonas de cambio", f"{e['zonas_total']}", f"de al menos {par['area_min_km2']:g} km²"),
        ("Días entre pasadas", f"{r['escena'].get('dias', '—')}", f"{r['antes']['fecha']} → {r['despues']['fecha']}"),
        ("Desplazamiento global", f"{fnum(par['desplazamiento_global_dB'], 2, True)} dB", "restado antes de clasificar"),
        ("Correlación", f"{fnum(e['correlacion'], 2)}", "1 = imágenes idénticas"),
        ("Agua", f"{fnum(e['agua']['antes_km2'], 1)} → {fnum(e['agua']['despues_km2'], 1)} km²",
         f"+{fnum(e['agua']['nueva_km2'], 1)} / −{fnum(e['agua']['perdida_km2'], 1)} km²"),
    ]
    ficha = [
        ("Sensor", r.get("sensor", "")),
        ("Pista / frame / órbita", f"{r.get('pista', '—')} / {r.get('frame', '—')} / {r.get('direccion', '—')}"),
        ("Mirada del radar", r["escena"].get("mirada") or "—"),
        ("Polarizaciones (antes / después)", f"{', '.join(r['escena'].get('polarizaciones_antes', [])) or '—'} / "
                                             f"{', '.join(r['escena'].get('polarizaciones_despues', [])) or '—'}"),
        ("Gránulo antes", r["antes"].get("granulo") or "—"),
        ("Gránulo después", r["despues"].get("granulo") or "—"),
        ("Píxel / proyección", f"{r['escena'].get('pixel_m', 20):g} m / EPSG:{r['escena'].get('epsg', '—')}"),
        ("Extensión (lat, lon)", f"{r['bounds'][0][0]:.4f}, {r['bounds'][0][1]:.4f} — {r['bounds'][1][0]:.4f}, {r['bounds'][1][1]:.4f}"),
        ("Generado", r.get("generado", "")),
    ]
    return kpis, ficha, cambio_km2


def informe_html(r, carpeta):
    e, par = r["estadisticas"], r["parametros"]
    clases, cob = r["clases"], r["coberturas"]
    U = par["umbral_dB"]
    kpis, ficha, _ = construir(r)
    img = r["imagenes"]
    orden_cob = e["coberturas"]["orden"]
    M = e["coberturas"]["matriz_km2"]
    mmax = max(max(f) for f in M) or 1
    hc = e["histograma_cambio"]
    zonas = r["zonas"]

    h = []
    a = h.append
    a("<!doctype html><html lang='es'><head><meta charset='utf-8'>")
    a("<meta name='viewport' content='width=device-width,initial-scale=1'>")
    a(f"<title>Informe de cambios NISAR · {E(r['titulo'])}</title>")
    a("""<style>
:root{--t:#16212b;--m:#5a6773;--l:#e3e8ec;--a:#c8932f}
*{box-sizing:border-box}body{margin:0;font:14px/1.55 system-ui,-apple-system,Segoe UI,sans-serif;color:var(--t);background:#fff}
main{max-width:1000px;margin:0 auto;padding:32px 24px 64px}
h1{font-size:28px;margin:4px 0 6px;line-height:1.2}h2{font-size:19px;margin:34px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--t)}
h3{font-size:15px;margin:18px 0 6px}.eyebrow{font-size:11px;letter-spacing:.12em;color:var(--a);font-weight:700;text-transform:uppercase}
.sub{color:var(--m)}.aviso{background:#fff5e0;border-left:4px solid var(--a);padding:10px 14px;margin:14px 0}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px;margin:16px 0}
.kpi{border:1px solid var(--l);border-radius:8px;padding:10px 12px}.kpi b{display:block;font-size:20px}.kpi span{font-size:11px;color:var(--m)}
.kpi small{display:block;font-size:11px;color:var(--m);text-transform:uppercase;letter-spacing:.06em}
table{border-collapse:collapse;width:100%;margin:8px 0;font-size:13px}th,td{border-bottom:1px solid var(--l);padding:5px 7px;text-align:left;vertical-align:top}
th{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--m)}td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.sw{display:inline-block;width:11px;height:11px;border-radius:2px;margin-right:6px;vertical-align:-1px;border:1px solid #0002}
.imgs{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}.imgs figure{margin:0}
.imgs img,.stack{width:100%;display:block;background:#111;border-radius:6px}.stack{position:relative}.stack img{position:absolute;inset:0;width:100%;height:100%}
.stack img:first-child{position:relative}figcaption{font-size:12px;color:var(--m);margin-top:4px}
.zona{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin:6px 0 16px}.zona img{width:100%;border-radius:4px;background:#111}
.matriz td{text-align:right}.matriz td.h{font-weight:600}.pie{font-size:12px;color:var(--m);margin-top:40px;border-top:1px solid var(--l);padding-top:10px}
.links a{margin-right:14px}
@media print{main{padding:0}h2{break-after:avoid}.zona,.imgs,table,svg{break-inside:avoid}.noprint{display:none}}
</style></head><body><main>""")
    a("<p class='eyebrow'>NASA Space Apps 2026 · NISAR · Informe de cambios</p>")
    a(f"<h1>{E(r['titulo'])}</h1>")
    a(f"<p class='sub'>{E(r['antes']['fecha'])} → {E(r['despues']['fecha'])} · pista {E(str(r.get('pista')))}, "
      f"frame {E(str(r.get('frame')))} · umbral ±{U:g} dB · agua &lt; {par['agua_dB']:g} dB</p>")
    a("<p class='noprint links'><a href='#' onclick='window.print();return false'>Imprimir / guardar como PDF</a>"
      "<a href='zonas.geojson' download>zonas.geojson</a><a href='zonas.csv' download>zonas.csv</a>"
      "<a href='informe.md' download>informe.md</a><a href='cambio.json' download>cambio.json</a></p>")
    if r.get("simulado") or r.get("nota"):
        a(f"<div class='aviso'><b>Aviso.</b> {E(r.get('nota') or 'La segunda fecha es simulada.')}</div>")

    a("<h2>1. Resumen</h2>")
    for t in r.get("resumen_texto", []):
        a(f"<p>{E(t)}</p>")
    a("<div class='kpis'>" + "".join(f"<div class='kpi'><small>{E(k)}</small><b>{E(v)}</b><span>{E(s)}</span></div>"
                                     for k, v, s in kpis) + "</div>")

    a("<h2>2. Imágenes</h2><div class='imgs'>")
    a(f"<figure><img src='{img['antes']}' alt='antes'><figcaption>Antes ({E(r['antes']['fecha'])}). Radar HH, gris de "
      f"{img['escala_gris_dB']['vmin']:g} a {img['escala_gris_dB']['vmax']:g} dB.</figcaption></figure>")
    a(f"<figure><img src='{img['despues']}' alt='después'><figcaption>Después ({E(r['despues']['fecha'])}), misma escala de gris.</figcaption></figure>")
    a(f"<figure><div class='stack'><img src='{img['antes']}' alt=''><img src='{img['cambio']}' alt='cambio'></div>"
      "<figcaption>Clases de cambio sobre la imagen de antes.</figcaption></figure>")
    a(f"<figure><img src='{img['diferencia']}' alt='diferencia'><figcaption>Diferencia en dB: azul = baja, rojo = sube.</figcaption></figure>")
    if img.get("densidad"):
        a(f"<figure><div class='stack'><img src='{img['antes']}' alt=''><img src='{img['densidad']}' alt='densidad'></div>"
          f"<figcaption>Densidad de cambio (% de píxeles que cambian en celdas de {img['resolucion_m'].get('densidad', 320):g} m).</figcaption></figure>")
    a("</div>")

    a("<h2>3. Cambios por clase</h2><table><tr><th>Clase</th><th class='n'>km²</th><th class='n'>% del área</th>"
      "<th class='n'>Zonas</th><th class='n'>km² en zonas</th><th>Lectura posible</th></tr>")
    for k, c in clases.items():
        v = e["por_clase"][k]
        a(f"<tr><td><span class='sw' style='background:{c['color']}'></span>{E(c['nombre'])}</td><td class='n'>{fnum(v['km2'], 2)}</td>"
          f"<td class='n'>{fnum(v['pct'], 3)}</td><td class='n'>{e['zonas_por_clase'][k]}</td>"
          f"<td class='n'>{fnum(e['zonas_km2_por_clase'][k], 2)}</td><td>{E(c['lectura'])}</td></tr>")
    a("</table>")
    a(svg_histograma([("Píxeles", "#7d8b97", hc["conteos"], "barra")], hc["bordes_dB"],
                     lineas=[(-U, "#e47759", f"−{U:g} dB"), (U, "#68b6a3", f"+{U:g} dB")], titulo_x="cambio de brillo (dB)"))
    c = e["cambio"]
    a(f"<p class='sub'>Cambio medio {fnum(c['media_dB'], 2, True)} dB, desviación {fnum(c['desviacion_dB'], 2)} dB. "
      f"La mitad de los píxeles cambia menos de {fnum(c['p50_abs_dB'], 1)} dB, el 90 % menos de {fnum(c['p90_abs_dB'], 1)} dB "
      f"y el 99 % menos de {fnum(c['p99_abs_dB'], 1)} dB.</p>")

    a("<h2>4. Brillo de cada fecha y coberturas radar</h2>")
    ha, hd = e["histograma_antes"], e["histograma_despues"]
    a(svg_histograma([("Antes", "#4a90c2", ha["conteos"], "linea"), ("Después", "#e4893f", hd["conteos"], "linea")],
                     ha["bordes_dB"], lineas=[(par["agua_dB"], "#3d8bff", "agua")], titulo_x="brillo radar HH (dB)"))
    b = e["brillo"]
    a(f"<p class='sub'>Mediana antes {fnum(b['mediana_antes_dB'], 1)} dB, después {fnum(b['mediana_despues_dB'], 1)} dB. "
      "Lectura aproximada del brillo (no es un mapa de usos del suelo):</p>")
    a("<table class='matriz'><tr><th>Antes ↓ / Después →</th>" + "".join(f"<th class='n'>{E(cob[k]['nombre'])}</th>" for k in orden_cob)
      + "<th class='n'>Total antes</th></tr>")
    for i, k in enumerate(orden_cob):
        celdas = "".join(f"<td style='background:rgba(200,147,47,{0.08 + 0.6 * M[i][j] / mmax:.2f})' "
                         f"class='{'h' if i == j else ''}'>{fnum(M[i][j], 1)}</td>" for j in range(4))
        a(f"<tr><th><span class='sw' style='background:{cob[k]['color']}'></span>{E(cob[k]['nombre'])}</th>{celdas}"
          f"<td class='n'>{fnum(e['coberturas']['antes_km2'][i], 1)}</td></tr>")
    a("<tr><th>Total después</th>" + "".join(f"<td>{fnum(v, 1)}</td>" for v in e["coberturas"]["despues_km2"]) + "<td></td></tr></table>")
    a("<table>" + "".join(f"<tr><td><span class='sw' style='background:{cob[k]['color']}'></span>{E(cob[k]['nombre'])}</td>"
                          f"<td>{E(cob[k]['lectura'])}</td></tr>" for k in orden_cob) + "</table>")
    w = e["agua"]
    a(f"<h3>Balance de agua</h3><p>Agua antes {fnum(w['antes_km2'], 1)} km², después {fnum(w['despues_km2'], 1)} km². "
      f"Se mantiene {fnum(w['estable_km2'], 1)} km², aparece {fnum(w['nueva_km2'], 1)} km² y desaparece {fnum(w['perdida_km2'], 1)} km².</p>")

    a(f"<h2>5. Zonas de cambio ({e['zonas_total']})</h2>")
    a("<table><tr><th>Zona</th><th>Clase</th><th class='n'>km²</th><th class='n'>Δ medio</th><th class='n'>Δ extremo</th>"
      "<th class='n'>dB antes → después</th><th class='n'>% agua antes → después</th><th>Cobertura</th><th>Confianza</th><th>Lat, lon</th></tr>")
    for z in zonas[:40]:
        col = clases[z["clase"]]["color"]
        a(f"<tr><td>{z['id']}</td><td><span class='sw' style='background:{col}'></span>{E(z['nombre'])}</td>"
          f"<td class='n'>{fnum(z['area_km2'], 2)}</td><td class='n'>{fnum(z['cambio_dB'], 1, True)}</td>"
          f"<td class='n'>{fnum(z.get('cambio_max_dB'), 1, True)}</td>"
          f"<td class='n'>{fnum(z.get('dB_antes'), 1)} → {fnum(z.get('dB_despues'), 1)}</td>"
          f"<td class='n'>{fnum(z.get('pct_agua_antes'), 0)} → {fnum(z.get('pct_agua_despues'), 0)}</td>"
          f"<td>{E(cob.get(z.get('cobertura_antes'), {}).get('nombre', '—'))} → {E(cob.get(z.get('cobertura_despues'), {}).get('nombre', '—'))}</td>"
          f"<td>{E(z.get('confianza', '—'))}</td>"
          f"<td><a href='https://www.google.com/maps/@{z['lat']},{z['lng']},4000m/data=!3m1!1e3' target='_blank' rel='noopener'>"
          f"{z['lat']:.4f}, {z['lng']:.4f}</a></td></tr>")
    a("</table>")
    if len(zonas) > 40:
        a(f"<p class='sub'>Se muestran 40 de {len(zonas)} zonas listadas. Todas están en zonas.csv y zonas.geojson.</p>")
    con_recorte = [z for z in zonas if z.get("recorte")]
    if con_recorte:
        a("<h3>Fichas de las zonas mayores (recortes a 20 m)</h3>")
        for z in con_recorte:
            a(f"<p><b>{z['id']} · {E(z['nombre'])}</b> — {fnum(z['area_km2'], 2)} km², Δ {fnum(z['cambio_dB'], 1, True)} dB, "
              f"confianza {E(z.get('confianza', '—'))}. Recorte de {z['recorte']['lado_km']:g} km.</p>")
            a(f"<div class='zona'><figure><img src='zonas/{z['id']}_antes.webp' alt=''><figcaption>Antes</figcaption></figure>"
              f"<figure><img src='zonas/{z['id']}_despues.webp' alt=''><figcaption>Después</figcaption></figure>"
              f"<figure><div class='stack'><img src='zonas/{z['id']}_antes.webp' alt=''><img src='zonas/{z['id']}_cambio.png' alt=''></div>"
              "<figcaption>Cambio</figcaption></figure></div>")

    a("<h2>6. Escena y método</h2><table>" + "".join(f"<tr><th>{E(k)}</th><td>{E(str(v))}</td></tr>" for k, v in ficha) + "</table>")
    a(f"""<ol>
<li><b>Filtro de speckle</b>: media {par.get('filtro_px', 5)}×{par.get('filtro_px', 5)} en potencia lineal (unos 100 m), para quitar el granulado típico del radar.</li>
<li><b>Diferencia</b> píxel a píxel en dB: después − antes.</li>
<li><b>Desplazamiento global</b> ({fnum(par['desplazamiento_global_dB'], 2, True)} dB): la mediana de la diferencia se resta, porque un cambio de humedad o calibración afecta a toda la escena y no es un cambio local.</li>
<li><b>Clases</b>: |Δ| &gt; {U:g} dB. «Agua nueva» y «agua que desaparece» exigen además cruzar el umbral de agua ({par['agua_dB']:g} dB).</li>
<li><b>Zonas</b>: clase dominante en bloques de {img['resolucion_m'].get('cambio', 80):g} m, agrupada en manchas conexas de al menos {par['area_min_km2']:g} km².</li>
<li><b>Confianza</b>: alta si el área ≥ 0,5 km² y |Δ| ≥ {2 * U:g} dB; media si el área ≥ 0,1 km² y |Δ| ≥ {1.25 * U:g} dB; baja en el resto.</li>
</ol>
<h3>Límites</h3><ul>
<li>Solo polarización HH. HV ayudaría a separar vegetación de suelo.</li>
<li>Umbrales fijos: el de agua falla en desiertos y en agua con viento.</li>
<li>Sin corrección de pendiente ni sombra: en montaña aparecen falsos cambios.</li>
<li>Las imágenes se colocan en el mapa con su rectángulo lat/lon, sin reproyectar (error de pocos píxeles).</li>
<li>Un cambio de radar es una señal, no una prueba: hay que contrastarlo con imagen óptica o sobre el terreno.</li></ul>""")
    a("<p class='pie'>Generado con processing/nisar_informe.py · Datos NISAR: NASA/ISRO vía ASF DAAC · Prototipo, no es un sistema de alerta operativo.</p>")
    a("</main></body></html>")
    return "".join(h)


def informe_md(r):
    e, par = r["estadisticas"], r["parametros"]
    clases, cob = r["clases"], r["coberturas"]
    kpis, ficha, _ = construir(r)
    L = [f"# Informe de cambios NISAR · {r['titulo']}", "",
         f"{r['antes']['fecha']} → {r['despues']['fecha']} · umbral ±{par['umbral_dB']:g} dB · agua < {par['agua_dB']:g} dB", ""]
    if r.get("simulado") or r.get("nota"):
        L += [f"> **Aviso.** {r.get('nota') or 'La segunda fecha es simulada.'}", ""]
    L += ["## Resumen", ""] + [t + "\n" for t in r.get("resumen_texto", [])]
    L += ["| Indicador | Valor | Detalle |", "|---|---|---|"] + [f"| {k} | {v} | {s} |" for k, v, s in kpis] + [""]
    L += ["## Cambios por clase", "", "| Clase | km² | % | Zonas | km² en zonas | Lectura |", "|---|--:|--:|--:|--:|---|"]
    for k, c in clases.items():
        v = e["por_clase"][k]
        L.append(f"| {c['nombre']} | {fnum(v['km2'], 2)} | {fnum(v['pct'], 3)} | {e['zonas_por_clase'][k]} | "
                 f"{fnum(e['zonas_km2_por_clase'][k], 2)} | {c['lectura']} |")
    orden = e["coberturas"]["orden"]
    L += ["", "## Coberturas radar (km², antes en filas, después en columnas)", "",
          "| | " + " | ".join(cob[k]["nombre"] for k in orden) + " |", "|---|" + "--:|" * 4]
    for i, k in enumerate(orden):
        L.append(f"| {cob[k]['nombre']} | " + " | ".join(fnum(v, 1) for v in e["coberturas"]["matriz_km2"][i]) + " |")
    w = e["agua"]
    L += ["", f"Agua: {fnum(w['antes_km2'], 1)} → {fnum(w['despues_km2'], 1)} km² "
              f"(aparece {fnum(w['nueva_km2'], 1)}, desaparece {fnum(w['perdida_km2'], 1)}).", ""]
    L += [f"## Zonas ({e['zonas_total']})", "",
          "| Zona | Clase | km² | Δ dB | dB antes → después | Confianza | Lat, lon |", "|---|---|--:|--:|--:|---|---|"]
    for z in r["zonas"][:40]:
        L.append(f"| {z['id']} | {z['nombre']} | {fnum(z['area_km2'], 2)} | {fnum(z['cambio_dB'], 1, True)} | "
                 f"{fnum(z.get('dB_antes'), 1)} → {fnum(z.get('dB_despues'), 1)} | {z.get('confianza', '—')} | {z['lat']:.4f}, {z['lng']:.4f} |")
    L += ["", "## Escena", ""] + [f"- **{k}:** {v}" for k, v in ficha] + [""]
    return "\n".join(L)


def geojson(r):
    feats = []
    for z in r["zonas"]:
        props = {k: z.get(k) for k in COLS_CSV}
        props["color"] = r["clases"][z["clase"]]["color"]
        if z.get("contorno"):
            polis = [[[[p[1], p[0]] for p in anillo] + [[anillo[0][1], anillo[0][0]]] for anillo in poli] for poli in z["contorno"]]
            geom = {"type": "MultiPolygon", "coordinates": polis}
        elif z.get("poligono"):
            ring = [[p[1], p[0]] for p in z["poligono"]]
            ring.append(ring[0])
            geom = {"type": "Polygon", "coordinates": [ring]}
        else:
            geom = {"type": "Point", "coordinates": [z["lng"], z["lat"]]}
        feats.append({"type": "Feature", "properties": props, "geometry": geom})
    return {"type": "FeatureCollection", "name": r["id"],
            "metadata": {"antes": r["antes"]["fecha"], "despues": r["despues"]["fecha"], "parametros": r["parametros"]},
            "features": feats}


def generar(carpeta):
    with open(os.path.join(carpeta, "cambio.json"), encoding="utf-8") as fh:
        r = json.load(fh)
    with open(os.path.join(carpeta, "informe.html"), "w", encoding="utf-8") as fh:
        fh.write(informe_html(r, carpeta))
    with open(os.path.join(carpeta, "informe.md"), "w", encoding="utf-8") as fh:
        fh.write(informe_md(r))
    with open(os.path.join(carpeta, "zonas.geojson"), "w", encoding="utf-8") as fh:
        json.dump(geojson(r), fh, ensure_ascii=False)
    with open(os.path.join(carpeta, "zonas.csv"), "w", encoding="utf-8-sig", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=COLS_CSV, extrasaction="ignore", delimiter=";")
        wr.writeheader()
        for z in r["zonas"]:
            wr.writerow(z)
    print(f"OK -> informes en {carpeta}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("carpetas", nargs="+", help="carpetas con cambio.json")
    for c in ap.parse_args().carpetas:
        generar(c)


if __name__ == "__main__":
    main()
