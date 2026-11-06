# Pieges NiceGUI / Quasar deja rencontres (a lire avant de deboguer l'UI)

Tous ont coute du temps sur le Biath Control Center. Le template les evite
deja — ne pas les reintroduire.

1. **`.classes(replace=...)` remplace TOUT**, y compris les classes par
   defaut de NiceGUI (ex: `flex` d'un `ui.row()`). Toujours les reinclure.
2. **`ui.button(..., color=None)`** sinon Quasar impose `primary` (bleu) et
   ignore les classes Tailwind de couleur.
3. **`ui.image(Path(...))`** : un `pathlib.Path`, pas une string (sinon 404
   silencieux). Tailles fixes (`h-10 w-16`).
4. **Focus dans un dialog** : `.props("autofocus")` + secours
   `ui.timer(0.1, lambda: el.run_method("focus"), once=True)`.
5. **PIEGE MAJEUR "auto-index page"** : tout code NiceGUI hors d'une
   fonction `@ui.page` est re-execute a chaque connexion navigateur. Les
   instances `CasparCG`/source de donnees sont creees au niveau module dans
   `main.py`, l'UI uniquement dans `@ui.page("/")`.
6. `ui.run(reload=False)` (taches de fond persistantes).
7. `valeur = await dialog` ouvre le dialog et attend `dialog.submit(v)`.
8. **Grille ligne/colonne** : jamais des `ui.row()` independantes (la
   "colonne N" ne s'aligne pas). Vraie grille CSS + `grid-row`/`grid-column`
   explicites. La hauteur d'une ligne est partagee par toutes les colonnes :
   pour empiler sous un bouton, utiliser la meme case.
9. **Header/footer Quasar** positionnes sur le viewport :
   `ui.query(".nicegui-content").style("padding-left: 0; padding-right: 0;")`
   — JAMAIS `padding: 0` (Quasar utilise padding-top pour pousser le contenu
   sous le header fixe -> corps cache derriere le header).
10. **Zoom d'une zone** : propriete CSS `zoom` (pas `transform: scale`), et
    diviser toute hauteur fixe par le zoom.
11. **Header sur une ligne** : `wrap=False` sur `ui.header()` ET chaque
    `ui.row()` (wrap=True par defaut), groupe de droite `flex-shrink: 0`,
    texte de gauche `min-w-0` + `truncate` + `clamp()`.
12. **`make_sortable()` ne marche PAS dans un `ui.dialog()`/`ui.menu()`**
    (contenu teleporte par Vue). Utiliser une `ui.column` "fixed inset-0"
    basculee par `.visible`, stylee comme un dialog.
13. Une icone d'alerte a cote d'un bouton : la positionner en `absolute`
    dans le conteneur `relative` du bouton, pas en voisine flex.
14. **Lambdas dans une boucle** : capturer par argument par defaut
    (`lambda _, ft=free_text: ...`). MAIS une lambda dont le 1er parametre a
    un defaut recoit l'evenement de clic a sa place : pour un handler sans
    argument, utiliser une fonction imbriquee (voir `edit_actions_for`).
15. **Abonnements a un singleton partage** (source de donnees,
    `on_dark_mode_change`) recrees a chaque chargement de page : se
    desabonner via `ui.context.client.on_delete(...)` quand c'est possible.
16. Un element cree dans une **grille CSS** y occupe une case : creer les
    dialogs du mode edition dans un hote hors grille (`dialog_host`).
17. Quasar met les libelles de bouton en MAJUSCULES (CSS) : un test qui
    cherche le texte d'un bouton doit chercher "ENREGISTRER", pas "Enregistrer".
18. Sous Windows, `Path.write_text()` ecrit en CRLF : ecrire avec
    `open(..., newline="\n")` pour garder les fichiers en LF.
