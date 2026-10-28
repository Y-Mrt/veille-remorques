# Veille remorques porte-voiture

Annonces Leboncoin de remorques porte-voiture (PTAC ~2,5 t, < 2 500 €, toute la France), vérifiées deux fois par jour (8 h 15 et 19 h 15) par une tâche planifiée Claude.

- `docs/` : le site GitHub Pages. Il lit `docs/data/annonces.json`.
- `scripts/merge_annonces.py` : la tâche planifiée écrit le résultat d'un passage dans un fichier `run.json`, puis ce script le fusionne dans `docs/data/annonces.json` (date de première détection, annonces retirées, passages bloqués).
- `scripts/validate_annonces.py` : refuse toute donnée inattendue (lien qui n'est pas une annonce Leboncoin en https, image hors `img.leboncoin.fr`, champ inconnu, texte trop long).
- `android/` : l'application Android. Elle affiche le site et envoie une notification quand une nouvelle annonce apparaît. Elle est compilée par GitHub Actions (`.github/workflows/apk.yml`), **uniquement à la demande**, et publiée dans les *Releases*.

## Sécurité

- **La tâche planifiée ne pousse que sur la branche `donnees`.** Le workflow « Publier les données » n'en reprend que `docs/data/annonces.json`, le vérifie avec le validateur de `main`, puis le copie sur `main`. Tout autre fichier modifié sur `donnees` est ignoré.
- Le site est déployé par le workflow « Déployer le site », qui revérifie les données avant chaque mise en ligne.
- L'APK n'est jamais recompilé automatiquement : une modification du code ne peut pas produire toute seule une nouvelle version de l'app.
- La clé de signature de l'APK n'est pas dans le dépôt : elle est dans les secrets GitHub `ANDROID_KEYSTORE_B64` (fichier PKCS12 en base64) et `ANDROID_KEYSTORE_PASSWORD`. Garde-en une copie hors de GitHub : sans elle, il faudra désinstaller l'app pour installer une nouvelle version.

## Mise en route (une seule fois)

1. **Settings → Secrets and variables → Actions** : créer les secrets `ANDROID_KEYSTORE_B64` et `ANDROID_KEYSTORE_PASSWORD`.
2. **Settings → Pages** : Source « GitHub Actions ».
3. **Actions → Déployer le site → Run workflow**, puis **Actions → Compiler l'APK Android → Run workflow**.
4. Sur le téléphone : ouvrir le site, toucher « Télécharger l'application Android », installer l'APK et accepter les notifications.

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
