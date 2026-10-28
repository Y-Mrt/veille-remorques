# Veille remorques porte-voiture

Annonces Leboncoin de remorques porte-voiture (PTAC ~2,5 t, < 2 500 €, toute la France), vérifiées deux fois par jour (8 h 15 et 19 h 15) par une tâche planifiée Claude.

- `docs/` : le site GitHub Pages. Il lit `docs/data/annonces.json`.
- `scripts/merge_annonces.py` : la tâche planifiée écrit le résultat d'un passage dans un fichier `run.json`, puis ce script le fusionne dans `docs/data/annonces.json` (date de première détection, annonces retirées, passages bloqués).
- `android/` : l'application Android. Elle affiche le site et envoie une notification quand une nouvelle annonce apparaît. Elle est compilée par GitHub Actions (`.github/workflows/apk.yml`) et publiée dans les *Releases*.

## Mise en route (une seule fois)

1. **Settings → Pages** : Source « Deploy from a branch », branche `main`, dossier `/docs`.
2. **Actions → Compiler l'APK Android → Run workflow** pour produire la première version de l'APK (elle se recompile ensuite à chaque modification du dossier `android/`).
3. Sur le téléphone : ouvrir le site, toucher « Télécharger l'application Android », installer l'APK et accepter les notifications.

L'app n'a pas besoin d'être réinstallée quand les annonces changent : elle lit les données du site.

## Format d'un passage (`run.json`)

```json
{
  "run_at": "2026-10-29T08:15:00+01:00",
  "run": "matin",
  "status": "ok",
  "message": "",
  "annonces": [{
    "url": "https://www.leboncoin.fr/ad/equipement_auto/1234567890",
    "titre": "Remorque plateau porte-voiture",
    "prix": 2200,
    "ville": "Brive-la-Gaillarde", "departement": "19", "distance_km": 52,
    "date_publication": "2026-10-28T10:00:00+01:00",
    "ptac_kg": 2500, "ptac_source": "PTAC indiqué dans l'annonce", "essieux": 2,
    "freinage": true, "treuil": true, "rampes": true, "carte_grise": "oui", "etat": "bon",
    "points": "Plancher refait, treuil manuel.",
    "image": "https://img.leboncoin.fr/api/v1/lbcpb1/images/…?rule=ad-large"
  }],
  "recommandations": [{ "id": "1234567890", "raison": "PTAC indiqué, freinée, à 50 km." }]
}
```

`status` vaut `"bloque"` (avec un `message`) si Leboncoin n'a pas pu être consulté : les annonces déjà publiées sont alors conservées telles quelles.

La clé de signature de l'APK (`android/keystore/`) est volontairement dans le dépôt : c'est une app personnelle, et une clé fixe permet d'installer les mises à jour par-dessus l'ancienne version.
