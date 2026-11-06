from nicegui import app, ui

from app_config import load_config
from casparcg import CasparCG
from data_source import create_data_source
from interface import build_body, build_footer, build_header
from paths import resource_path
from project import APP_NAME, PORT

#favicon de l'onglet navigateur (PAS l'icone du .exe, definie dans app.spec)
ICON_PATH = resource_path("icon.ico")

#reglages machine (config.json), modifiables en direct depuis Parametres
config = load_config()

#instances UNIQUES creees au niveau module, AVANT ui.run() : tout code
#NiceGUI hors d'une fonction @ui.page serait re-execute a chaque connexion
#navigateur (piege "auto-index page") et recreerait des instances jamais
#connectees
caspar = CasparCG(
    config["caspar_ip"],
    config["caspar_port"],
    channel_programm=config["caspar_channel_programme"],
    channel_preview=config["caspar_channel_preview"],
)
#None tant qu'aucune source de donnees n'est implementee (project.py)
data = create_data_source(config)


@ui.page("/")
def index() -> None:
    #dict partage header <-> corps (bascule du mode edition), recree a
    #chaque chargement de page
    hooks: dict = {}
    build_header(caspar, data, config, hooks)
    build_body(caspar, data, config, hooks)
    build_footer(caspar, data, config)


@app.on_startup
async def startup() -> None:
    caspar_error = await caspar.connect()
    print(f"CasparCG connect -> {'OK' if not caspar_error else caspar_error}")

    if data is not None:
        data_error = await data.connect()
        print(f"Source de donnees connect -> {'OK' if not data_error else data_error}")


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        title=APP_NAME,
        port=PORT,
        reload=False,
        favicon=ICON_PATH if ICON_PATH.exists() else None,
    )
