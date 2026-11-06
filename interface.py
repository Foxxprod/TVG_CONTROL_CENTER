import inspect
from datetime import datetime

from nicegui import ui

import media_browser
from app_config import save_config
from button_editor import open_button_editor
from buttons_config import load_layout, save_button_configs
from casparcg import CasparCG
from data_source import DataSource
from paths import resource_path
from project import (
    BODY_ZOOM,
    FOOTER_INVOKES,
    GROW_SECTION,
    HEADER_TOGGLES,
    LOGO_FILE,
    MEDIA_DEFAULT_LAYER,
    MEDIA_TAB_ENABLED,
    SECTIONS,
)
from scene_button import SceneButton

#ressource EN LECTURE SEULE embarquee dans l'executable (voir paths.py)
LOGO_PATH = resource_path(*LOGO_FILE)

#parametres acceptes dans templates.json pour un bouton = parametres du
#constructeur SceneButton (hors objets injectes par le code) - sert a
#detecter les fautes de frappe (voir buttons_config.load_layout)
BUTTON_FIELDS = set(inspect.signature(SceneButton.__init__).parameters) - {
    "self", "caspar", "data", "on_config_changed", "edit_actions",
}

#classes communes des petits boutons ronds/pilules du header
HEADER_ICON_BUTTON_CLASSES = (
    "border border-slate-600 bg-slate-700/40 hover:bg-slate-700/60 text-slate-300 rounded-full"
)


#classes d'un bouton "pilule" a contour colore (header/footer), meme
#recette pour toutes les couleurs : contour plein, fond a 20%, texte clair
def pill_classes(color: str, extra: str = "") -> str:
    return (
        f"border border-{color}-500 bg-{color}-600/20 hover:bg-{color}-600/30 "
        f"text-{color}-400 font-bold rounded-full {extra}"
    ).strip()


#etat "enclenche" des HEADER_TOGGLES, hors build_header pour survivre a un
#rechargement de page (meme principe que SceneButton._active_pgm)
_toggle_active: dict[str, bool] = {}


#case de statut en 2 moities egales : titre en haut, statut en bas.
#Tooltip au survol (IP:port + ping).
def _build_status_box(title: str) -> tuple[ui.row, ui.icon, ui.label, ui.tooltip]:
    with ui.column().classes("h-full w-32 justify-between border-l border-slate-700 gap-0"):
        with ui.row().classes("flex-1 w-full items-center justify-center px-3"):
            ui.label(title).classes(
                "text-sm font-bold tracking-wide text-slate-300 whitespace-nowrap"
            )

        with ui.row().classes(
            replace="flex-1 w-full flex items-center justify-center gap-1 flex-nowrap cursor-help"
        ) as status_row:
            icon = ui.icon("wifi_off").classes("text-base")
            status_label = ui.label("DECONNECTE").classes("text-xs font-bold whitespace-nowrap")
            tooltip = ui.tooltip("").classes("bg-slate-700 text-white font-bold")

    return status_row, icon, status_label, tooltip


#case horloge (label en haut, valeur en gros en dessous), fond blanc
def _build_clock_box(title: str, border_left: bool) -> ui.label:
    border_classes = "border-l border-slate-300 " if border_left else ""
    with ui.column().classes(f"h-full justify-center items-center {border_classes}px-4 gap-0"):
        ui.label(title).classes("text-[10px] font-bold tracking-wide text-slate-500 whitespace-nowrap")
        value_label = ui.label().classes(
            "text-2xl font-mono font-bold leading-none text-slate-900 whitespace-nowrap"
        )

    return value_label


#vert si connecte, rouge clignotant sinon
def _apply_status(
    row: ui.row, icon: ui.icon, label: ui.label, tooltip: ui.tooltip, connected: bool, detail: str
) -> None:
    base = "flex-1 w-full flex items-center justify-center gap-1 flex-nowrap cursor-help "

    if connected:
        row.classes(replace=base + "bg-green-600/20 text-green-400")
    else:
        row.classes(replace=base + "bg-red-600/20 text-red-400 animate-pulse")

    icon.name = "wifi" if connected else "wifi_off"
    label.text = "CONNECTE" if connected else "DECONNECTE"
    tooltip.text = detail


def _status_detail(ip: str, port: int, connected: bool, ping_ms: float | None) -> str:
    detail = f"{ip}:{port}"
    if connected and ping_ms is not None:
        detail += f" - ping {ping_ms:.0f} ms"
    return detail


