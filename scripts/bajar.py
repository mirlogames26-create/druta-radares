# -*- coding: utf-8 -*-
"""Baja las fuentes de los radares a datos/: el inventario de la DGT (NAP, DATEX II) y los radares de OpenStreetMap
de Espana y Portugal (Overpass: velocidad y tramo; camaras de semaforo). Si alguna falla, sale con error y no se
toca radares.json (se queda el de la semana anterior)."""
import os, sys, json, time, urllib.request, urllib.parse
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos"); os.makedirs(DATOS, exist_ok=True)
UA = {"User-Agent": "druta-radares/1.0 (+https://github.com/mirlogames26-create/druta-radares)"}
DGT = "https://nap.dgt.es/datex2/dgt/PredefinedLocationsPublication/radares/content.xml"
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter"]
AREAS = 'area["ISO3166-1"="ES"][admin_level=2]->.es;area["ISO3166-1"="PT"][admin_level=2]->.pt;'
Q_VEL = ('[out:json][timeout:600];' + AREAS +
         '(node["highway"="speed_camera"](area.es);node["highway"="speed_camera"](area.pt);'
         'rel["type"="enforcement"]["enforcement"~"maxspeed|average_speed"](area.es);'
         'rel["type"="enforcement"]["enforcement"~"maxspeed|average_speed"](area.pt););out geom;')
Q_SEM = ('[out:json][timeout:600];' + AREAS +
         '(rel["type"="enforcement"]["enforcement"="traffic_signals"](area.es);'
         'rel["type"="enforcement"]["enforcement"="traffic_signals"](area.pt);'
         'node["enforcement"="traffic_signals"](area.es);node["enforcement"="traffic_signals"](area.pt););out geom;')

def get(url, data=None, timeout=660):
    req = urllib.request.Request(url, data=data, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read()

def overpass(q, nombre):
    for intento in range(2):
        for ep in OVERPASS:
            try:
                d = get(ep, urllib.parse.urlencode({"data": q}).encode())
                n = len(json.loads(d.decode("utf-8")).get("elements", []))
                if n == 0: raise ValueError("respuesta vacia")
                open(os.path.join(DATOS, nombre), "wb").write(d)
                print("OK", nombre, n, "elementos de", ep); return
            except Exception as ex:
                print("  fallo", ep, ex)
        time.sleep(60)
    sys.exit("No se pudo bajar " + nombre)

x = get(DGT, timeout=180)
if b"CabinasCinemometro" not in x: sys.exit("La DGT no ha devuelto el inventario de radares")
open(os.path.join(DATOS, "radares_dgt.xml"), "wb").write(x); print("OK DGT", len(x), "bytes")
overpass(Q_VEL, "osm_todos.json")
overpass(Q_SEM, "osm_semaforos.json")
