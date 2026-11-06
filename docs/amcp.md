# CasparCG / AMCP — rappels et regles de la base

`casparcg.py` est une implementation maison (socket TCP brut). Toute
nouvelle commande doit etre verifiee contre la doc AMCP officielle
(casparcg.com / repo `server/docs`), la doc pouvant etre datee — ne pas
supposer une syntaxe.

## Reponses

- `202 X OK` : succes, aucune ligne en plus (CG ADD/UPDATE/STOP/REMOVE, PLAY, CLEAR...).
- `201 X OK` + **une** ligne (ex: CG INVOKE).
- `200 X OK` + plusieurs lignes terminees par une ligne vide (CLS, TLS, INFO...).
- `4xx`/`5xx` : erreur. Code `0` cote logiciel = erreur locale/reseau.
- BUG HISTORIQUE : ne lire que le cas 200 laissait la ligne d'un 201 dans le
  tampon et desynchronisait toutes les reponses suivantes (puis fausse
  deconnexion au PING suivant). `_read_response` gere les 3 cas.
- `PING` repond `PONG` brut (gere a part). Ping toutes les 5 s, reconnexion
  automatique toutes les 5 s.

## Channels

`"prw"` / `"pgm"` -> `channel_preview` / `channel_programm` (reglables dans
Parametres). Adresse `channel-layer`, layer TOUJOURS explicite (un bouton
previse sur son propre layer).

## Graphiques (templates)

| Methode | Commande |
|---|---|
| `play_template` | `CG c-l ADD cg "tpl" 1 "<xml>"` |
| `update_template` | `CG c-l UPDATE cg "<xml>"` |
| `stop` | `CG c-l STOP cg` + `CG REMOVE` automatique 5 s apres |
| `invoke_template` | `CG c-l INVOKE cg fonction` (nom sans espace, sans guillemets) |
| `clear` | `CLEAR c-l` (tout producer) ou `CLEAR c` (channel entier) |
| `play_prw_to_pgm` | rejoue en pgm le dernier template/donnees envoye en preview sur ce (layer, cg_layer), puis CLEAR preview |
| `emergency_all_out` | `CLEAR` des deux channels |

Donnees : XML `<templateData><componentData id="cle"><data id="text"
value="valeur"/></componentData>...</templateData>`, echappe XML puis AMCP.

## Medias (onglet MEDIAS)

| Methode | Commande |
|---|---|
| `list_media` | `CLS` -> `"NOM" TYPE TAILLE DATE [FRAMES] [TIMEBASE]` |
| `play_media` | `PLAY c-l "clip" [LOOP] [MIX\|PUSH\|SLIDE\|WIPE duree]` |
| `set_media_loop` | `CALL c-l LOOP 0/1` |
| `pause_media` / `resume_media` | `PAUSE c-l` / `RESUME c-l` |
| `set_mixer` | `MIXER c-l OPACITY\|VOLUME v [duree]` |
| `clear_mixer` | `MIXER c-l CLEAR` |
| `move_layer` | `SWAP c-a c-b` (la lecture continue ; le MIXER ne suit pas -> reappliquer) |

Les layers des boutons de la grille sont refuses dans l'onglet MEDIAS.
`project.MEDIA_DEFAULT_LAYER` (50) : choisir une plage hors des layers
graphiques du projet.

## Regles

- Ne jamais envoyer `BYE` sur une connexion locale a la console du serveur.
- Ne jamais casser preview -> Take -> programme ni l'auto-remove differe.
- Plusieurs previews simultanees = voulu (pre-composition), ne pas revenir
  a un layer de preview unique.
