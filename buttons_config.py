# Chargement ET VALIDATION de templates.json (catalogue des boutons), lu a
# chaque chargement de page par interface.build_body.
#
# Chaque entree reprend les parametres du constructeur SceneButton (voir
# scene_button.py), plus :
#   - "section" (obligatoire) : une des cles de project.SECTIONS
#   - "row"/"column" (optionnels, defaut 1) : case de la grille
# Une entree "_column_title": true (section/column/title) est un titre de
# colonne ; l'entree "_example": true est de la documentation, ignoree.
#
# AUCUNE erreur de ce fichier ne fait planter le logiciel : load_layout()
# collecte des messages lisibles (JSON mal forme avec ligne/colonne, champ
# manquant, champ inconnu/mal orthographie, section inconnue, valeur non
# numerique...) que l'interface affiche dans un bandeau rouge. Les
# entrees invalides sont ignorees, les autres s'affichent normalement.
#
# templates.json peut aussi etre REECRIT par le logiciel (options de
# free_text ajoutees/supprimees en direct) - JAMAIS si le fichier n'a pas
# pu etre lu (layout.can_save = False), sinon une simple faute de frappe
# dans le JSON ferait ecraser tout le catalogue par une liste vide.

import json
from dataclasses import dataclass, field
from pathlib import Path

from paths import FROZEN, ensure_user_file, resource_path

BUTTONS_CONFIG_PATH = ensure_user_file("templates.json")

REQUIRED_FIELDS = ("section", "label", "template", "layer")
COLUMN_TITLE_REQUIRED_FIELDS = ("section", "column", "title")
INT_FIELDS = ("row", "column", "layer", "cg_layer", "second_cg_layer")
#cles propres a templates.json (pas des parametres SceneButton)
LAYOUT_FIELDS = {"section", "row", "column", "_comment"}


@dataclass
class ButtonsLayout:
    #liste brute (memes objets que buttons/column_titles) - reecrite telle
    #quelle par save_button_configs pour persister une modification faite
    #en memoire par un SceneButton
    raw: list = field(default_factory=list)
    buttons: list[dict] = field(default_factory=list)
    column_titles: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    can_save: bool = False


#identifie une entree de facon STABLE pour merge_bundled_templates : le
#triplet (template, layer, cg_layer) est ce qui est reellement envoye a
#CasparCG, "label" seul ne suffit pas
def _entry_identity(entry: dict) -> tuple:
    if entry.get("_example"):
        return ("_example",)
    if entry.get("_column_title"):
        return ("_column_title", entry.get("section"), entry.get("column"))
    return ("_button", entry.get("template"), entry.get("layer"), entry.get("cg_layer", 1))


#complete (AJOUTE UNIQUEMENT) la copie utilisateur de templates.json avec
#les entrees NOUVELLES du templates.json embarque dans l'executable - sans
#ca, une version recompilee avec de nouveaux boutons ne les ferait jamais
#apparaitre (la copie utilisateur n'est creee qu'au tout premier
#lancement). Ne retire ni n'ecrase jamais rien.
def merge_bundled_templates(bundled: list[dict], user: list[dict]) -> tuple[list[dict], bool]:
    existing_identities = {_entry_identity(entry) for entry in user if isinstance(entry, dict)}
    merged = list(user)
    changed = False

    for entry in bundled:
        if not isinstance(entry, dict):
            continue
        identity = _entry_identity(entry)
        if identity not in existing_identities:
            merged.append(entry)
            existing_identities.add(identity)
            changed = True

    return merged, changed


def _merge_bundled_templates_on_startup() -> None:
    if not FROZEN:
        return

    try:
        bundled = _load_raw(resource_path("templates.json"))
        user = _load_raw(BUTTONS_CONFIG_PATH)
    except (OSError, ValueError):
        return

    merged, changed = merge_bundled_templates(bundled, user)
    if changed:
        save_button_configs(merged)


#lit le JSON brut (liste). Leve ValueError avec un message LISIBLE par un
#operateur (ligne/colonne de l'erreur de syntaxe) plutot que la trace brute
def _load_raw(path: Path) -> list:
    try:
        with path.open("r", encoding="utf-8") as f:
            configs = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path.name} : JSON invalide ligne {exc.lineno}, colonne {exc.colno} - {exc.msg}"
            " (virgule en trop/manquante, guillemet non ferme, commentaire... ?)"
        ) from exc

    if not isinstance(configs, list):
        raise ValueError(f"{path.name} doit contenir une liste JSON [ ... ] de definitions")

    return configs


def save_button_configs(configs: list, path: Path = BUTTONS_CONFIG_PATH) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(configs, f, indent=2, ensure_ascii=False)


#nom court d'une entree pour les messages d'erreur
def _describe(index: int, entry: dict) -> str:
    name = entry.get("label") or entry.get("title") or entry.get("template") or "?"
    return f"Entree #{index + 1} ('{name}')"


