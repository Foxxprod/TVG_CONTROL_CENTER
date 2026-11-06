# Onglet MEDIAS : bibliotheque des medias presents sur le serveur CasparCG
# (CLS - videos, images, sons) et lecture sur un layer au choix, en preview
# ou directement au programme, avec la MEME logique que les boutons de la
# grille : un seul occupant par (channel, layer), preview jaune, programme
# rouge, Take preview -> programme.
#
# Medias en cours (_active, niveau module) : survivent a un rechargement de
# page, comme SceneButton._active_pgm. Chaque onglet navigateur ouvert se
# resynchronise via _version (compteur incremente a chaque changement).
#
# Changer le layer d'un media EN COURS utilise SWAP (casparcg.move_layer) :
# la lecture continue sans coupure. Les reglages MIXER (opacite/volume) ne
# suivent pas un SWAP, ils sont donc reappliques sur le nouveau layer.
#
# Les layers utilises par les boutons de la grille (SceneButton) sont
# refuses ici pour ne jamais ecraser un graphique.

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime

from nicegui import ui

from casparcg import CasparCG, MediaItem
from scene_button import SceneButton

TRANSITIONS = ["CUT", "MIX", "PUSH", "SLIDE", "WIPE"]
TYPE_FILTERS = {"ALL": "Tous", "MOVIE": "Videos", "STILL": "Images", "AUDIO": "Sons"}


@dataclass
class ActiveMedia:
    channel: str  # "prw" | "pgm"
    layer: int
    clip: str
    loop: bool
    transition: str
    duration: int
    paused: bool = False
    opacity: float = 1.0
    volume: float = 1.0


_active: dict[tuple[str, int], ActiveMedia] = {}
_version = {"value": 0}


def _changed() -> None:
    _version["value"] += 1


#oublie tous les medias en cours sans commande AMCP (CasparCG deja vide,
#apres un emergency all out - voir interface.build_header)
def reset_media() -> None:
    _active.clear()
    _changed()


def _format_duration(item: MediaItem) -> str:
    seconds = item.duration_seconds
    if seconds is None:
        return "-"
    minutes, secs = divmod(int(round(seconds)), 60)
    return f"{minutes:02d}:{secs:02d}"


def _format_size(size: int) -> str:
    if size >= 1024**3:
        return f"{size / 1024**3:.1f} Go"
    if size >= 1024**2:
        return f"{size / 1024**2:.1f} Mo"
    return f"{size / 1024:.0f} Ko"


def _format_date(raw: str) -> str:
    try:
        return datetime.strptime(raw[:14], "%Y%m%d%H%M%S").strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return raw


#bouton de la grille qui utilise deja ce layer video (principal ou
#second CG), None sinon
def _gfx_conflict(layer: int) -> SceneButton | None:
    for button in SceneButton._instances:
        if layer == button.layer or (button.second_cg and layer == button._second_cg_video_layer()):
            return button
    return None


