# TVG Control Center — template

Base commune pour créer des logiciels de régie qui pilotent des habillages TV
dans **CasparCG** (NiceGUI, Python 3.13).

Même interface, même connexion AMCP, même logique preview → Take → programme
et même design d'un projet à l'autre : on ne change que `project.py` et
`templates.json`.

## Ce que fournit la base

- **Interface** : header (logo, titre, plein écran, mode édition, paramètres,
  EMERGENCY ALL OUT, statut CasparCG, heure), corps en sections + grille,
  footer ALL OUT / CLEAR PRW / TAKE PREVIEW / SWAP. Thème clair/sombre.
- **CasparCG** : client AMCP, ping + reconnexion auto, paramètres modifiables à chaud.
- **Preview / programme** : clic = preview puis Take, pastille IN = direct
  programme, OUT = stop ; previews multiples.
- **Options de bouton** : multipage, texte libre, liste à choix, compteur -/+,
  données fixes, second CG, envoi IP source de données (voir `docs/button-options.md`).
- **Mode édition** : création / modification / suppression de boutons depuis
  l'interface, enregistrée dans `templates.json`.
- **Onglet MÉDIAS** : bibliothèque CasparCG, lecture sur un layer au choix,
  boucle, transition, SWAP, pause, opacité, volume.
- **Robustesse** : `templates.json` invalide → bandeau d'erreur précis, jamais
  de plantage ni d'écrasement.
- **Source de données** : contrat prêt (`data_source.py`), invisible tant
  qu'aucune n'est branchée (voir `docs/data-source.md`).
- **Livraison** : `.exe` PyInstaller (`app.spec`), config dans `%APPDATA%`.

## Lancer la base

```
py -3 -m pip install -r requirements.txt
py -3 main.py
```

Puis ouvrir http://localhost:8081.

## Créer un nouveau Control Center

Soit via le bouton GitHub **Use this template**, soit en local :

```
py -3 tools/new_project.py ..\TENNIS_CONTROL_CENTER --name "TENNIS - CONTROL CENTER" --slug TennisControlCenter
```

Ensuite, dans le nouveau projet :

1. `project.py` : `SECTIONS`, `GROW_SECTION`, `HEADER_TOGGLES`, `FOOTER_INVOKES`,
   `MEDIA_TAB_ENABLED`, `MEDIA_DEFAULT_LAYER`, `DATA_SOURCE_CLASS`.
2. `templates.json` : remplacer les boutons de démo (garder l'entrée `_example`).
3. Remplacer `assets/logo.png` / `icon.ico` si besoin.
4. Remplir `PROJECT_CONTEXT.txt` (mémoire du projet).

## Compiler

```
py -3 -m pip install -r requirements.txt pyinstaller
pyinstaller app.spec
```

→ `dist\<APP_SLUG>\<APP_SLUG>.exe` (livrer le dossier entier).

## Documentation

| Fichier | Contenu |
| --- | --- |
| `docs/button-options.md` | Toutes les options de bouton et comment en ajouter |
| `docs/design.md` | Charte graphique figée |
| `docs/amcp.md` | Commandes AMCP utilisées, codes de réponse |
| `docs/data-source.md` | Brancher une source de données |
| `docs/websocket_data_source.py` | Implémentation WebSocket prête à copier |
| `docs/nicegui-pitfalls.md` | Pièges NiceGUI connus |
