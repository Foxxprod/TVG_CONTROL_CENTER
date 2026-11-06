# Persistance de la configuration utilisateur (config.json) : theme clair/
# sombre, titre du logiciel, titre d'epreuve (optionnel), adresse/port
# CasparCG et numeros de channel preview/programme, adresse/port de la
# source de donnees (utilises seulement si project.DATA_SOURCE_CLASS est
# defini).
#
# Lue une fois au demarrage (main.py) dans un dict simple partage par
# reference avec interface.build_header, qui le modifie et le sauvegarde
# depuis la boite de dialogue Parametres. config.json n'est PAS commite
# (reglage machine), contrairement a templates.json.

import json
from pathlib import Path

from paths import user_data_path
from project import APP_NAME

CONFIG_PATH = user_data_path("config.json")

DEFAULT_CONFIG = {
    "dark_mode": False,
    "software_title": APP_NAME,
    #titre d'epreuve/d'emission affiche a cote du titre logiciel - peut
    #rester vide (la zone est alors masquee)
    "event_title": "",
    "caspar_ip": "127.0.0.1",
    "caspar_port": 5250,
    "caspar_channel_preview": 1,
    "caspar_channel_programme": 2,
    "data_ip": "127.0.0.1",
    "data_port": 8765,
}


#lit config.json et complete les champs manquants avec les valeurs par
#defaut (fichier absent ou incomplet, ex: toute premiere execution). Un
#fichier illisible ne bloque jamais le demarrage : defauts + message.
def load_config(path: Path = CONFIG_PATH) -> dict:
    config = dict(DEFAULT_CONFIG)

    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                config.update(json.load(f))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"config.json illisible ({exc}), valeurs par defaut utilisees")

    return config


#reecrit integralement config.json (le cree si absent)
def save_config(config: dict, path: Path = CONFIG_PATH) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
