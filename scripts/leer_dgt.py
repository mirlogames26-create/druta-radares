# -*- coding: utf-8 -*-
"""Lee el inventario DATEX II de la DGT (radares_dgt.xml) -> dgt.json: [{id, tipo, lat, lon, via, pk_m, sentido, prov}]"""
import re, json, sys, xml.etree.ElementTree as ET
NS = {"d": "http://datex2.eu/schema/1_0/1_0"}
raiz = ET.parse(sys.argv[1] if len(sys.argv) > 1 else "radares_dgt.xml").getroot()
out = []
for conj in raiz.iter("{%s}predefinedLocationSet" % NS["d"]):
    tramo = "VelocidadMedia" in conj.get("id")
    for loc in conj.findall("d:predefinedLocation", NS):
        pid = loc.get("id")
        def puntos(tag):
            r = []
            for p in loc.iter("{%s}%s" % (NS["d"], tag)):
                c = p.find("d:pointCoordinates", NS)
                if c is None: continue
                via = [n.find("d:descriptor/d:value", NS).text for n in p.findall("d:name", NS)
                       if n.findtext("d:tpegDescriptorType", namespaces=NS) == "linkName"]
                r.append((float(c.findtext("d:latitude", namespaces=NS)), float(c.findtext("d:longitude", namespaces=NS)), via[0] if via else ""))
            return r
        rp = loc.find(".//d:referencePoint", NS)
        pk = float(rp.findtext("d:referencePointDistance", namespaces=NS)) if rp is not None and rp.findtext("d:referencePointDistance", namespaces=NS) else None
        sent = rp.findtext("d:directionRelative", namespaces=NS) if rp is not None else None
        prov = rp.findtext("d:administrativeArea/d:value", namespaces=NS) if rp is not None else None
        if tramo:
            for tag, tipo in (("from", "tramo_inicio"), ("to", "tramo_fin")):
                for la, lo, via in puntos(tag):
                    out.append(dict(id=pid, tipo=tipo, lat=la, lon=lo, via=via, pk_m=pk, sentido=sent, prov=prov))
        else:
            for la, lo, via in puntos("point"):
                out.append(dict(id=pid, tipo="fijo", lat=la, lon=lo, via=via, pk_m=pk, sentido=sent, prov=prov))
import os
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "radares_dgt.xml")), "dgt.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
from collections import Counter
print(len(out), Counter(r["tipo"] for r in out))
