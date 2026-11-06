# Options de bouton (templates.json)

Chaque entree de `templates.json` = un `SceneButton`. Champs obligatoires :
`section`, `label`, `template`, `layer`. Tout champ inconnu est signale dans
le bandeau rouge (faute de frappe) — pour ajouter une option, ajouter un
parametre au constructeur `SceneButton` (la liste des champs acceptes en est
deduite automatiquement, voir `interface.BUTTON_FIELDS`).

Les boutons peuvent aussi etre crees/modifies/supprimes depuis l'interface :
**mode edition** (crayon du header). Meme validation que le fichier.

## Toujours present : preview -> programme

| Action | idle | preview | programme |
|---|---|---|---|
| clic sur le bouton | play en **preview** | **Take** -> programme | rien |
| pastille au survol | **IN** = direct programme | **IN** = Take | **OUT** = stop (toujours visible) |

- Un `(layer, cg_layer)` = un seul occupant, en preview comme au programme.
- Un bouton previse sur SON layer (le meme qu'au programme) : plusieurs
  previews simultanees possibles, TAKE PREVIEW / SWAP / CLEAR PRW agissent
  sur toutes.
- Couleurs : idle slate, preview `bg-yellow-600`, programme `bg-red-600`.

```json
{"section": "live", "row": 1, "column": 1, "label": "LOGO", "template": "logo", "layer": 10}
```

`cg_layer` (defaut 1) : layer d'empilement CG dans le layer video.

## Multipage

Fleches `<` `>` dans la pastille, numero affiche `LABEL (n)`, envoye dans
`field_page` (defaut `page`), pousse en direct (CG UPDATE) si deja affiche.

```json
{"label": "CLASSEMENT", "template": "ranking", "layer": 30,
 "multipage_on": true, "reset_page_on_play": true, "field_page": "page"}
```

## Texte libre

```json
"free_texts": [{"field": "name", "label": "Nom"}]
```

Champ sous le bouton (box bordee), valeur envoyee a chaque play/update,
grise tant que le bouton n'est pas idle.

## Liste a choix multiples

```json
"free_texts": [{"field": "sponsor", "label": "Sponsor", "options": ["A", "B"]}]
```

`options` present (meme vide `[]`) -> combo box + texte libre en dessous
(mutuellement exclusifs) + icones `+`/`-` qui ajoutent/suppriment une option
EN DIRECT, persistee dans `templates.json`.

## Compteur numerique (spinbox)

```json
"free_texts": [{"field": "home", "label": "Domicile", "type": "number",
                "min": 0, "max": 99, "step": 1, "default": 0}]
```

Ligne `(-) [valeur] (+)` (saisie directe aussi possible). `min`/`max`/`step`/
`default` optionnels. Contrairement aux champs texte, **reste modifiable a
l'antenne** : chaque changement est pousse aussitot (CG UPDATE) si le
graphique est en preview/au programme — ex: compter des points. Valeur
entiere envoyee sans decimale (`"12"`, pas `"12.0"`). Un meme bouton peut
melanger texte, liste et compteurs.

## Donnees fixes

```json
"extra_data": {"style": "dark", "lang": "fr"}
```

## Second graphique synchronise

```json
"second_cg": "lower_third_bg", "second_cg_layer": 19
```

Joue/stoppe/mis a jour en meme temps que le principal, meme payload. Toujours
au `cg_layer + 1` (sinon il remplacerait le principal sur un layer partage).
Un echec du second CG ne fait jamais echouer le principal.

## Envoi de l'IP de la source de donnees

```json
"send_ip": true, "field_ip": "ip"
```

Refuse (bandeau rouge) tant que `project.DATA_SOURCE_CLASS` est `None`.

## Titres de colonne

```json
{"_column_title": true, "section": "live", "column": 2, "title": "INFOS"}
```

## Grille

- `row`/`column` : ENTIERS (un `"1"` est tolere et converti).
- Plusieurs entrees sur la meme case s'empilent verticalement (c'est ce que
  fait le `+` de bas de colonne du mode edition).
- La hauteur d'une ligne est partagee par toutes les colonnes de la section :
  pour empiler sous un bouton, utiliser la MEME case plutot que `row + 1`.

## Ajouter une nouvelle option (pour un projet)

1. Parametre dans `SceneButton.__init__` (avec defaut) + stockage `self.x`.
2. Rendu dans `_build` / `_build_button` si besoin, en suivant le design.
3. Valeur dans `_build_payload`.
4. Champ dans `button_editor.py` (sinon l'editeur ne le connait pas, et le
   perdrait a l'enregistrement d'un bouton modifie).
5. Documentation dans l'entree `_example` de `templates.json`.
