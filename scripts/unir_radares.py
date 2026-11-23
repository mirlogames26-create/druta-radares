# -*- coding: utf-8 -*-
"""
Une todas las fuentes de radares en android/app/src/main/assets/radares.json:
  1. los que ya tenia la app (OSM sobre nuestros ejes, con el sentido de su calzada: build_radares_osm.py,
     sentido_radares.py y export_radares.py), que se guardan en radares/base_ejes.json la primera vez;
  2. el inventario oficial de la DGT (dgt/radares_dgt.xml -> dgt/leer_dgt.py -> dgt/dgt.json; CC BY, NAP DGT):
     radares fijos y de tramo de las carreteras que gestiona (no Cataluna ni Pais Vasco, ni los urbanos);
  3. todos los de OpenStreetMap de Espana y Portugal (osm_todos.json: velocidad y tramo; osm_semaforos.json:
     camaras de semaforo en rojo), tambien los de los nucleos urbanos, que son de los ayuntamientos.
  4. los avisos de los usuarios YA COMPROBADOS (formulario de opiniones de dRuta: «Radar nuevo» / «Error en un radar»):
     aportaciones.json = [{"lat", "lon", "tipo", "limite", "rumbo" (opcional), "fecha", "comprobado": fuente o nota}]
     entran antes que la DGT y OSM;
     correcciones.json = [{"lat", "lon", "tipo", "accion", "valor", "fecha", "comprobado"}] se aplica al final a los
     radares de esa familia a menos de MISMO_M (aunque la DGT u OSM los sigan dando). accion: "quitar";
     "tipo" (valor = tipo nuevo); "limite" (valor = km/h); "rumbo" (valor = grados, o -1 = los dos sentidos);
     "paralela" (valor 1 = es de otra carretera: no se avisa mientras vamos por el eje).
     tipo tambien puede ser "movil" (zona habitual de radar movil; solo llega por aqui).
Un radar de una fuente posterior no se anade si ya hay otro del mismo tipo a menos de MISMO_M.
Formato: [lat, lon, tipo, limite, rumbo, paralela]; tipo fijo | tramo_inicio | tramo_fin | semaforo;
rumbo -1 = sentido desconocido (la app avisa si queda por delante); paralela 1 = esta cerca de uno de
nuestros ejes pero no sobre el (otra carretera paralela, un enlace): la app no lo avisa mientras vamos por el eje.

    python scripts/bajar.py; python scripts/leer_dgt.py datos/radares_dgt.xml; python scripts/unir_radares.py
(lo hace cada lunes .github/workflows/radares.yml). Escribe radares.json y meta.json en la raiz del repositorio.
"""
import os, sys, json, math, datetime
from collections import Counter
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")
MISMO_M = 150.0
EN_EJE_M = 40.0
CERCA_EJE_M = 1500.0

def hav(a, b):
    p = math.radians
    x = math.sin(p(b[0] - a[0]) / 2) ** 2 + math.cos(p(a[0])) * math.cos(p(b[0])) * math.sin(p(b[1] - a[1]) / 2) ** 2
    return 12742000 * math.asin(math.sqrt(x))

def rumbo(a, b):
    p = math.radians
    y = math.sin(p(b[1] - a[1])) * math.cos(p(b[0]))
    x = math.cos(p(a[0])) * math.sin(p(b[0])) - math.sin(p(a[0])) * math.cos(p(b[0])) * math.cos(p(b[1] - a[1]))
    return int(round((math.degrees(math.atan2(y, x)) + 360) % 360))

# --- ejes en celdas para medir la distancia a la calzada mas cercana ---
EJES = json.load(open(os.path.join(RAIZ, "ejes.json"), encoding="utf-8"))
K = 50.0   # celdas de ~2 km
CEL = {}
for pts in EJES.values():
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        if hav(a, b) > 2000: continue
        for la, lo in ((a[0], a[1]), (b[0], b[1])):
            CEL.setdefault((int(la * K), int(math.floor(lo * K))), set()).add((a[0], a[1], b[0], b[1]))