#convertit en int les champs numeriques (un "1" entre guillemets est une
#erreur frequente en editant a la main - accepte silencieusement), renvoie
#un message d'erreur si la valeur n'est pas numerique du tout
def _coerce_ints(entry: dict, where: str) -> str | None:
    for key in INT_FIELDS:
        if key not in entry or entry[key] is None:
            continue
        try:
            entry[key] = int(entry[key])
        except (TypeError, ValueError):
            return f"{where} : '{key}' doit etre un nombre entier (recu {entry[key]!r})"
    return None


def _validate_free_texts(value, where: str) -> str | None:
    if not isinstance(value, list):
        return f"{where} : 'free_texts' doit etre une liste [ {{\"field\": ...}} ]"
    for free_text in value:
        if not isinstance(free_text, dict) or not free_text.get("field"):
            return f"{where} : chaque free_text doit etre un objet avec au moins \"field\""
        name = free_text["field"]
        options = free_text.get("options")
        if options is not None and not isinstance(options, list):
            return f"{where} : 'options' du free_text '{name}' doit etre une liste"

        kind = free_text.get("type", "text")
        if kind not in ("text", "number"):
            return f"{where} : 'type' du free_text '{name}' doit etre \"text\" ou \"number\" (recu {kind!r})"
        if kind == "number":
            if options is not None:
                return f"{where} : le free_text nombre '{name}' ne peut pas avoir d'options"
            for key in ("min", "max", "step", "default"):
                number = free_text.get(key)
                if number is not None and (isinstance(number, bool) or not isinstance(number, (int, float))):
                    return f"{where} : '{key}' du free_text '{name}' doit etre un nombre (recu {number!r})"
            if free_text.get("step", 1) <= 0:
                return f"{where} : 'step' du free_text '{name}' doit etre positif"
    return None


#valide (et normalise : entiers) UNE definition de bouton - utilisee par
#load_layout ET par l'editeur du mode edition (button_editor.py), pour
#que les deux appliquent exactement les memes regles. Renvoie None si OK.
def validate_button(
    entry: dict,
    known_sections: list[str],
    button_fields: set[str],
    has_data_source: bool,
    where: str = "Bouton",
) -> str | None:
    missing = [key for key in REQUIRED_FIELDS if key not in entry]
    unknown = sorted(key for key in entry if key not in button_fields | LAYOUT_FIELDS)

    if missing:
        return f"{where} : champ(s) obligatoire(s) manquant(s) {missing}"
    if unknown:
        return f"{where} : champ(s) inconnu(s) {unknown} (faute de frappe ?)"
    if entry["section"] not in known_sections:
        return f"{where} : section inconnue '{entry['section']}' (attendu : {', '.join(known_sections)})"

    error = _coerce_ints(entry, where)
    if error is None and "free_texts" in entry:
        error = _validate_free_texts(entry["free_texts"], where)
    if error is None and entry.get("send_ip") and not has_data_source:
        error = f"{where} : 'send_ip' demande une source de donnees (project.DATA_SOURCE_CLASS)"
    return error


#charge et valide templates.json. known_sections : cles de
#project.SECTIONS ; button_fields : parametres acceptes par SceneButton ;
#has_data_source : False -> send_ip refuse (aucune source a transmettre)
def load_layout(
    known_sections: list[str],
    button_fields: set[str],
    has_data_source: bool,
    path: Path = BUTTONS_CONFIG_PATH,
) -> ButtonsLayout:
    layout = ButtonsLayout()

    if not path.exists():
        layout.errors.append(f"Fichier introuvable : {path}")
        return layout

    try:
        layout.raw = _load_raw(path)
    except (OSError, ValueError) as exc:
        layout.errors.append(str(exc))
        return layout

    layout.can_save = True

    for index, entry in enumerate(layout.raw):
        if not isinstance(entry, dict):
            layout.errors.append(f"Entree #{index + 1} : doit etre un objet {{ ... }}")
            continue
        if entry.get("_example"):
            continue

        where = _describe(index, entry)

        if entry.get("_column_title"):
            missing = [key for key in COLUMN_TITLE_REQUIRED_FIELDS if key not in entry]
            error = (
                f"{where} : titre de colonne incomplet, champ(s) manquant(s) {missing}"
                if missing
                else _coerce_ints(entry, where)
            )
            if error is None and entry["section"] not in known_sections:
                error = f"{where} : section inconnue '{entry['section']}' (attendu : {', '.join(known_sections)})"
            if error:
                layout.errors.append(error)
            else:
                layout.column_titles.append(entry)
            continue

        error = validate_button(entry, known_sections, button_fields, has_data_source, where)
        if error:
            layout.errors.append(error)
        else:
            layout.buttons.append(entry)

    return layout


_merge_bundled_templates_on_startup()
