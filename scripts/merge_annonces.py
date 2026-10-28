#!/usr/bin/env python3
"""Fusionne le résultat d'un passage de veille dans docs/data/annonces.json.

Usage : python3 scripts/merge_annonces.py run.json [docs/data/annonces.json]

run.json (écrit par la tâche planifiée à chaque passage) :
{
  "run_at": "2026-10-29T08:15:00+01:00",
  "run": "matin" | "soir",
  "status": "ok" | "bloque",
  "message": "texte court (obligatoire si bloque)",
  "annonces": [ { "url": "...", "titre": "...", "prix": 1800, ... } ],
  "recommandations": [ { "id": "1234567890", "raison": "..." } ]
}

Seules les annonces VÉRIFIÉES (PTAC indiqué ≥ 2 t, ou 2 essieux vus sur les
photos) doivent figurer dans "annonces". Le script :
- garde la date de première détection (first_seen) de chaque annonce ;
- marque en_ligne=false les annonces absentes d'un passage réussi ;
- supprime les annonces retirées depuis plus de 30 jours ;
- n'efface rien si le passage a été bloqué (navigateur injoignable, captcha).
"""
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

CHAMPS = [
    "titre", "prix", "ville", "departement", "distance_km", "date_publication",
    "ptac_kg", "ptac_source", "essieux", "freinage", "treuil", "rampes",
    "carte_grise", "etat", "points", "url", "image",
]
RETENTION_JOURS = 30
MAX_RUNS = 60


def parse_dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def annonce_id(a):
    if a.get("id"):
        return str(a["id"])
    m = re.search(r"(\d{8,})", a.get("url", ""))
    if not m:
        raise ValueError(f"Impossible de trouver l'identifiant de l'annonce : {a.get('url')!r}")
    return m.group(1)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    run = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out_path = Path(sys.argv[2] if len(sys.argv) > 2 else "docs/data/annonces.json")
    data = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    data.setdefault("annonces", [])
    data.setdefault("recommandations", [])
    data.setdefault("runs", [])

    run_at = run["run_at"]
    parse_dt(run_at)  # valide le format
    status = run.get("status", "ok")
    if status not in ("ok", "bloque"):
        sys.exit(f"status inconnu : {status!r}")

    existantes = {a["id"]: a for a in data["annonces"]}
    nouvelles = 0
    vues = set()

    if status == "ok":
        for brute in run.get("annonces", []):
            aid = annonce_id(brute)
            if aid in vues:
                continue
            vues.add(aid)
            a = existantes.get(aid)
            if a is None:
                a = {"id": aid, "first_seen": run_at}
                existantes[aid] = a
                nouvelles += 1
            for champ in CHAMPS:
                if champ in brute and brute[champ] not in (None, ""):
                    a[champ] = brute[champ]
            a["last_seen"] = run_at
            a["en_ligne"] = True
            a.pop("retiree_le", None)

        for aid, a in existantes.items():
            if aid not in vues and a.get("en_ligne", True):
                a["en_ligne"] = False
                a["retiree_le"] = run_at

        limite = parse_dt(run_at) - timedelta(days=RETENTION_JOURS)
        existantes = {
            aid: a for aid, a in existantes.items()
            if a.get("en_ligne") or parse_dt(a.get("retiree_le", run_at)) >= limite
        }
        data["recommandations"] = [
            {"id": str(r["id"]), "raison": r.get("raison", "")}
            for r in run.get("recommandations", []) if str(r.get("id")) in existantes
        ]

    # En ligne d'abord, puis les plus récemment détectées.
    data["annonces"] = sorted(existantes.values(), key=lambda a: a.get("first_seen", ""), reverse=True)
    data["annonces"].sort(key=lambda a: not a.get("en_ligne", True))

    data["last_run"] = {
        "run_at": run_at,
        "run": run.get("run", ""),
        "status": status,
        "message": run.get("message", ""),
        "nb_en_ligne": sum(1 for a in data["annonces"] if a.get("en_ligne")),
        "nb_nouvelles": nouvelles,
    }
    if status == "ok":
        data["last_ok_run_at"] = run_at
    data["runs"] = ([dict(data["last_run"])] + data["runs"])[:MAX_RUNS]
    data["updated_at"] = run_at

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{status} : {data['last_run']['nb_en_ligne']} en ligne, {nouvelles} nouvelle(s)")


if __name__ == "__main__":
    main()