def dist_eje(la, lo):
    mejor = 1e9
    kx = 111320 * math.cos(math.radians(la)); ky = 110540
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            for a0, a1, b0, b1 in CEL.get((int(la * K) + dy, int(math.floor(lo * K)) + dx), ()):
                ax, ay = (a1 - lo) * kx, (a0 - la) * ky; bx, by = (b1 - lo) * kx, (b0 - la) * ky
                vx, vy = bx - ax, by - ay; l2 = vx * vx + vy * vy
                t = 0 if l2 == 0 else max(0, min(1, -(ax * vx + ay * vy) / l2))
                mejor = min(mejor, math.hypot(ax + t * vx, ay + t * vy))
    return mejor

def familia(t): return "tramo" if t.startswith("tramo") else t

# --- 1. base: lo que ya tenia la app ---
ruta_base = os.path.join(RAIZ, "base_ejes.json")
lista = [[r[0], r[1], r[2], r[3], r[4], 0] for r in json.load(open(ruta_base, encoding="utf-8"))]
fuente = Counter({"ejes (OSM)": len(lista)})
REJ = {}
def indexar(r): REJ.setdefault((int(r[0] * 200), int(math.floor(r[1] * 200))), []).append(r)
for r in lista: indexar(r)
def opuestos(a, b):
    # dos sentidos conocidos que difieren mas de 90 grados: la misma camara controla los dos sentidos
    return a is not None and a >= 0 and b is not None and b >= 0 and abs((a - b + 180) % 360 - 180) > 90
def repetido(la, lo, tipo, rb=None):
    cy, cx = int(la * 200), int(math.floor(lo * 200))
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            for r in REJ.get((cy + dy, cx + dx), []):
                if familia(r[2]) == familia(tipo) and hav((la, lo), (r[0], r[1])) < MISMO_M and not opuestos(r[4], rb):
                    return True
    return False
def anadir(la, lo, tipo, lim, rb, origen):
    if repetido(la, lo, tipo, rb): return
    d = dist_eje(la, lo)
    r = [round(la, 6), round(lo, 6), tipo, lim or 0, -1 if rb is None else rb, 1 if EN_EJE_M < d < CERCA_EJE_M else 0]
    lista.append(r); indexar(r); fuente[origen] += 1

def limite(tags):
    v = (tags or {}).get("maxspeed", "")
    return int(v) if v.isdigit() else 0

# --- 1b. avisos de usuarios ya comprobados ---
def leer_opc(nombre):
    ruta = os.path.join(RAIZ, nombre)
    return json.load(open(ruta, encoding="utf-8")) if os.path.exists(ruta) else []
for r in leer_opc("aportaciones.json"):
    anadir(r["lat"], r["lon"], r["tipo"], r.get("limite", 0), r.get("rumbo"), "usuarios")

# --- 2. DGT ---
for r in json.load(open(os.path.join(DATOS, "dgt.json"), encoding="utf-8")):
    anadir(r["lat"], r["lon"], r["tipo"], 0, None, "DGT")

# --- 3. OpenStreetMap: relaciones (dan tipo, limite y, con from/device, el sentido) y nodos sueltos ---
def miembros(el, rol): return [(m["lat"], m["lon"]) for m in el.get("members", []) if m.get("type") == "node" and "lat" in m and m.get("role") == rol]
SEM_SUELTOS = []
osm = json.load(open(os.path.join(DATOS, "osm_todos.json"), encoding="utf-8"))["elements"]
for el in osm:
    if el["type"] != "relation": continue
    t = el.get("tags", {}); lim = limite(t)
    if t.get("enforcement") == "average_speed":
        for rol, tipo in (("from", "tramo_inicio"), ("to", "tramo_fin")):
            for p in miembros(el, rol): anadir(p[0], p[1], tipo, lim, None, "OSM tramo")
    else:
        dev = miembros(el, "device"); ini = miembros(el, "from")
        for p in dev:
            rb = rumbo(ini[0], p) if ini and hav(ini[0], p) > 5 else None
            anadir(p[0], p[1], "fijo", lim, rb, "OSM velocidad")
