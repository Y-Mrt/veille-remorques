#!/usr/bin/env python3
"""Vérifie que docs/data/annonces.json ne contient que des données attendues.

Usage : python3 scripts/validate_annonces.py docs/data/annonces.json
Sort en erreur (code 1) au moindre champ inattendu : lien qui n'est pas une
annonce Leboncoin en https, image qui ne vient pas de img.leboncoin.fr,
texte trop long, type incorrect.
"""
import json
import re
import sys

URL_RE = re.compile(r"^https://www\.leboncoin\.fr/[A-Za-z0-9_\-/.]+$")
IMG_RE = re.compile(r"^https://img\.leboncoin\.fr/[A-Za-z0-9_\-/.%]+(\?[A-Za-z0-9_\-=&.]+)?$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$")
ID_RE = re.compile(r"^\d{6,15}$")

TEXTE = {"titre": 200, "ville": 80, "departement": 4, "ptac_source": 120,
         "carte_grise": 60, "etat": 60, "points": 600}
NOMBRE = {"prix": (0, 100000), "distance_km": (0, 2500), "ptac_kg": (0, 10000), "essieux": (1, 4)}
BOOL = {"freinage", "treuil", "rampes", "en_ligne"}
DATES = {"date_publication", "first_seen", "last_seen", "retiree_le"}
ANNONCE_CLES = set(TEXTE) | set(NOMBRE) | BOOL | DATES | {"id", "url", "image"}
RACINE_CLES = {"updated_at", "last_run", "last_ok_run_at", "recommandations", "annonces", "runs"}
RUN_CLES = {"run_at", "run", "status", "message", "nb_en_ligne", "nb_nouvelles"}

erreurs = []


def err(msg):
    erreurs.append(msg)


def check_date(v, ou):
    if v is not None and not (isinstance(v, str) and DATE_RE.match(v)):
        err(f"{ou} : date invalide {v!r}")


def check_run(r, ou):
    if r is None:
        return
    if not isinstance(r, dict) or set(r) - RUN_CLES:
        return err(f"{ou} : champs inattendus")
    check_date(r.get("run_at"), ou + ".run_at")
    if r.get("run") not in ("matin", "soir", ""):
        err(f"{ou}.run invalide")
    if r.get("status") not in ("ok", "bloque"):
        err(f"{ou}.status invalide")
    if not isinstance(r.get("message", ""), str) or len(r.get("message", "")) > 300:
        err(f"{ou}.message invalide")
    for k in ("nb_en_ligne", "nb_nouvelles"):
        if not isinstance(r.get(k, 0), int):
            err(f"{ou}.{k} invalide")


def main():
    d = json.load(open(sys.argv[1], encoding="utf-8"))
    if not isinstance(d, dict) or set(d) - RACINE_CLES:
        err("racine : champs inattendus")
        d = {}
    check_date(d.get("updated_at"), "updated_at")
    check_date(d.get("last_ok_run_at"), "last_ok_run_at")
    check_run(d.get("last_run"), "last_run")
    for i, r in enumerate(d.get("runs", [])[:100]):
        check_run(r, f"runs[{i}]")
    if len(d.get("runs", [])) > 100:
        err("runs : trop d'entrées")

    ids = set()
    annonces = d.get("annonces", [])
    if not isinstance(annonces, list) or len(annonces) > 500:
        err("annonces : liste invalide")
        annonces = []
    for i, a in enumerate(annonces):
        ou = f"annonces[{i}]"
        if not isinstance(a, dict):
            err(ou + " invalide"); continue
        if set(a) - ANNONCE_CLES:
            err(f"{ou} : champs inattendus {sorted(set(a) - ANNONCE_CLES)}")
        if not (isinstance(a.get("id"), str) and ID_RE.match(a["id"])):
            err(f"{ou}.id invalide")
        ids.add(a.get("id"))
        if not (isinstance(a.get("url"), str) and URL_RE.match(a["url"])):
            err(f"{ou}.url doit être un lien https://www.leboncoin.fr/…")
        if "image" in a and not (isinstance(a["image"], str) and IMG_RE.match(a["image"])):
            err(f"{ou}.image doit venir de https://img.leboncoin.fr/")
        for k, n in TEXTE.items():
            if k in a and not (isinstance(a[k], str) and len(a[k]) <= n):
                err(f"{ou}.{k} invalide ou trop long")
        for k, (lo, hi) in NOMBRE.items():
            if k in a and not (isinstance(a[k], (int, float)) and not isinstance(a[k], bool) and lo <= a[k] <= hi):
                err(f"{ou}.{k} hors limites")
        for k in BOOL:
            if k in a and not isinstance(a[k], bool):
                err(f"{ou}.{k} doit être vrai/faux")
        for k in DATES:
            check_date(a.get(k), f"{ou}.{k}")

    for i, r in enumerate(d.get("recommandations", [])):
        if not isinstance(r, dict) or set(r) - {"id", "raison"} or r.get("id") not in ids \
                or not isinstance(r.get("raison", ""), str) or len(r.get("raison", "")) > 300:
            err(f"recommandations[{i}] invalide")

    if erreurs:
        for e in erreurs[:50]:
            print("ERREUR :", e)
        sys.exit(1)
    print(f"OK : {len(annonces)} annonce(s) valides")


if __name__ == "__main__":
    main()
