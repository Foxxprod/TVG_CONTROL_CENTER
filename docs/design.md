# Charte graphique (identique pour tous les Control Center)

Ne pas reinventer : reutiliser les classes existantes (`pill_classes()`,
`HEADER_ICON_BUTTON_CLASSES`, `section_card_classes()`). Toute nouvelle
fonctionnalite doit ressembler a ce qui existe deja.

## Structure de page

```
+-- header (bg-slate-900, m-3, rounded-2xl, UNE seule ligne) -------------+
| logo | [titre logiciel blanc] titre epreuve... | [] ✎ ⚙ EMERGENCY | CASPAR CG | (DATA) | HEURE |
+-------------------------------------------------------------------------+
 (GRAPHIQUES | MEDIAS)   <- onglets pilule bg-slate-900
+-- section (carte rounded-2xl, bg-white / bg-slate-800) -----------------+
|  TITRE SECTION            TITRE COLONNE                                  |
|  ( BOUTON )  ( < BOUTON (2) > )                                          |
+-------------------------------------------------------------------------+
+-- footer (bg-slate-900, m-3, rounded-2xl) ------------------------------+
|      ( ALL OUT )  ( CLEAR PRW )  ( TAKE PREVIEW )  ( SWAP )  (invokes)   |
+-------------------------------------------------------------------------+
```

- Header/footer TOUJOURS sombres (slate-900), dans les deux themes.
- Fond de page : `bg-slate-50` clair / `bg-slate-900` sombre.
- Corps reduit par `BODY_ZOOM` (0.8), header/footer non zoomes.
- Header : `wrap=False` partout, groupe de droite `flex-shrink: 0`, seul le
  texte de gauche retrecit (clamp + truncate). Titre d'epreuve masque s'il est vide.

## Couleurs fonctionnelles

| Sens | Couleur |
|---|---|
| idle | `bg-slate-700` (clair) / `bg-slate-600` (sombre) |
| preview | `yellow` (`bg-yellow-600`) |
| programme / danger / OUT | `red` (`bg-red-600`) |
| ALL OUT | `orange` |
| TAKE | `green` |
| SWAP | `blue` |
| mode edition | `sky` |
| invoke (sponsor...) | `purple` par defaut |
| connecte / deconnecte | `green-600/20` / `red-600/20 animate-pulse` |

## Recettes

- **Bouton pilule colore** (header/footer/medias) : `pill_classes(color, extra)`
  = contour `-500`, fond `-600/20`, hover `-600/30`, texte `-400`,
  `font-bold rounded-full`. Toujours `color=None` sur `ui.button` (sinon
  Quasar impose sa couleur primary).
- **Bouton icone rond du header** : `HEADER_ICON_BUTTON_CLASSES` + `.props("round")`.
- **Bouton de grille** : pastille `rounded-full w-64`, texte `text-sm font-bold
  text-white`, segments annexes (fleches, crayon/poubelle) `bg-slate-800` separes
  par `border-slate-600`.
- **Box sous un bouton** (champs) : `border rounded-xl p-2`, `bg-slate-50` /
  `bg-slate-800`.
- **Titre de section** : `text-sm font-bold tracking-wide text-slate-500`.
- **Titre de colonne** : `text-sm font-bold uppercase tracking-wide text-slate-400`.
- **Sous-titre de formulaire** : `text-xs font-bold uppercase tracking-wide text-slate-500`.
- **Bandeau d'alerte** : `border border-red-500 bg-red-600/10 rounded-2xl` (info :
  `sky`).
- Notifications : `ui.notify(..., type="positive" | "warning" | "negative" | "info")`.
- Theme : tout composant non-Quasar qui depend du theme s'abonne via
  `SceneButton.on_dark_mode_change(callback)`.

## Textes

Interface en francais, SANS accents dans le code (convention du projet),
libelles de boutons d'action en MAJUSCULES.