#barre d'outils du haut. `data` vaut None tant qu'aucune source de
#donnees n'est implementee : tout ce qui la concerne est alors omis.
#`hooks` : dict partage avec build_body (cree par chargement de page dans
#main.py) - build_header s'execute AVANT build_body, mais le clic sur le
#bouton d'edition n'arrive qu'apres que build_body l'ait peuple.
def build_header(caspar: CasparCG, data: DataSource | None, config: dict, hooks: dict) -> None:
    toggle_buttons: dict[str, ui.button] = {}
    edit_state = {"value": False}

    def edit_button_classes() -> str:
        if edit_state["value"]:
            return pill_classes("sky", "rounded-full animate-pulse")
        return HEADER_ICON_BUTTON_CLASSES

    #bascule le MODE EDITION de la grille (voir build_body)
    def on_edit_click() -> None:
        set_edit_mode = hooks.get("set_edit_mode")
        if set_edit_mode is None or not set_edit_mode(not edit_state["value"]):
            return
        edit_state["value"] = not edit_state["value"]
        edit_button.classes(replace=edit_button_classes())

    def toggle_classes(toggle: dict, active: bool) -> str:
        if active:
            return pill_classes(toggle.get("color", "orange"), "px-4 animate-pulse")
        return f"{HEADER_ICON_BUTTON_CLASSES} font-bold px-4"

    #clear complet des deux channels (tout producer, sans animation) +
    #remise a idle de tous les boutons et medias. Les HEADER_TOGGLES
    #marques keep_on_emergency sont rejoues aussitot.
    async def on_emergency_click() -> None:
        prw_response, pgm_response = await caspar.emergency_all_out()
        SceneButton.reset_all()
        media_browser.reset_media()

        for toggle in HEADER_TOGGLES:
            label = toggle["label"]
            if not _toggle_active.get(label):
                continue
            if toggle.get("keep_on_emergency"):
                for channel in toggle.get("channels", ["pgm"]):
                    await caspar.play_template(channel, toggle["template"], layer=toggle["layer"])
            else:
                _toggle_active[label] = False
                toggle_buttons[label].classes(replace=toggle_classes(toggle, False))

        errors = [r.message for r in (prw_response, pgm_response) if r.is_error]
        if errors:
            ui.notify(f"Erreur lors de l'emergency all out : {'; '.join(errors)}", type="negative")
        else:
            ui.notify("Emergency all out effectue", type="warning")

    #bascule d'un HEADER_TOGGLE : clic = envoi (avec confirmation si
    #"confirm"), reclic = clear direct, sans confirmation
    async def on_toggle_click(toggle: dict) -> None:
        label = toggle["label"]
        channels = toggle.get("channels", ["pgm"])

        if _toggle_active.get(label):
            responses = [await caspar.clear(channel, layer=toggle["layer"]) for channel in channels]
            _toggle_active[label] = False
            toggle_buttons[label].classes(replace=toggle_classes(toggle, False))
            errors = [r.message for r in responses if r.is_error]
            if errors:
                ui.notify(f"Erreur lors du retrait de {label} : {'; '.join(errors)}", type="negative")
            else:
                ui.notify(f"{label} retire", type="positive")
            return

        if toggle.get("confirm"):
            with ui.dialog() as confirm_dialog, ui.card():
                ui.label(f"Envoyer {label} ?").classes("text-base font-bold")
                ui.label(
                    f"Le template {toggle['template']} sera envoye sur : {', '.join(channels).upper()}."
                ).classes("text-sm text-slate-500")
                with ui.row().classes("justify-end gap-2 w-full mt-2"):
                    ui.button("Annuler", on_click=lambda: confirm_dialog.submit(False))
                    ui.button("Envoyer", on_click=lambda: confirm_dialog.submit(True)).classes(
                        "bg-slate-800 text-white"
                    )
            if not await confirm_dialog:
                return

        responses = [
            await caspar.play_template(
                channel, toggle["template"], data={"_label": f"GFX {channel.upper()}"},
                layer=toggle["layer"],
            )
            for channel in channels
        ]
        errors = [r.message for r in responses if r.is_error]
        if errors:
            ui.notify(f"Erreur lors de l'envoi de {label} : {'; '.join(errors)}", type="negative")
            return

        _toggle_active[label] = True
        toggle_buttons[label].classes(replace=toggle_classes(toggle, True))
        ui.notify(f"{label} envoye", type="positive")

    #fond de la PAGE (header/footer restent sombres en permanence)
    def apply_body_background() -> None:
        ui.query("body").classes(replace="bg-slate-900" if config["dark_mode"] else "bg-slate-50")

    #enregistre, sauvegarde et applique IMMEDIATEMENT les parametres (theme,
    #titres, reconnexions) sans redemarrer le logiciel
    async def on_settings_save() -> None:
        config["dark_mode"] = dark_switch.value
        config["software_title"] = title_input.value or config["software_title"]
        config["event_title"] = event_title_input.value or ""
        config["caspar_ip"] = caspar_ip_input.value or config["caspar_ip"]
        config["caspar_port"] = int(caspar_port_input.value or config["caspar_port"])
        config["caspar_channel_preview"] = int(prw_channel_input.value or config["caspar_channel_preview"])
        config["caspar_channel_programme"] = int(pgm_channel_input.value or config["caspar_channel_programme"])
        if data is not None:
            config["data_ip"] = data_ip_input.value or config["data_ip"]
            config["data_port"] = int(data_port_input.value or config["data_port"])

        save_config(config)

        dark_mode.set_value(config["dark_mode"])
        apply_body_background()
        SceneButton.set_dark_mode(config["dark_mode"])
        software_title_label.text = config["software_title"]

        errors = []
        if data is not None:
            errors.append(await data.change_connection(config["data_ip"], config["data_port"]))
        errors.append(
            await caspar.change_connection(
                config["caspar_ip"],
                config["caspar_port"],
                config["caspar_channel_preview"],
                config["caspar_channel_programme"],
            )
        )

        settings_dialog.close()

        errors = [e for e in errors if e]
        if errors:
            ui.notify(f"Parametres enregistres, mais erreur de connexion : {'; '.join(errors)}", type="warning")
        else:
            ui.notify("Parametres enregistres et appliques", type="positive")

    fullscreen = ui.fullscreen()

    #boite "Donnees recues" : dernier message brut de la source de donnees
    #(arborescence repliable), rafraichie seulement quand elle est ouverte
    data_editor = None
    if data is not None:
        with ui.dialog() as data_dialog, ui.card().classes("gap-3 w-[52rem] max-w-[95vw]"):
            ui.label("Donnees recues").classes("text-lg font-bold")
            data_editor = ui.json_editor({"content": {"json": {}}, "readOnly": True}).classes(
                "w-full h-[65vh]"
            )
            with ui.row().classes("justify-end w-full"):
                ui.button("Fermer", on_click=data_dialog.close)

    def refresh_data_dialog() -> None:
        if data_editor is None or not data_dialog.value:
            return
        data_editor.properties["content"] = {"json": data.latest_data or {}}
        data_editor.update()

    with ui.dialog() as settings_dialog, ui.card().classes("gap-3 w-[28rem]"):
        ui.label("Parametres").classes("text-lg font-bold")

        dark_switch = ui.switch("Mode sombre", value=config["dark_mode"])
        title_input = ui.input("Titre du logiciel", value=config["software_title"]).classes("w-full")
        event_title_input = ui.input(
            "Titre de l'epreuve (optionnel)", value=config["event_title"]
        ).classes("w-full")

        if data is not None:
            ui.label(f"Source de donnees ({data.status_title})").classes(
                "text-xs font-bold uppercase tracking-wide text-slate-500 mt-2"
            )
            with ui.row().classes("gap-2 w-full"):
                data_ip_input = ui.input("IP", value=config["data_ip"]).classes("flex-1")
                data_port_input = ui.number(
                    "Port", value=config["data_port"], min=1, max=65535, step=1
                ).classes("w-28")

        ui.label("CasparCG").classes("text-xs font-bold uppercase tracking-wide text-slate-500 mt-2")
        with ui.row().classes("gap-2 w-full"):
            caspar_ip_input = ui.input("IP", value=config["caspar_ip"]).classes("flex-1")
            caspar_port_input = ui.number(
                "Port", value=config["caspar_port"], min=1, max=65535, step=1
            ).classes("w-28")
        with ui.row().classes("gap-2 w-full"):
            prw_channel_input = ui.number(
                "Channel preview", value=config["caspar_channel_preview"], min=1, step=1
            ).classes("flex-1")
            pgm_channel_input = ui.number(
                "Channel programme", value=config["caspar_channel_programme"], min=1, step=1
            ).classes("flex-1")

        with ui.row().classes("justify-end gap-2 w-full mt-2"):
            ui.button("Annuler", on_click=settings_dialog.close)
            ui.button("Enregistrer", on_click=on_settings_save).classes("bg-slate-800 text-white")

    dark_mode = ui.dark_mode(config["dark_mode"])
    apply_body_background()
    SceneButton.set_dark_mode(config["dark_mode"])

    #padding HORIZONTAL par defaut de NiceGUI neutralise pour aligner le
    #corps sur le header/footer (m-3). JAMAIS padding-top/bottom : Quasar
    #s'en sert pour pousser le contenu sous le header fixe.
    ui.query(".nicegui-content").style("padding-left: 0; padding-right: 0;")

    #wrap=False PARTOUT : ui.header()/ui.row() passent a la ligne par
    #defaut. Le groupe de DROITE (pilotage) garde sa taille (flex-shrink 0),
    #seul le texte de GAUCHE retrecit (flex-1 min-w-0 + clamp + truncate).
    with ui.header(wrap=False).classes(
        "items-stretch justify-between bg-slate-900 text-white p-0 m-3 rounded-2xl overflow-hidden"
    ):
        #flex-1 : le groupe de gauche occupe toute la place laissee par le
        #groupe de droite (sinon ses enfants flex-1 min-w-0 se reduisent
        #au minimum et le titre est tronque meme sur un grand ecran)
        with ui.row(wrap=False).classes("items-stretch gap-0 min-w-0 flex-1"):
            with ui.row().classes("items-center px-4 py-3"):
                ui.image(LOGO_PATH).classes("h-10 w-16")

            #largeur naturelle, mais peut retrecir (flex: 0 1 auto) - le
            #panneau blanc ne s'etire pas inutilement sur un grand ecran
            with ui.row().classes("h-full items-center bg-white px-4 min-w-0").style("flex: 0 1 auto;"):
                software_title_label = ui.label(config["software_title"]).classes(
                    "font-bold text-slate-900 truncate min-w-0"
                ).style("font-size: clamp(0.7rem, 1.4vw, 1.125rem);")

            #titre d'epreuve (config ou source de donnees) - masque si vide
            event_title_row = ui.row(wrap=False).classes("items-center gap-1 px-4 py-3 min-w-0 flex-1")
            with event_title_row:
                event_title_label = ui.label().classes(
                    "text-sm font-bold text-slate-300 truncate min-w-0"
                )

        with ui.row(wrap=False).classes("items-stretch gap-0").style("flex-shrink: 0;"):
            with ui.row(wrap=False).classes("items-center gap-2 px-4 py-3"):
                ui.button(icon="fullscreen", color=None, on_click=fullscreen.toggle).classes(
                    HEADER_ICON_BUTTON_CLASSES
                ).props("round").bind_icon_from(
                    fullscreen, "value", backward=lambda v: "fullscreen_exit" if v else "fullscreen"
                ).tooltip("Plein ecran")

                if data is not None:
                    ui.button(icon="data_object", color=None, on_click=data_dialog.open).classes(
                        HEADER_ICON_BUTTON_CLASSES
                    ).props("round").tooltip("Donnees recues")

                edit_button = ui.button(icon="edit", color=None, on_click=on_edit_click).classes(
                    edit_button_classes()
                ).props("round").tooltip("Mode edition (ajouter/modifier/supprimer des boutons)")

                ui.button(icon="settings", color=None, on_click=settings_dialog.open).classes(
                    HEADER_ICON_BUTTON_CLASSES
                ).props("round").tooltip("Parametres")

                ui.button(
                    "EMERGENCY ALL OUT", icon="warning", color=None, on_click=on_emergency_click
                ).classes(
                    "border border-red-500 bg-red-600/20 hover:bg-red-600/30 "
                    "text-red-400 font-bold rounded-full px-4"
                )

                for toggle in HEADER_TOGGLES:
                    toggle_buttons[toggle["label"]] = ui.button(
                        toggle["label"],
                        color=None,
                        on_click=lambda _, t=toggle: on_toggle_click(t),
                    ).classes(toggle_classes(toggle, _toggle_active.get(toggle["label"], False)))

            caspar_row, caspar_icon, caspar_label, caspar_tooltip = _build_status_box("CASPAR CG")
            if data is not None:
                data_row, data_icon, data_label, data_tooltip = _build_status_box(data.status_title)

            with ui.row(wrap=False).classes("h-full items-stretch border-l border-slate-700 bg-white gap-0"):
                clock_label = _build_clock_box("HEURE", border_left=False)

    def update_header() -> None:
        event_title = (data.event_title if data is not None else "") or config["event_title"]
        event_title_label.text = event_title
        event_title_row.visible = bool(event_title)

        _apply_status(
            caspar_row, caspar_icon, caspar_label, caspar_tooltip, caspar.connected,
            _status_detail(caspar.ip, caspar.port, caspar.connected, caspar.last_ping_ms),
        )
        if data is not None:
            _apply_status(
                data_row, data_icon, data_label, data_tooltip, data.connected,
                _status_detail(data.ip, data.port, data.connected, data.last_ping_ms),
            )

        clock_label.text = datetime.now().strftime("%H:%M:%S")
        refresh_data_dialog()

    update_header()
    ui.timer(1.0, update_header)


