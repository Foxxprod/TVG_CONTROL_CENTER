# Chemins de fichiers, compatibles a la fois avec une execution en mode
# developpement (python main.py depuis le repo) ET en mode installe
# (executable compile via PyInstaller, voir app.spec).
#
#   - resource_path() : ressources EN LECTURE SEULE embarquees dans
#     l'executable (logo, templates.json "de base"). En mode installe,
#     PyInstaller les extrait dans sys._MEIPASS - jamais a utiliser pour
#     ecrire quoi que ce soit.
#
#   - user_data_path() : fichiers UTILISATEUR modifiables par le logiciel
#     (config.json, templates.json une fois copie). En mode installe,
#     %APPDATA%\<APP_SLUG> (ecrivable sans droits admin). En
#     developpement, la racine du projet.

import shutil
import sys
from pathlib import Path

from project import APP_SLUG

#True uniquement dans un executable compile par PyInstaller
FROZEN = getattr(sys, "frozen", False)


def resource_path(*parts: str) -> Path:
    if FROZEN:
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    else:
        base = Path(__file__).parent

    return base.joinpath(*parts)


def user_data_path(*parts: str) -> Path:
    if FROZEN:
        import os

        base = Path(os.environ.get("APPDATA", Path.home())) / APP_SLUG
        base.mkdir(parents=True, exist_ok=True)
    else:
        base = Path(__file__).parent

    return base.joinpath(*parts)


#garantit qu'un fichier utilisateur existe, en le copiant depuis la
#ressource embarquee du meme nom s'il est absent (tout premier lancement
#en mode installe). Ne touche jamais a un fichier utilisateur existant.
def ensure_user_file(filename: str) -> Path:
    target = user_data_path(filename)

    if FROZEN and not target.exists():
        source = resource_path(filename)
        if source.exists():
            shutil.copy(source, target)

    return target