sem = json.load(open(os.path.join(DATOS, "osm_semaforos.json"), encoding="utf-8"))["elements"]
# Camaras de semaforo en rojo etiquetadas en OSM como radar de velocidad (highway=speed_camera con nota «SEM ...»,
# «semáforo en rojo», speed_camera/enforcement=traffic_signals, o que son la camara de una relacion de semaforo):
# no son de velocidad. Si ya estan en una relacion de semaforo (con su sentido) se quitan; si no, van como semaforo.
DISP_SEM = {m.get("ref") for el in sem if el["type"] == "relation" for m in el.get("members", []) if m.get("role") == "device"}
NODOS_SEM = {el["id"] for el in sem if el["type"] == "node"}
def es_semaforo(el):
    t = el.get("tags") or {}
    txt = (t.get("note", "") + " " + t.get("description", "")).lower()
    return (el["id"] in DISP_SEM or el["id"] in NODOS_SEM or txt.strip().startswith("sem ")
            or "semáforo" in txt or "semaforo" in txt or t.get("speed_camera") == "traffic_signals"
            or t.get("enforcement") == "traffic_signals")
for el in osm:
    if el["type"] == "node":
        if es_semaforo(el):
            if el["id"] not in DISP_SEM and el["id"] not in NODOS_SEM:
                SEM_SUELTOS.append(el)
            continue
        anadir(el["lat"], el["lon"], "fijo", limite(el.get("tags")), None, "OSM velocidad")
for el in sem:
    if el["type"] == "relation":
        # el aviso va donde esta el semaforo (to); si no, la camara (device); el sentido, de from hacia ahi
        dest = miembros(el, "to") or miembros(el, "device") or miembros(el, "via")
        ini = miembros(el, "from")
        for p in dest[:1]:
            rb = rumbo(ini[0], p) if ini and hav(ini[0], p) > 5 else None
            anadir(p[0], p[1], "semaforo", 0, rb, "OSM semaforo")
for el in sem:
    if el["type"] == "node":
        anadir(el["lat"], el["lon"], "semaforo", 0, None, "OSM semaforo")
for el in SEM_SUELTOS:
    anadir(el["lat"], el["lon"], "semaforo", 0, None, "OSM semaforo (etiquetado como velocidad)")

# --- 4. correcciones de los usuarios (comprobadas) ---
COL = {"tipo": 2, "limite": 3, "rumbo": 4, "paralela": 5}
for q in leer_opc("correcciones.json"):
    toca = [r for r in lista if familia(r[2]) == familia(q["tipo"]) and hav((q["lat"], q["lon"]), (r[0], r[1])) < MISMO_M]
    if q["accion"] == "quitar":
        lista = [r for r in lista if not any(r is t for t in toca)]
    else:
        for r in toca: r[COL[q["accion"]]] = q["valor"]
    fuente["correcciones (" + q["accion"] + ")"] += len(toca)

# Prudencia: si salen muchos menos que la semana pasada (una fuente a medias), no se publica.
salida = os.path.join(RAIZ, "radares.json")
antes = len(json.load(open(salida, encoding="utf-8"))) if os.path.exists(salida) else 0
if antes and len(lista) < 0.85 * antes:
    sys.exit("Solo %d radares frente a %d: no se publica" % (len(lista), antes))
json.dump(lista, open(salida, "w", encoding="utf-8"), separators=(",", ":"))
json.dump({"fecha": datetime.date.today().isoformat(), "radares": len(lista),
           "por_tipo": dict(Counter(r[2] for r in lista)),
           "fuentes": ["DGT, inventario de radares (NAP, CC BY 4.0)", "© colaboradores de OpenStreetMap (ODbL)",
                       "avisos de usuarios de dRuta, comprobados"]},
          open(os.path.join(RAIZ, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("radares en la app:", len(lista), dict(fuente))
print("   por tipo:", dict(Counter(r[2] for r in lista)), "| con sentido:", sum(r[4] >= 0 for r in lista),
      "| paralelas:", sum(r[5] for r in lista))