#bandeau rouge listant les erreurs de templates.json (en haut de l'onglet
#GRAPHIQUES) - le reste de l'interface reste utilisable
def _build_layout_errors(errors: list[str], can_save: bool) -> None:
    with ui.column().classes(
        "w-full border border-red-500 bg-red-600/10 rounded-2xl p-3 gap-1"
    ):
        with ui.row(wrap=False).classes("w-full items-center gap-2"):
            ui.icon("error").classes("text-red-500 text-xl")
            ui.label("templates.json contient des erreurs").classes("text-sm font-bold text-red-500")
            ui.space()
            ui.button("Recharger", icon="refresh", color=None, on_click=ui.navigate.reload).classes(
                pill_classes("red", "px-3")
            ).props("dense")
        for error in errors:
            ui.label(f"- {error}").classes("text-xs text-red-500 font-mono")
        if not can_save:
            ui.label(
                "Aucun bouton charge. Le fichier ne sera pas reecrit par le logiciel tant "
                "qu'il n'est pas corrige."
            ).classes("text-xs text-red-400 italic")
        else:
            ui.label("Les entrees en erreur sont ignorees, les autres sont affichees.").classes(
                "text-xs text-red-400 italic"
            )


#corps de page : onglets GRAPHIQUES (grille de boutons) et MEDIAS
#(si project.MEDIA_TAB_ENABLED). Dans GRAPHIQUES, une carte par section
#(project.SECTIONS) empilee verticalement ; GROW_SECTION absorbe la
#hauteur restante. Chaque section est une VRAIE grille CSS (grid-row/
#grid-column explicites) pour que la colonne N s'aligne sur toutes les
#lignes ; la ligne 1 de chaque grille est reservee aux titres de colonne.
#
#La grille est construite par render(), rappelable a tout moment (mode
#edition active/desactive, bouton ajoute/modifie/supprime) : templates.json
#est relu, la grille reconstruite, et chaque nouveau SceneButton reprend
#l'etat en direct de l'ancienne instance du meme bouton (SceneButton.adopt)
#- un graphique a l'antenne reste suivi, sans recharger la page.
#
#MODE EDITION (hooks["set_edit_mode"], bascule depuis le header) :
#  - boutons fantomes "+" en bas de chaque colonne et au bout de chaque
#    ligne -> editeur d'attributs (button_editor.py) pour creer un bouton
#  - crayon/poubelle sur chaque bouton (et clic = modifier)
#  - un bouton en preview/a l'antenne ne peut etre ni modifie ni supprime
def build_body(caspar: CasparCG, data: DataSource | None, config: dict, hooks: dict) -> None:
    section_keys = [key for key, _ in SECTIONS]
    section_grids: dict[str, ui.element] = {}
    section_cards: dict[str, ui.column] = {}
    has_data_source = data is not None

    state = {"layout": None, "edit": False, "first_render": True}
    page_buttons: list[SceneButton] = []

    def section_card_classes(key: str) -> str:
        grow_classes = "flex-1 " if key == GROW_SECTION else ""
        if SceneButton._dark_mode:
            return (
                f"w-full {grow_classes}min-h-0 border border-slate-700 rounded-2xl "
                "bg-slate-800 p-3 gap-2 overflow-auto"
            )
        return (
            f"w-full {grow_classes}min-h-0 border border-slate-200 rounded-2xl "
            "bg-white p-3 gap-2 overflow-auto"
        )

    def refresh_section_cards(_dark: bool) -> None:
        for key, card in section_cards.items():
            card.classes(replace=section_card_classes(key))

    SceneButton.on_dark_mode_change(refresh_section_cards)

    #persiste templates.json (options de free_text ajoutees en direct,
    #mode edition) - jamais si le fichier n'a pas pu etre lu (il serait
    #ecrase par du vide)
    def persist_templates() -> bool:
        layout = state["layout"]
        if layout is None or not layout.can_save:
            ui.notify("templates.json illisible : corrigez-le avant de modifier les boutons", type="negative")
            return False
        save_button_configs(layout.raw)
        return True

    # ------------------------------------------------------------------
    # mode edition
    # ------------------------------------------------------------------

    def find_button(entry: dict) -> SceneButton | None:
        return next((b for b in page_buttons if b.entry is entry), None)

    def check_idle(entry: dict) -> bool:
        button = find_button(entry)
        if button is not None and button._state != "idle":
            ui.notify(
                f"'{entry['label']}' est en preview/a l'antenne : retirez-le avant de le modifier",
                type="warning",
            )
            return False
        return True

    async def edit_entry(entry: dict | None, position: tuple[str, int, int] | None = None) -> None:
        if entry is not None and not check_idle(entry):
            return

        with dialog_host:
            new = await open_button_editor(entry, position, BUTTON_FIELDS, has_data_source)
        if new is None:
            return

        raw = state["layout"].raw
        if entry is None:
            raw.append(new)
        else:
            #remplacement EN PLACE (meme position dans le fichier)
            raw[next(i for i, e in enumerate(raw) if e is entry)] = new

        if persist_templates():
            ui.notify(f"Bouton '{new['label']}' enregistre", type="positive")
            render()

    async def delete_entry(entry: dict) -> None:
        if not check_idle(entry):
            return

        with dialog_host, ui.dialog() as dialog, ui.card():
            ui.label(f"Supprimer le bouton '{entry['label']}' ?").classes("text-base font-bold")
            ui.label("Il sera retire de templates.json.").classes("text-sm text-slate-500")
            with ui.row().classes("justify-end gap-2 w-full"):
                ui.button("Annuler", on_click=lambda: dialog.submit(False))
                ui.button("Supprimer", color="red", on_click=lambda: dialog.submit(True))

        confirmed = await dialog
        dialog.delete()
        if not confirmed:
            return

        raw = state["layout"].raw
        raw[:] = [e for e in raw if e is not entry]
        if persist_templates():
            ui.notify(f"Bouton '{entry['label']}' supprime", type="positive")
            render()

    #actions SANS argument (NiceGUI passerait l'evenement de clic a une
    #lambda a parametre par defaut, ecrasant l'entree)
    def edit_actions_for(entry: dict):
        async def edit() -> None:
            await edit_entry(entry)

        async def delete() -> None:
            await delete_entry(entry)

        return edit, delete

    def set_edit_mode(enabled: bool) -> bool:
        if enabled and not (state["layout"] and state["layout"].can_save):
            ui.notify("templates.json illisible : mode edition indisponible", type="negative")
            return False
        state["edit"] = enabled
        render()
        return True

    hooks["set_edit_mode"] = set_edit_mode

    # ------------------------------------------------------------------
    # construction de la grille
    # ------------------------------------------------------------------

    def place(section: str, row: int, column: int) -> ui.column:
        with section_grids[section]:
            return ui.column().classes("gap-2").style(f"grid-row: {row + 1}; grid-column: {column};")

    #fantomes "+" :
    #  - bas de colonne : DANS la case du dernier bouton de la colonne (les
    #    elements d'une case s'empilent) - le nouveau bouton se colle juste
    #    sous le dernier. Une nouvelle ligne de grille le mettrait sous
    #    l'element le plus HAUT de toute la ligne (hauteur de ligne
    #    partagee par toutes les colonnes), loin de sa colonne.
    #  - bout de ligne : nouvelle case, colonne suivante
    #  - colonne avec seulement un titre, ou section vide : ligne 1
    def ghost_positions(buttons: list[dict], titles: list[dict]) -> dict[str, set[tuple[int, int]]]:
        positions: dict[str, set[tuple[int, int]]] = {key: set() for key in section_keys}

        for key in section_keys:
            cells = {(b.get("row", 1), b.get("column", 1)) for b in buttons if b["section"] == key}
            columns = {c for _, c in cells} | {t["column"] for t in titles if t["section"] == key}
            rows = {r for r, _ in cells}

            for column in columns:
                last_row = max((r for r, c in cells if c == column), default=1)
                positions[key].add((last_row, column))
            for row in rows:
                last_column = max(c for r, c in cells if r == row)
                positions[key].add((row, last_column + 1))
            if not positions[key]:
                positions[key].add((1, 1))

        return positions

    #ghost DANS une case existante (en dernier, sous ses boutons) ou dans
    #une nouvelle case
    def add_ghost(section: str, row: int, column: int, cells: dict) -> None:
        cell = cells.get((section, row, column)) or place(section, row, column)
        with cell:
            ghost = ui.row().classes(
                "w-64 items-center justify-center py-2 rounded-full border-2 border-dashed "
                "border-sky-400/70 text-sky-500 hover:border-sky-500 hover:bg-sky-500/10 cursor-pointer"
            )
            with ghost:
                ui.icon("add").classes("text-xl")
            ghost.on("click", lambda _, p=(section, row, column): edit_entry(None, p))
            ghost.tooltip(f"Ajouter un bouton (ligne {row}, colonne {column})")

    def render() -> None:
        layout = load_layout(section_keys, BUTTON_FIELDS, has_data_source)
        state["layout"] = layout
        edit = state["edit"]

        if state["first_render"]:
            for error in layout.errors:
                print(f"[templates.json] {error}")

        banner_host.clear()
        with banner_host:
            if edit:
                with ui.row(wrap=False).classes(
                    "w-full items-center gap-2 border border-sky-500 bg-sky-500/10 rounded-2xl px-3 py-2"
                ):
                    ui.icon("edit").classes("text-sky-500 text-xl")
                    ui.label(
                        "MODE EDITION - cliquez sur + pour ajouter un bouton, sur un bouton pour le "
                        "modifier, sur la poubelle pour le supprimer."
                    ).classes("text-sm font-bold text-sky-600")
            if layout.errors:
                _build_layout_errors(layout.errors, layout.can_save)

        old_buttons = list(page_buttons)
        page_buttons.clear()
        for grid in section_grids.values():
            grid.clear()

        cells: dict[tuple[str, int, int], ui.column] = {}
        for entry in layout.buttons:
            kwargs = {k: v for k, v in entry.items() if k not in ("_comment", "section", "row", "column")}
            cell_key = (entry["section"], entry.get("row", 1), entry.get("column", 1))
            if cell_key not in cells:
                cells[cell_key] = place(*cell_key)
            with cells[cell_key]:
                button = SceneButton(
                    caspar,
                    data,
                    on_config_changed=persist_templates,
                    edit_actions=edit_actions_for(entry) if edit else None,
                    **kwargs,
                )
            #lien vers SA definition dans templates.json (mode edition)
            button.entry = entry
            page_buttons.append(button)

        #reprise de l'etat en direct des anciennes instances (meme identite)
        unmatched = list(old_buttons)
        for button in page_buttons:
            old = next((o for o in unmatched if o.identity == button.identity), None)
            if old is not None:
                unmatched.remove(old)
                button.adopt(old)
        for old in old_buttons:
            SceneButton.forget(old)

        #un seul titre par (section, column), le dernier l'emporte.
        #margin-bottom negatif : colle le titre a la premiere ligne de
        #boutons sans toucher au gap entre les lignes suivantes
        titles = {(t["section"], t["column"]): t["title"] for t in layout.column_titles}
        for (section, column), title in titles.items():
            with section_grids[section]:
                ui.label(title).classes(
                    "text-sm font-bold uppercase tracking-wide text-slate-400 text-center"
                ).style(f"grid-row: 1; grid-column: {column}; margin-bottom: -14px;")

        if edit:
            for section, positions in ghost_positions(layout.buttons, layout.column_titles).items():
                for row, column in sorted(positions):
                    add_ghost(section, row, column, cells)

        if state["first_render"] and layout.errors:
            ui.notify(
                f"templates.json : {len(layout.errors)} erreur(s), voir le bandeau rouge",
                type="negative",
                timeout=8000,
            )
        state["first_render"] = False

    #hauteur disponible = viewport - (header + footer + barre d'onglets).
    #zoom (BODY_ZOOM) : la hauteur brute est divisee par le zoom pour que
    #la hauteur RENDUE reste correcte (le zoom retrecit aussi la boite)
    tabs_height = 44 if MEDIA_TAB_ENABLED else 0
    panel_style = f"height: calc((100vh - {190 + tabs_height}px) / {BODY_ZOOM}); zoom: {BODY_ZOOM};"

    def build_graphics_panel() -> None:
        nonlocal banner_host
        with ui.column().classes("w-full gap-3").style(panel_style):
            banner_host = ui.column().classes("w-full gap-2 empty:hidden")

            for key, title in SECTIONS:
                card = ui.column().classes(section_card_classes(key))
                section_cards[key] = card
                with card:
                    ui.label(title).classes("text-sm font-bold tracking-wide text-slate-500")
                    section_grids[key] = ui.element("div").classes(
                        "w-full grid gap-4 items-start justify-items-center pt-2"
                    ).style("grid-auto-columns: max-content; grid-auto-rows: max-content;")

    banner_host: ui.column | None = None
    #hote des boites de dialogue du mode edition, HORS des grilles (un
    #element cree dans une grille y occuperait une case)
    dialog_host = ui.element("div").classes("hidden")

    with ui.column().classes("w-full px-3 pb-3 gap-2"):
        if MEDIA_TAB_ENABLED:
            with ui.tabs().props(
                'dense no-caps inline-label indicator-color="transparent" '
                'active-class="bg-slate-700 text-white"'
            ).classes("self-start bg-slate-900 text-slate-400 rounded-full overflow-hidden") as tabs:
                graphics_tab = ui.tab("GRAPHIQUES", icon="layers").classes("rounded-full px-4")
                media_tab = ui.tab("MEDIAS", icon="video_library").classes("rounded-full px-4")

            media_loaded = {"value": False}

            #la bibliotheque n'est lue qu'a la PREMIERE ouverture de l'onglet
            #(CLS peut etre long sur un gros serveur), puis via son bouton
            async def on_tab_change(event) -> None:
                if event.value == "MEDIAS" and not media_loaded["value"]:
                    media_loaded["value"] = True
                    await load_library()

            tabs.on_value_change(on_tab_change)

            with ui.tab_panels(tabs, value=graphics_tab, animated=False).classes("w-full bg-transparent"):
                with ui.tab_panel(graphics_tab).classes("p-0"):
                    build_graphics_panel()
                with ui.tab_panel(media_tab).classes("p-0"):
                    with ui.column().classes("w-full").style(panel_style):
                        load_library = media_browser.build_media_tab(caspar, MEDIA_DEFAULT_LAYER)
        else:
            build_graphics_panel()

    render()


