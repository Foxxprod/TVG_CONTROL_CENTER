"""Cree un nouveau projet Control Center CasparCG a partir de ce depot template.

usage :
    py -3 tools/new_project.py DEST --name "TENNIS - CONTROL CENTER" --slug TennisControlCenter [--port 8081]

Copie la base (racine du depot, sans .git / docs / tools / README) dans DEST
(qui doit etre absent ou vide), puis renseigne APP_NAME / APP_SLUG / PORT
dans project.py. Ne touche a rien d'autre : les sections, boutons et options
se reglent ensuite dans project.py et templates.json.
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent

#ce qui appartient au depot template et pas a un projet genere
IGNORED = ("__pycache__", "config.json", ".git", "docs", "tools", "README.md",
           "build", "dist")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dest")
    parser.add_argument("--name", required=True, help="nom affiche (APP_NAME)")
    parser.add_argument("--slug", required=True, help="nom technique sans espace (APP_SLUG)")
    parser.add_argument("--port", type=int, default=8081)
    args = parser.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9_-]+", args.slug):
        print("--slug : lettres, chiffres, _ ou - uniquement (sert de nom de dossier et d'exe)")
        return 1

    dest = Path(args.dest).resolve()
    #empeche de copier le template dans lui-meme (copie recursive infinie)
    if dest == TEMPLATE or TEMPLATE in dest.parents:
        print("DEST ne peut pas etre a l'interieur du depot template")
        return 1
    if dest.exists() and any(dest.iterdir()):
        print(f"{dest} existe deja et n'est pas vide - abandon (rien n'a ete ecrase)")
        return 1

    shutil.copytree(TEMPLATE, dest, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(*IGNORED))

    project = dest / "project.py"
    text = project.read_text(encoding="utf-8")
    text = re.sub(r'^APP_NAME = ".*"$', f'APP_NAME = "{args.name}"', text, flags=re.M)
    text = re.sub(r'^APP_SLUG = ".*"$', f'APP_SLUG = "{args.slug}"', text, flags=re.M)
    text = re.sub(r"^PORT = \d+$", f"PORT = {args.port}", text, flags=re.M)
    with project.open("w", encoding="utf-8", newline="\n") as f:
        f.write(text)

    context = dest / "PROJECT_CONTEXT.txt"
    context_text = context.read_text(encoding="utf-8").replace("__APP_NAME__", args.name)
    with context.open("w", encoding="utf-8", newline="\n") as f:
        f.write(context_text)

    print(f"Projet cree dans {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