def _log(message: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [MEDIA] {message}")


#construit le contenu de l'onglet et renvoie load_library (a appeler a la
#premiere ouverture de l'onglet, voir interface.build_body)
def build_media_tab(caspar: CasparCG, default_layer: int) -> Callable[[], Awaitable[None]]:
    library: list[MediaItem] = []
    selected: dict[str, MediaItem | None] = {"item": None}
    seen_version = {"value": -1}

    def card_classes() -> str:
        if SceneButton._dark_mode:
            return "border border-slate-700 rounded-2xl bg-slate-800 p-3 gap-2 min-h-0"
        return "border border-slate-200 rounded-2xl bg-white p-3 gap-2 min-h-0"

    #(carte, classes de taille propres a cette carte)
    cards: list[tuple[ui.column, str]] = []

    def refresh_theme(_dark: bool) -> None:
        for card, extra in cards:
            card.classes(replace=f"{card_classes()} {extra}")
        refresh_active()

    SceneButton.on_dark_mode_change(refresh_theme)

    def make_card(extra: str) -> ui.column:
        card = ui.column().classes(f"{card_classes()} {extra}")
        cards.append((card, extra))
        return card

    def section_title(text: str) -> None:
        ui.label(text).classes("text-sm font-bold tracking-wide text-slate-500")

    # ------------------------------------------------------------------
    # actions
    # ------------------------------------------------------------------

    async def load_library() -> None:
        if not caspar.connected:
            ui.notify("CasparCG deconnecte : impossible de lister les medias", type="warning")
            return

        items, error = await caspar.list_media()
        if error:
            ui.notify(f"Erreur CLS : {error}", type="negative")
            return

        library[:] = items
        apply_filters()
        ui.notify(f"{len(items)} media(s) trouve(s)", type="info")

    def apply_filters() -> None:
        search = (search_input.value or "").lower()
        media_type = type_select.value
        rows = [
            {
                "name": item.name,
                "type": item.type,
                "duration": _format_duration(item),
                "size": _format_size(item.size),
                "modified": _format_date(item.modified),
            }
            for item in library
            if (media_type == "ALL" or item.type == media_type) and search in item.name.lower()
        ]
        table.rows = rows
        table.update()
        count_label.text = f"{len(rows)} / {len(library)}"

    def on_select(event) -> None:
        names = [row["name"] for row in event.selection]
        selected["item"] = next((item for item in library if names and item.name == names[0]), None)
        refresh_player()

    def check_layer(layer: int) -> bool:
        conflict = _gfx_conflict(layer)
        if conflict is not None:
            ui.notify(f"Layer {layer} deja utilise par le bouton '{conflict.label}'", type="warning")
            return False
        return True

    async def play(channel: str, item: MediaItem | None = None) -> None:
        item = item or selected["item"]
        if item is None:
            ui.notify("Selectionnez d'abord un media", type="warning")
            return

        layer = int(layer_input.value or default_layer)
        if not check_layer(layer):
            return

        transition = transition_select.value
        duration = int(duration_input.value or 0)

        response = await caspar.play_media(
            channel, layer, item.name, loop=loop_switch.value, transition=transition, duration=duration
        )
        if response.is_error:
            _log(f"PLAY {channel.upper()} '{item.name}' : ERREUR - {response.message}")
            ui.notify(f"Erreur lors du play : {response.message}", type="negative")
            return

        _log(f"PLAY {channel.upper()} '{item.name}' (layer={layer}, loop={loop_switch.value}) OK")
        _active[(channel, layer)] = ActiveMedia(
            channel, layer, item.name, loop_switch.value, transition, duration
        )
        _changed()
        refresh_active()

    async def take(media: ActiveMedia) -> None:
        response = await caspar.play_media(
            "pgm", media.layer, media.clip, loop=media.loop,
            transition=media.transition, duration=media.duration,
        )
        if response.is_error:
            ui.notify(f"Erreur lors du take : {response.message}", type="negative")
            return

        await caspar.clear("prw", layer=media.layer)
        _active.pop(("prw", media.layer), None)
        media.channel = "pgm"
        media.paused = False
        _active[("pgm", media.layer)] = media
        #opacite/volume regles en preview reappliques au programme
        for prop, value in (("OPACITY", media.opacity), ("VOLUME", media.volume)):
            if value != 1.0:
                await caspar.set_mixer("pgm", media.layer, prop, value)
        _log(f"TAKE '{media.clip}' (layer={media.layer}) OK")
        _changed()
        refresh_active()

    async def out(media: ActiveMedia) -> None:
        response = await caspar.clear(media.channel, layer=media.layer)
        await caspar.clear_mixer(media.channel, media.layer)
        if response.is_error:
            ui.notify(f"Erreur lors du clear : {response.message}", type="negative")
        _log(f"OUT {media.channel.upper()} '{media.clip}' (layer={media.layer})")
        _active.pop((media.channel, media.layer), None)
        _changed()
        refresh_active()

    async def out_all() -> None:
        for media in list(_active.values()):
            await out(media)

    async def move(media: ActiveMedia, new_layer_value) -> None:
        try:
            new_layer = int(new_layer_value)
        except (TypeError, ValueError):
            return
        if new_layer == media.layer or not check_layer(new_layer):
            refresh_active()
            return
        if (media.channel, new_layer) in _active:
            ui.notify(f"Layer {new_layer} deja occupe par un autre media", type="warning")
            refresh_active()
            return

        response = await caspar.move_layer(media.channel, media.layer, new_layer)
        if response.is_error:
            ui.notify(f"Erreur lors du changement de layer : {response.message}", type="negative")
            refresh_active()
            return

        await caspar.clear_mixer(media.channel, media.layer)
        for prop, value in (("OPACITY", media.opacity), ("VOLUME", media.volume)):
            if value != 1.0:
                await caspar.set_mixer(media.channel, new_layer, prop, value)

        _log(f"MOVE '{media.clip}' {media.channel.upper()} layer {media.layer} -> {new_layer}")
        _active.pop((media.channel, media.layer), None)
        media.layer = new_layer
        _active[(media.channel, new_layer)] = media
        _changed()
        refresh_active()

    async def toggle_loop(media: ActiveMedia, value: bool) -> None:
        response = await caspar.set_media_loop(media.channel, media.layer, value)
        if response.is_error:
            ui.notify(f"Erreur LOOP : {response.message}", type="negative")
            return
        media.loop = value
        _changed()

    async def toggle_pause(media: ActiveMedia) -> None:
        if media.paused:
            response = await caspar.resume_media(media.channel, media.layer)
        else:
            response = await caspar.pause_media(media.channel, media.layer)
        if response.is_error:
            ui.notify(f"Erreur PAUSE/RESUME : {response.message}", type="negative")
            return
        media.paused = not media.paused
        _changed()
        refresh_active()

    async def set_mixer(media: ActiveMedia, prop: str, value) -> None:
        try:
            value = float(value)
        except (TypeError, ValueError):
            return
        response = await caspar.set_mixer(media.channel, media.layer, prop, value)
        if response.is_error:
            ui.notify(f"Erreur MIXER {prop} : {response.message}", type="negative")
            return
        setattr(media, prop.lower(), value)
        _changed()

    # ------------------------------------------------------------------
    # rendu
    # ------------------------------------------------------------------

    def refresh_player() -> None:
        item = selected["item"]
        if item is None:
            selected_label.text = "Aucun media selectionne"
            selected_detail.text = "Choisissez un media dans la bibliotheque (double-clic = preview)"
        else:
            selected_label.text = item.name
            selected_detail.text = f"{item.type} - {_format_duration(item)} - {_format_size(item.size)}"

    @ui.refreshable
    def active_list() -> None:
        seen_version["value"] = _version["value"]

        if not _active:
            ui.label("Aucun media en cours").classes("text-xs text-slate-400")
            return

        box_classes = (
            "w-full border border-slate-700 rounded-xl bg-slate-900/40 p-2 gap-1"
            if SceneButton._dark_mode
            else "w-full border border-slate-300 rounded-xl bg-slate-50 p-2 gap-1"
        )

        for media in sorted(_active.values(), key=lambda m: (m.channel != "pgm", m.layer)):
            on_air = media.channel == "pgm"
            with ui.column().classes(box_classes):
                with ui.row(wrap=False).classes("w-full items-center gap-2"):
                    ui.label("PGM" if on_air else "PRW").classes(
                        "text-xs font-bold text-white rounded-full px-2 py-0.5 "
                        + ("bg-red-600" if on_air else "bg-yellow-600")
                    )
                    ui.label(media.clip).classes("text-sm font-bold truncate min-w-0 flex-1")
                    if media.paused:
                        ui.label("PAUSE").classes("text-xs font-bold text-orange-500")

                with ui.row(wrap=False).classes("w-full items-center gap-2"):
                    layer_field = ui.number("Layer", value=media.layer, min=1, step=1, format="%d").props(
                        "dense"
                    ).classes("w-20")
                    layer_field.on("keydown.enter", lambda _, m=media, f=layer_field: move(m, f.value))
                    layer_field.on("blur", lambda _, m=media, f=layer_field: move(m, f.value))

                    ui.switch(
                        "Boucle", value=media.loop,
                        on_change=lambda e, m=media: toggle_loop(m, e.value),
                    ).props("dense")

                    ui.space()

                    ui.button(
                        icon="play_arrow" if media.paused else "pause",
                        color=None,
                        on_click=lambda _, m=media: toggle_pause(m),
                    ).props("round dense flat").classes("text-slate-500").tooltip(
                        "Reprendre" if media.paused else "Pause"
                    )

                    if not on_air:
                        ui.button(
                            "TAKE", color=None, on_click=lambda _, m=media: take(m)
                        ).classes(
                            "border border-green-500 bg-green-600/20 hover:bg-green-600/30 "
                            "text-green-500 font-bold rounded-full px-3"
                        ).props("dense")

                    ui.button(
                        "OUT", color=None, on_click=lambda _, m=media: out(m)
                    ).classes(
                        "border border-red-500 bg-red-600/20 hover:bg-red-600/30 "
                        "text-red-500 font-bold rounded-full px-3"
                    ).props("dense")

                for prop, icon in (("OPACITY", "opacity"), ("VOLUME", "volume_up")):
                    with ui.row(wrap=False).classes("w-full items-center gap-2"):
                        ui.icon(icon).classes("text-slate-400 text-base")
                        slider = ui.slider(
                            min=0, max=1, step=0.05, value=getattr(media, prop.lower())
                        ).props("dense label").classes("flex-1")
                        #"change" = relachement du curseur (pas a chaque pixel)
                        slider.on(
                            "change", lambda e, m=media, p=prop: set_mixer(m, p, e.args)
                        )

    def refresh_active() -> None:
        active_list.refresh()

    #resynchronise cet onglet navigateur si un autre a modifie les medias
    def poll_active() -> None:
        if seen_version["value"] != _version["value"]:
            refresh_active()

    # ------------------------------------------------------------------
    # mise en page
    # ------------------------------------------------------------------

    with ui.row(wrap=False).classes("w-full h-full items-stretch gap-3"):
        with make_card("flex-1 h-full"):
            with ui.row(wrap=False).classes("w-full items-center gap-2"):
                section_title("BIBLIOTHEQUE")
                count_label = ui.label("").classes("text-xs text-slate-400")
                ui.space()
                search_input = ui.input(placeholder="Rechercher...").props(
                    "dense clearable"
                ).classes("w-64")
                type_select = ui.select(TYPE_FILTERS, value="ALL").props("dense").classes("w-32")
                ui.button(
                    icon="refresh", color=None, on_click=load_library
                ).classes(
                    "border border-slate-400 bg-slate-500/10 hover:bg-slate-500/20 "
                    "text-slate-500 rounded-full"
                ).props("round dense").tooltip("Relire la liste des medias (CLS)")

            search_input.on_value_change(lambda _: apply_filters())
            type_select.on_value_change(lambda _: apply_filters())

            table = ui.table(
                columns=[
                    {"name": "name", "label": "Nom", "field": "name", "align": "left", "sortable": True},
                    {"name": "type", "label": "Type", "field": "type", "align": "left", "sortable": True},
                    {"name": "duration", "label": "Duree", "field": "duration", "align": "right"},
                    {"name": "size", "label": "Taille", "field": "size", "align": "right"},
                    {"name": "modified", "label": "Modifie", "field": "modified", "align": "right"},
                ],
                rows=[],
                row_key="name",
                selection="single",
                pagination=0,
                on_select=on_select,
            ).props("dense flat virtual-scroll hide-bottom").classes("w-full flex-1 min-h-0")

            #double-clic sur une ligne = envoi direct en preview
            async def on_row_dblclick(event) -> None:
                name = event.args[1]["name"] if len(event.args) > 1 else None
                item = next((i for i in library if i.name == name), None)
                if item is not None:
                    selected["item"] = item
                    table.selected = [event.args[1]]
                    refresh_player()
                    await play("prw", item)

            table.on("rowDblclick", on_row_dblclick)

        with ui.column().classes("w-[28rem] h-full gap-3 min-h-0").style("flex-shrink: 0;"):
            with make_card("w-full"):
                section_title("LECTURE")
                selected_label = ui.label().classes("text-base font-bold truncate w-full")
                selected_detail = ui.label().classes("text-xs text-slate-400")

                with ui.row(wrap=False).classes("w-full items-center gap-2"):
                    layer_input = ui.number(
                        "Layer", value=default_layer, min=1, step=1, format="%d"
                    ).props("dense").classes("w-24")
                    loop_switch = ui.switch("Boucle", value=False).props("dense")
                with ui.row(wrap=False).classes("w-full items-center gap-2"):
                    transition_select = ui.select(TRANSITIONS, value="CUT", label="Transition").props(
                        "dense"
                    ).classes("flex-1")
                    duration_input = ui.number(
                        "Duree (frames)", value=0, min=0, step=1, format="%d"
                    ).props("dense").classes("w-32")

                with ui.row(wrap=False).classes("w-full items-center gap-2 mt-1"):
                    ui.button(
                        "PREVIEW", icon="visibility", color=None, on_click=lambda: play("prw")
                    ).classes(
                        "flex-1 border border-yellow-500 bg-yellow-600/20 hover:bg-yellow-600/30 "
                        "text-yellow-600 font-bold rounded-full"
                    )
                    ui.button(
                        "DIRECT PGM", icon="play_arrow", color=None, on_click=lambda: play("pgm")
                    ).classes(
                        "flex-1 border border-red-500 bg-red-600/20 hover:bg-red-600/30 "
                        "text-red-500 font-bold rounded-full"
                    )

            with make_card("w-full flex-1"):
                with ui.row(wrap=False).classes("w-full items-center"):
                    section_title("EN COURS")
                    ui.space()
                    ui.button("TOUT COUPER", icon="layers_clear", color=None, on_click=out_all).classes(
                        "border border-orange-500 bg-orange-600/20 hover:bg-orange-600/30 "
                        "text-orange-500 font-bold rounded-full px-3"
                    ).props("dense")
                with ui.scroll_area().classes("w-full flex-1"):
                    active_list()

    refresh_player()
    ui.timer(1.0, poll_active)

    return load_library