#pied de page : actions GLOBALES sur les boutons de la grille,
#independantes de quel bouton a envoye quoi
def build_footer(caspar: CasparCG, data: DataSource | None, config: dict) -> None:
    async def on_all_out_click() -> None:
        await SceneButton.stop_all_pgm()
        ui.notify("ALL OUT : tous les graphiques au programme ont ete stoppes", type="warning")

    async def on_clear_prw_click() -> None:
        errors = await SceneButton.clear_all_previews()
        if errors:
            ui.notify(f"Erreur lors du clear preview : {'; '.join(errors)}", type="negative")
        else:
            ui.notify("Preview clear", type="info")

    footer_button_classes = "px-8 py-3 text-lg"

    with ui.footer().classes("flex-col gap-2 bg-slate-900 p-3 m-3 rounded-2xl overflow-hidden"):
        with ui.row().classes("items-center justify-center gap-4 w-full"):
            ui.button("ALL OUT", icon="stop_circle", color=None, on_click=on_all_out_click).classes(
                pill_classes("orange", footer_button_classes)
            )
            ui.button("CLEAR PRW", icon="layers_clear", color=None, on_click=on_clear_prw_click).classes(
                pill_classes("yellow", footer_button_classes)
            )
            ui.button(
                "TAKE PREVIEW", icon="arrow_upward", color=None, on_click=SceneButton.take_all_previews
            ).classes(pill_classes("green", footer_button_classes))
            ui.button("SWAP", icon="swap_vert", color=None, on_click=SceneButton.swap_preview_pgm).classes(
                pill_classes("blue", footer_button_classes)
            )

            for invoke in FOOTER_INVOKES:
                ui.button(
                    invoke["label"],
                    icon=invoke.get("icon", "bolt"),
                    color=None,
                    on_click=lambda _, f=invoke["function"]: SceneButton.invoke_all_pgm(f),
                ).classes(pill_classes(invoke.get("color", "purple"), footer_button_classes))
