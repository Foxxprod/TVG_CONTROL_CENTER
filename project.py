# Reglages PROPRES A CE PROJET de Control Center.
#
# C'est le SEUL fichier Python a adapter pour un nouveau projet (avec
# templates.json pour le catalogue de boutons). Tout le reste (casparcg.py,
# scene_button.py, interface.py, media_browser.py...) est le noyau commun :
# meme design, meme logique preview/programme d'un projet a l'autre.

#nom affiche (onglet navigateur, titre par defaut du header)
APP_NAME = "CONTROL CENTER"

#nom technique sans espace : dossier %APPDATA%\<APP_SLUG> en mode installe,
#nom de l'executable compile (voir app.spec)
APP_SLUG = "ControlCenter"

#port HTTP local de l'interface NiceGUI
PORT = 8081

#logo du header (ressource embarquee, voir paths.resource_path)
LOGO_FILE = ("assets", "logo.png")

#sections du corps de page, dans l'ordre d'affichage (haut -> bas) :
#(cle utilisee dans templates.json, titre affiche)
SECTIONS: list[tuple[str, str]] = [
    ("opening", "OUVERTURE"),
    ("live", "DIRECT"),
    ("closing", "FERMETURE"),
]

#section qui absorbe toute la hauteur restante (les autres se reduisent a
#leur contenu) - None = aucune
GROW_SECTION: str | None = "live"

#facteur de reduction du corps de page (propriete CSS zoom, < 1 = plus petit)
BODY_ZOOM = 0.8

#source de donnees externe (WebSocket, API, fichier...) - None tant
#qu'aucune n'est implementee : RIEN ne s'affiche alors dans l'interface
#(ni statut dans le header, ni reglages, ni bouton "donnees"). Pour en
#brancher une : creer une sous-classe de data_source.DataSource puis
#  from my_source import MySource
#  DATA_SOURCE_CLASS = MySource
DATA_SOURCE_CLASS = None

#boutons bascule du header (ex: mire, bandeau logo permanent), sur un
#layer DEDIE hors de la grille. Chaque entree :
#  {"label": "TEST PATTERN", "template": "test_pattern", "layer": 900,
#   "channels": ["prw", "pgm"], "confirm": True, "color": "orange",
#   "keep_on_emergency": False}
HEADER_TOGGLES: list[dict] = []

#boutons du footer qui invoquent une fonction exposee par TOUS les
#templates actuellement au programme (CG INVOKE). Chaque entree :
#  {"label": "SPONSOR IN", "function": "sponsor_in", "icon": "loyalty",
#   "color": "purple"}
FOOTER_INVOKES: list[dict] = []

#second onglet MEDIAS (bibliotheque CasparCG + lecture sur un layer au choix)
MEDIA_TAB_ENABLED = True
MEDIA_DEFAULT_LAYER = 50
