# Exemple d'utilisation :
#
#   SceneButton(
#       caspar, data,
#       label="LOWER THIRD",
#       template="lower_third",
#       layer=20,
#       multipage_on=True,
#       free_texts=[{"field": "name", "label": "Nom"}],
#   )

from datetime import datetime
from typing import Callable

from nicegui import ui

from casparcg import CasparCG
from data_source import DataSource


class SceneButton:
    """Bouton representant un graphique CasparCG configurable.

    Comportement au clic (corps du bouton) :
        - idle      -> joue le template en preview
        - preview   -> Take vers le programme (play_prw_to_pgm)
        - programme -> ne fait rien (utiliser la pastille "OUT" pour stop)

    Au survol, une pastille apparait au-dessus du bouton :
        - "IN"  (idle)      -> envoie DIRECTEMENT au programme
        - "IN"  (preview)   -> Take vers le programme
        - "OUT" (programme) -> stop le graphique ; reste visible en
          permanence tant que le graphique est a l'antenne.

    Un (layer, cg_layer) CasparCG n'a qu'un seul occupant, en preview comme
    au programme (chaque bouton previse sur SON PROPRE layer, le meme qu'au
    programme). Plusieurs boutons sur des layers differents peuvent donc
    etre en preview EN MEME TEMPS (TAKE PREVIEW/SWAP du footer agissent sur
    tous). Mettre un bouton en preview/au programme ne libere que SON
    PROPRE slot.

    Options (toutes declarees dans templates.json) :
        extra_data      : dict de valeurs fixes toujours envoyees.
        multipage_on    : fleches < > autour du label, numero de page envoye
                          dans field_page, pousse en direct si deja affiche.
                          reset_page_on_play remet la page a 1 a chaque play.
        free_texts      : zones de saisie sous le bouton, ex :
                            [{"field": "name", "label": "Nom"},
                             {"field": "sponsor", "label": "Sponsor",
                              "options": ["A", "B"]}]
                          Sans "options" : texte libre. Avec "options" :
                          liste a choix + texte libre (mutuellement
                          exclusifs) et icones +/- pour ajouter/supprimer
                          une option en direct (persistee dans
                          templates.json). Grises tant que le bouton n'est
                          pas idle.
                          "type": "number" (+ min/max/step/default
                          optionnels) : compteur - [valeur] +, modifiable
                          a l'antenne, pousse en direct (ex: points).
        second_cg       : deuxieme template joue/stoppe/mis a jour EN MEME
                          TEMPS que le principal (meme payload), sur
                          second_cg_layer (layer video) ou le meme layer
                          video, toujours au cg_layer + 1. Un echec du
                          second CG ne fait jamais echouer le principal.
        send_ip         : envoie l'IP de la source de donnees (field_ip) -
                          seulement si une source est implementee.
    """

    #registre de toutes les instances vivantes (reset_all, ALL OUT...)
    _instances: list["SceneButton"] = []

    #bouton qui occupe actuellement chaque (layer, cg_layer) en preview /
    #au programme
    _active_preview: dict[tuple[int, int], "SceneButton"] = {}
    _active_pgm: dict[tuple[int, int], "SceneButton"] = {}

    #theme courant, partage par tous les boutons (voir set_dark_mode). Les
    #autres modules (cartes de section, onglet medias) s'abonnent via
    #on_dark_mode_change plutot que de dupliquer un etat sombre/clair.
    _dark_mode: bool = False
    _dark_mode_listeners: list[Callable[[bool], None]] = []

    @classmethod
    def set_dark_mode(cls, dark: bool) -> None:
        cls._dark_mode = dark
        for button in cls._instances:
            button._refresh_box_style()
            button._refresh_appearance()
        for callback in cls._dark_mode_listeners:
            callback(dark)

    @classmethod
    def on_dark_mode_change(cls, callback: Callable[[bool], None]) -> None:
        cls._dark_mode_listeners.append(callback)

    def __init__(
        self,
        caspar: CasparCG,
        data: DataSource | None,
        label: str,
        template: str,
        layer: int,
        cg_layer: int = 1,
        extra_data: dict[str, str] | None = None,
        send_ip: bool = False,
        field_ip: str = "ip",
        multipage_on: bool = False,
        field_page: str = "page",
        reset_page_on_play: bool = False,
        free_texts: list[dict[str, object]] | None = None,
        second_cg: str | None = None,
        second_cg_layer: int | None = None,
        on_config_changed: Callable[[], None] | None = None,
        edit_actions: tuple[Callable[[], object], Callable[[], object]] | None = None,
    ):
        self.caspar = caspar
        self.data = data

        self.label = label
        self.template = template
        self.layer = layer
        self.cg_layer = cg_layer
        self.extra_data = extra_data or {}

        self.second_cg = second_cg
        self.second_cg_layer = second_cg_layer

        self.send_ip = send_ip
        self.field_ip = field_ip

        self.multipage_on = multipage_on
        self.field_page = field_page
        self.reset_page_on_play = reset_page_on_play

        self.free_texts = free_texts or []

        #appele quand une option de free_text est ajoutee/supprimee en
        #direct, pour que interface.py persiste templates.json - ce module
        #ne sait pas ou/comment ecrire ce fichier
        self._on_config_changed = on_config_changed

        #MODE EDITION (voir interface.build_body) : (modifier, supprimer).
        #Non None -> le clic ouvre l'editeur au lieu de jouer, la pastille
        #IN/OUT est remplacee par les icones crayon/poubelle
        self._edit_actions = edit_actions
        #definition templates.json d'origine (renseignee par interface.py)
        self.entry: dict | None = None

        self._state = "idle"  # "idle" | "preview" | "programme"
        self._page = 1
        #dernier payload envoye au second CG en preview, rejoue tel quel au
        #Take (play_prw_to_pgm ne reprend qu'UN producer, celui du principal)
        self._second_cg_payload: dict[str, str] | None = None
        self._free_text_widgets: dict[str, tuple[ui.select | None, ui.input]] = {}
        #free_texts "type": "number" (compteur -/+), a part : un 0 est une
        #valeur valide (le "or" des champs texte l'effacerait) et ils
        #restent modifiables a l'antenne
        self._number_widgets: dict[str, ui.number] = {}
        self._box: ui.column | None = None
        self._button_container: ui.column | None = None
        self._warning_icon: ui.icon | None = None

        self._build()
        SceneButton._instances.append(self)

    #log console horodate (le .exe est compile avec console=True)
    def _log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{self.label}] {message}")

    #remet ce bouton a idle sans commande AMCP (CasparCG deja vide, ex:
    #apres un emergency all out)
    def reset_to_idle(self) -> None:
        was_active = self._state != "idle"

        self._state = "idle"
        self._second_cg_payload = None
        key = (self.layer, self.cg_layer)
        if SceneButton._active_preview.get(key) is self:
            del SceneButton._active_preview[key]
        if SceneButton._active_pgm.get(key) is self:
            del SceneButton._active_pgm[key]
        self._refresh_appearance()

        if was_active:
            self._log("RESET (remis a idle)")

    #identite STABLE d'un bouton (ce qui est reellement envoye a CasparCG),
    #pour retrouver "le meme bouton" apres une reconstruction de la grille
    @property
    def identity(self) -> tuple[str, int, int]:
        return (self.template, self.layer, self.cg_layer)

    #reprend l'etat EN DIRECT d'une ancienne instance du meme bouton (grille
    #reconstruite par le mode edition) : un graphique a l'antenne/en preview
    #reste suivi, la page et les textes saisis ne sont pas perdus
    def adopt(self, old: "SceneButton") -> None:
        self._state = old._state
        self._page = old._page
        self._second_cg_payload = old._second_cg_payload

        for field, old_number in old._number_widgets.items():
            if field in self._number_widgets:
                self._number_widgets[field].value = old_number.value

        for field, (old_select, old_input) in old._free_text_widgets.items():
            if field not in self._free_text_widgets:
                continue
            select_widget, input_widget = self._free_text_widgets[field]
            if select_widget is not None and old_select is not None and old_select.value in select_widget.options:
                select_widget.value = old_select.value
            input_widget.value = old_input.value

        key = (self.layer, self.cg_layer)
        if SceneButton._active_preview.get(key) is old:
            SceneButton._active_preview[key] = self
        if SceneButton._active_pgm.get(key) is old:
            SceneButton._active_pgm[key] = self
        self._refresh_appearance()

    #retire une instance dont les elements ont ete detruits (grille
    #reconstruite) de tous les registres
    @classmethod
    def forget(cls, button: "SceneButton") -> None:
        if button in cls._instances:
            cls._instances.remove(button)
        for registry in (cls._active_preview, cls._active_pgm):
            for key in [k for k, v in registry.items() if v is button]:
                del registry[key]

    @classmethod
    def reset_all(cls) -> None:
        print("=== EMERGENCY ALL OUT : remise a idle de tous les boutons ===")
        for button in cls._instances:
            button.reset_to_idle()

    #stoppe (CG STOP + auto-remove differe) tous les boutons au programme,
    #sans toucher a la preview - bouton ALL OUT du footer
    @classmethod
    async def stop_all_pgm(cls) -> None:
        print("=== ALL OUT : arret de tous les graphiques au programme ===")
        for button in list(cls._instances):
            if button._state == "programme":
                await button._stop()

    #CG INVOKE d'une fonction du template sur TOUS les boutons au
    #programme (second_cg compris) - boutons project.FOOTER_INVOKES
    @classmethod
    async def invoke_all_pgm(cls, function: str) -> None:
        buttons = [button for button in cls._instances if button._state == "programme"]
        if not buttons:
            ui.notify("Aucun graphique a l'antenne", type="warning")
            return

        print(f"=== INVOKE '{function}' sur {len(buttons)} graphique(s) au programme ===")
        for button in buttons:
            targets = [(button.layer, button.cg_layer)]
            if button.second_cg:
                targets.append((button._second_cg_video_layer(), button._second_cg_stack_layer()))

            for layer, cg_layer in targets:
                response = await button.caspar.invoke_template(
                    "pgm", function, layer=layer, cg_layer=cg_layer
                )
                if response.is_error:
                    button._log(f"INVOKE '{function}' (layer={layer}) : ERREUR - {response.message}")
                    ui.notify(f"Erreur INVOKE sur '{button.label}' : {response.message}", type="negative")
                else:
                    button._log(f"INVOKE '{function}' OK (layer={layer}, cg_layer={cg_layer})")

    #clear immediat de TOUS les slots de preview suivis localement + remise
    #a idle des boutons concernes - bouton CLEAR PRW. Renvoie les erreurs.
    @classmethod
    async def clear_all_previews(cls) -> list[str]:
        print("=== CLEAR PRW : vidage de tous les slots de preview actifs ===")
        errors: list[str] = []

        for button in list(cls._active_preview.values()):
            response = await button.caspar.clear("prw", layer=button.layer)
            if response.is_error:
                errors.append(response.message)

            if button.second_cg:
                second_layer = button._second_cg_video_layer()
                if second_layer != button.layer:
                    second_response = await button.caspar.clear("prw", layer=second_layer)
                    if second_response.is_error:
                        errors.append(second_response.message)

            button.reset_to_idle()

        return errors

    #Take de CHAQUE bouton en preview - bouton TAKE PREVIEW
    @classmethod
    async def take_all_previews(cls) -> None:
        buttons = list(cls._active_preview.values())
        if not buttons:
            ui.notify("Aucun graphique en preview", type="warning")
            return

        print(f"=== TAKE PREVIEW : envoi de {len(buttons)} graphique(s) au programme ===")
        for button in buttons:
            await button._take()

    #comme take_all_previews, mais renvoie EN PLUS en preview le graphique
    #qui etait au programme (vrai echange) - bouton SWAP. Appariement en 2
    #passes : d'abord par (layer, cg_layer) identique, puis dans l'ordre
    #(un swap se fait normalement entre deux boutons DIFFERENTS, donc sur
    #des layers differents).
    @classmethod
    async def swap_preview_pgm(cls) -> None:
        preview_buttons = list(cls._active_preview.values())
        if not preview_buttons:
            ui.notify("Aucun graphique en preview", type="warning")
            return

        print(f"=== SWAP : echange de {len(preview_buttons)} graphique(s) preview/programme ===")
        remaining_pgm = list(cls._active_pgm.values())
        pairing: dict["SceneButton", "SceneButton | None"] = {}

        for preview_button in preview_buttons:
            exact = cls._active_pgm.get((preview_button.layer, preview_button.cg_layer))
            if exact is not None and exact in remaining_pgm:
                remaining_pgm.remove(exact)
                pairing[preview_button] = exact
            else:
                pairing[preview_button] = None

        for preview_button in preview_buttons:
            if pairing[preview_button] is None and remaining_pgm:
                pairing[preview_button] = remaining_pgm.pop(0)

        for preview_button in preview_buttons:
            pgm_button = pairing[preview_button]

            #payload capture AVANT le stop, pour le rejouer a l'identique
            pgm_payload = None
            if pgm_button is not None and pgm_button is not preview_button:
                pgm_payload = pgm_button._build_payload()
                await pgm_button._stop()

            await preview_button._take()

            if pgm_button is not None and pgm_payload is not None:
                response = await pgm_button.caspar.play_template(
                    "prw",
                    pgm_button.template,
                    data=pgm_payload,
                    layer=pgm_button.layer,
                    cg_layer=pgm_button.cg_layer,
                )
                if response.is_error:
                    pgm_button._log(f"SWAP : erreur renvoi en preview - {response.message}")
                    ui.notify(f"Erreur lors du swap (renvoi en preview) : {response.message}", type="negative")
                    continue

                pgm_button._state = "preview"
                cls._active_preview[(pgm_button.layer, pgm_button.cg_layer)] = pgm_button
                pgm_button._refresh_appearance()
                pgm_button._log(f"SWAP : renvoye en PREVIEW (layer={pgm_button.layer}) OK")

                #renvoyer aussi son second_cg, sinon un futur Take ne le
                #rejouerait plus jamais au programme
                await pgm_button._play_second_cg("prw", pgm_payload)

    #construit l'element visuel : bouton (+ fleches multipage + pastille
    #IN/OUT) et eventuels champs free_texts, regroupes dans une "box" bordee
    #s'il y a quelque chose sous le bouton. La box se dimensionne sur le
    #bouton (w-64), les champs (w-full) se calent dessus.
    def _build(self) -> None:
        with ui.row().classes("items-start gap-2"):
            if self.free_texts:
                self._box = ui.column()
                with self._box:
                    self._build_button()
                    self._build_free_text_inputs()
                self._refresh_box_style()
            else:
                self._build_button()

        ui.timer(1.0, self._refresh_connection_warning)

    def _muted_text_color(self) -> str:
        return "text-slate-300" if SceneButton._dark_mode else "text-slate-600"

    def _refresh_box_style(self) -> None:
        if self._box is None:
            return

        if SceneButton._dark_mode:
            self._box.classes(replace="border border-slate-700 rounded-xl bg-slate-800 p-2 gap-2")
        else:
            self._box.classes(replace="border border-slate-300 rounded-xl bg-slate-50 p-2 gap-2")

    def _build_button(self) -> None:
        self._button_container = ui.column().classes("relative group inline-flex gap-0 w-64")
        with self._button_container:
            self._hover_label = ui.label("IN")
            self._hover_label.on("click", self._on_hover_click)

            edit_outline = (
                " outline outline-2 outline-dashed outline-sky-500 outline-offset-2"
                if self._edit_actions is not None
                else ""
            )
            with ui.row().classes(
                "w-full items-stretch border rounded-full overflow-hidden gap-0 border-slate-600"
                + edit_outline
            ):
                if self.multipage_on:
                    prev_area = ui.row().classes(
                        "items-center justify-center px-2 bg-slate-800 "
                        "hover:bg-slate-700 cursor-pointer border-r border-slate-600"
                    )
                    with prev_area:
                        ui.icon("chevron_left").classes("text-white text-base")
                    prev_area.on("click", self._on_prev_page)

                self._main_area = ui.row().classes(
                    "flex-1 items-center justify-center px-2 py-2 cursor-pointer"
                )
                with self._main_area:
                    self._label_widget = ui.label(self._label_text()).classes(
                        "text-sm font-bold text-white text-center whitespace-nowrap"
                    )
                self._main_area.on("click", self._on_main_click)

                if self.multipage_on:
                    next_area = ui.row().classes(
                        "items-center justify-center px-2 bg-slate-800 "
                        "hover:bg-slate-700 cursor-pointer border-l border-slate-600"
                    )
                    with next_area:
                        ui.icon("chevron_right").classes("text-white text-base")
                    next_area.on("click", self._on_next_page)

                #mode edition : crayon/poubelle DANS la pastille (comme les
                #fleches multipage) - au-dessus, ils chevauchaient les
                #titres de colonne
                if self._edit_actions is not None:
                    edit, delete = self._edit_actions
                    with ui.row(wrap=False).classes(
                        "items-center gap-0 px-1 bg-slate-800 border-l border-slate-600"
                    ):
                        ui.icon("edit").classes(
                            "text-sky-400 hover:text-sky-300 cursor-pointer text-base px-1"
                        ).on("click", edit).tooltip("Modifier")
                        ui.icon("delete").classes(
                            "text-red-400 hover:text-red-300 cursor-pointer text-base px-1"
                        ).on("click", delete).tooltip("Supprimer")

            #icone d'alerte de connexion positionnee par rapport au BOUTON
            #seul (pas a la box entiere, agrandie par les champs en dessous)
            with ui.row().classes(
                "absolute left-full top-1/2 -translate-y-1/2 ml-2 items-center gap-2"
            ):
                self._build_connection_warning()

        self._refresh_appearance()

    def _label_text(self) -> str:
        if self.multipage_on:
            return f"{self.label} ({self._page})"
        return self.label

    #champs de saisie sous le bouton. Sans "options" : un ui.input. Avec
    #"options" : un ui.select + un ui.input texte libre mutuellement
    #exclusifs (un select seul n'accepte pas de texte hors liste), avec
    #icones +/- pour gerer la liste en direct. "type": "number" : compteur
    #- [valeur] + (voir _build_number_input).
    def _build_free_text_inputs(self) -> None:
        with ui.column().classes("w-full gap-1"):
            for free_text in self.free_texts:
                field = free_text["field"]
                label = free_text.get("label", field)
                options = free_text.get("options")

                if free_text.get("type") == "number":
                    self._build_number_input(free_text)
                elif options is not None:
                    with ui.row().classes("w-full items-center gap-1"):
                        select_widget = ui.select(
                            options=list(options), value=None, label=label
                        ).classes("flex-1")

                        add_icon = ui.icon("add_circle").classes(
                            "text-slate-500 hover:text-green-600 cursor-pointer text-lg"
                        )
                        remove_icon = ui.icon("remove_circle").classes(
                            "text-slate-500 hover:text-red-600 cursor-pointer text-lg"
                        )

                    input_widget = ui.input(label="Texte libre").classes("w-full")

                    #arguments par defaut (pas de reference directe aux
                    #variables de boucle) : sinon tous les free_texts
                    #pointeraient sur la DERNIERE iteration (fermeture Python)
                    add_icon.on(
                        "click",
                        lambda _, ft=free_text, sel=select_widget, inp=input_widget: (
                            self._on_add_free_text_option(ft, sel, inp)
                        ),
                    )
                    remove_icon.on(
                        "click",
                        lambda _, ft=free_text, sel=select_widget: (
                            self._on_remove_free_text_option(ft, sel)
                        ),
                    )

                    select_widget.on_value_change(
                        lambda e, inp=input_widget: inp.set_value(None) if e.value else None
                    )
                    input_widget.on_value_change(
                        lambda e, sel=select_widget: sel.set_value(None) if e.value else None
                    )

                    self._free_text_widgets[field] = (select_widget, input_widget)
                else:
                    input_widget = ui.input(label=label).classes("w-full")
                    self._free_text_widgets[field] = (None, input_widget)

    #compteur numerique : boutons -/+ de part et d'autre d'un ui.number
    #(saisie directe possible). RESTE MODIFIABLE A L'ANTENNE (contrairement
    #aux champs texte) : chaque changement est pousse aussitot (CG UPDATE)
    #si le graphique est en preview/au programme - ex: compter des points
    def _build_number_input(self, free_text: dict) -> None:
        field = free_text["field"]
        step = free_text.get("step", 1)
        minimum = free_text.get("min")
        maximum = free_text.get("max")

        async def on_change(_event) -> None:
            if self._state != "idle":
                await self._update_data()

        def bump(direction: int) -> None:
            value = (number_widget.value or 0) + direction * step
            if minimum is not None:
                value = max(minimum, value)
            if maximum is not None:
                value = min(maximum, value)
            number_widget.value = value

        spin_classes = (
            "border border-slate-500 bg-slate-500/10 hover:bg-slate-500/20 text-slate-500 rounded-full"
        )
        with ui.row(wrap=False).classes("w-full items-center gap-1"):
            ui.button(icon="remove", color=None, on_click=lambda: bump(-1)).props(
                "round dense"
            ).classes(spin_classes)
            number_widget = ui.number(
                label=free_text.get("label", field),
                value=free_text.get("default", 0),
                min=minimum,
                max=maximum,
                step=step,
                on_change=on_change,
            ).props("dense input-class=text-center").classes("flex-1")
            ui.button(icon="add", color=None, on_click=lambda: bump(1)).props(
                "round dense"
            ).classes(spin_classes)

        self._number_widgets[field] = number_widget

    #ajoute une option EN DIRECT : au ui.select (selectionnee aussitot) ET
    #a free_text["options"] - le meme dict que celui charge depuis
    #templates.json, donc persiste via self._on_config_changed
    async def _on_add_free_text_option(
        self, free_text: dict, select_widget: ui.select, input_widget: ui.input
    ) -> None:
        with ui.dialog() as dialog, ui.card():
            ui.label("Nouvelle option").classes("text-base font-bold")
            new_option_input = (
                ui.input(label=free_text.get("label", free_text["field"]))
                .classes("w-64")
                .props("autofocus")
            )
            new_option_input.on("keydown.enter", lambda: dialog.submit(new_option_input.value))
            new_option_input.on("keydown.escape", lambda: dialog.submit(None))

            with ui.row():
                ui.button("Annuler", on_click=lambda: dialog.submit(None))
                ui.button("Ajouter", on_click=lambda: dialog.submit(new_option_input.value))

        ui.timer(0.1, lambda: new_option_input.run_method("focus"), once=True)

        value = await dialog

        if not value:
            return

        options = free_text.setdefault("options", [])
        if value not in options:
            options.append(value)

        select_widget.options = list(options)
        select_widget.value = value
        select_widget.update()
        input_widget.set_value(None)

        if self._on_config_changed is not None:
            self._on_config_changed()

        ui.notify(f"Option '{value}' ajoutee", type="positive")

    #supprime DEFINITIVEMENT l'option selectionnee, apres confirmation
    async def _on_remove_free_text_option(self, free_text: dict, select_widget: ui.select) -> None:
        value = select_widget.value
        if not value:
            ui.notify("Selectionnez d'abord une option a supprimer", type="warning")
            return

        with ui.dialog() as dialog, ui.card():
            ui.label("Supprimer cette option ?").classes("text-base font-bold")
            ui.label(f"'{value}' sera definitivement retiree de la liste.").classes(
                "text-sm text-slate-500"
            )
            with ui.row():
                ui.button("Annuler", on_click=lambda: dialog.submit(False))
                ui.button("Supprimer", color="red", on_click=lambda: dialog.submit(True))

        if not await dialog:
            return

        options = free_text.setdefault("options", [])
        if value in options:
            options.remove(value)

        select_widget.options = list(options)
        select_widget.value = None
        select_widget.update()

        if self._on_config_changed is not None:
            self._on_config_changed()

        ui.notify(f"Option '{value}' supprimee", type="positive")

    def _build_connection_warning(self) -> None:
        self._warning_icon = ui.icon("warning").classes("text-red-500 text-xl cursor-help")
        with self._warning_icon:
            self._warning_tooltip = ui.tooltip("").classes("bg-red-600 text-white font-bold")

        self._warning_icon.visible = False

    def _refresh_connection_warning(self) -> None:
        problems = []
        if not self.caspar.connected:
            problems.append("CasparCG deconnecte")
        if self.send_ip and self.data is not None and not self.data.connected:
            problems.append("Source de donnees deconnectee")

        self._warning_icon.visible = bool(problems)
        self._warning_tooltip.text = " / ".join(problems)

        #marge a droite seulement quand l'icone est visible : les boutons
        #sans alerte restent serres dans la grille
        if self._warning_icon.visible:
            self._button_container.classes(add="mr-10", remove="mr-0")
        else:
            self._button_container.classes(add="mr-0", remove="mr-10")

    #couleur du corps selon l'etat (idle adapte au theme, preview jaune,
    #programme rouge - identiques dans les deux themes), texte de la
    #pastille IN/OUT, visibilite permanente de "OUT" a l'antenne
    def _refresh_appearance(self) -> None:
        colors = {
            "idle": (
                "bg-slate-600 hover:bg-slate-500"
                if SceneButton._dark_mode
                else "bg-slate-700 hover:bg-slate-600"
            ),
            "preview": "bg-yellow-600 hover:bg-yellow-500",
            "programme": "bg-red-600 hover:bg-red-500",
        }

        self._main_area.classes(
            replace="flex-1 items-center justify-center px-2 py-2 cursor-pointer "
            + colors[self._state]
        )
        self._label_widget.text = self._label_text()

        on_air = self._state == "programme"
        self._hover_label.text = "OUT" if on_air else "IN"
        if self._edit_actions is not None:
            visibility = "hidden"
        elif on_air:
            visibility = "opacity-100 pointer-events-auto"
        else:
            visibility = "opacity-0 group-hover:opacity-100 pointer-events-none group-hover:pointer-events-auto"
        self._hover_label.classes(
            replace="absolute bottom-full left-1/2 -translate-x-1/2 transition-opacity "
            "bg-slate-800 text-white text-sm font-bold rounded-full px-4 py-1.5 "
            "cursor-pointer border border-slate-600 whitespace-nowrap z-10 " + visibility
        )

        #champs non modifiables tant que le graphique n'est pas idle
        for select_widget, input_widget in self._free_text_widgets.values():
            for widget in (select_widget, input_widget):
                if widget is None:
                    continue
                if self._state == "idle":
                    widget.enable()
                else:
                    widget.disable()

    async def _on_main_click(self) -> None:
        if self._edit_actions is not None:
            await self._edit_actions[0]()
            return
        if self._state == "idle":
            await self._play("prw")
        elif self._state == "preview":
            await self._take()

    async def _on_hover_click(self) -> None:
        if self._edit_actions is not None:
            return
        if self._state == "programme":
            await self._stop()
        elif self._state == "preview":
            await self._take()
        else:
            await self._play("pgm")

    async def _on_next_page(self) -> None:
        self._page += 1
        self._refresh_appearance()
        if self._state != "idle":
            await self._update_data()

    async def _on_prev_page(self) -> None:
        if self._page <= 1:
            return
        self._page -= 1
        self._refresh_appearance()
        if self._state != "idle":
            await self._update_data()

    #assemble les donnees envoyees au template selon les options actives
    def _build_payload(self) -> dict[str, str]:
        payload = dict(self.extra_data)

        if self.send_ip and self.data is not None:
            payload[self.field_ip] = self.data.ip

        if self.multipage_on:
            payload[self.field_page] = str(self._page)

        for field, (select_widget, input_widget) in self._free_text_widgets.items():
            value = (select_widget.value if select_widget else None) or input_widget.value
            payload[field] = str(value) if value else ""

        #12.0 -> "12" (ui.number renvoie des float)
        for field, number_widget in self._number_widgets.items():
            value = number_widget.value
            if value is None:
                payload[field] = ""
            else:
                payload[field] = str(int(value)) if float(value).is_integer() else str(value)

        return payload

    async def _play(self, channel: str) -> None:
        if self.multipage_on and self.reset_page_on_play:
            self._page = 1

        payload = self._build_payload()

        if channel == "prw":
            await self._claim_preview()
        else:
            await self._claim_pgm_slot()

        response = await self.caspar.play_template(
            channel, self.template, data=payload, layer=self.layer, cg_layer=self.cg_layer
        )

        if response.is_error:
            self._log(f"PLAY {channel.upper()} : ERREUR - {response.message}")
            ui.notify(f"Erreur lors du play : {response.message}", type="negative")
            return

        self._log(
            f"PLAY {'PREVIEW' if channel == 'prw' else 'PROGRAMME'} "
            f"(template={self.template}, layer={self.layer}, cg_layer={self.cg_layer}) "
            f"OK - donnees : {payload}"
        )

        await self._play_second_cg(channel, payload)

        self._state = "preview" if channel == "prw" else "programme"
        if channel == "prw":
            SceneButton._active_preview[(self.layer, self.cg_layer)] = self
        else:
            SceneButton._active_pgm[(self.layer, self.cg_layer)] = self
        self._refresh_appearance()

    #un seul occupant par (layer, cg_layer) de preview : remet a idle
    #l'ancien occupant puis clear ce layer cote CasparCG (inconditionnel,
    #meme si le suivi local est desynchronise)
    async def _claim_preview(self) -> None:
        previous = SceneButton._active_preview.get((self.layer, self.cg_layer))
        if previous is not None and previous is not self:
            previous.reset_to_idle()

        await self.caspar.clear("prw", layer=self.layer)

    #un seul occupant par (layer, cg_layer) programme : stoppe l'ancien
    async def _claim_pgm_slot(self) -> None:
        previous = SceneButton._active_pgm.get((self.layer, self.cg_layer))
        if previous is not None and previous is not self:
            await previous._stop()

    def _second_cg_video_layer(self) -> int:
        return self.second_cg_layer if self.second_cg_layer is not None else self.layer

    #TOUJOURS cg_layer + 1 : si second_cg_layer est omis, les deux
    #producers partagent le meme layer video, et un CG ADD sur un
    #(adresse, cg_layer) deja occupe REMPLACE silencieusement le principal
    def _second_cg_stack_layer(self) -> int:
        return self.cg_layer + 1

    async def _play_second_cg(self, channel: str, payload: dict[str, str]) -> None:
        if not self.second_cg:
            return

        response = await self.caspar.play_template(
            channel,
            self.second_cg,
            data=payload,
            layer=self._second_cg_video_layer(),
            cg_layer=self._second_cg_stack_layer(),
        )

        if response.is_error:
            self._log(f"PLAY {channel.upper()} second CG '{self.second_cg}' : ERREUR - {response.message}")
            ui.notify(f"Erreur lors du play du second CG : {response.message}", type="negative")
            return

        self._log(f"PLAY {channel.upper()} second CG '{self.second_cg}' OK")

        if channel == "prw":
            self._second_cg_payload = payload

    async def _take(self) -> None:
        await self._claim_pgm_slot()

        response = await self.caspar.play_prw_to_pgm(self.layer, cg_layer=self.cg_layer)

        if response.is_error:
            self._log(f"TAKE : ERREUR - {response.message}")
            ui.notify(f"Erreur lors du take : {response.message}", type="negative")
            return

        self._log(f"TAKE (preview -> programme, layer={self.layer}, cg_layer={self.cg_layer}) OK")

        #play_prw_to_pgm n'a repris que le producer principal : rejouer le
        #second CG a la main, puis le clearer en preview s'il y etait sur
        #son propre layer (le clear de play_prw_to_pgm ne vise que self.layer)
        if self.second_cg and self._second_cg_payload is not None:
            second_response = await self.caspar.play_template(
                "pgm",
                self.second_cg,
                data=self._second_cg_payload,
                layer=self._second_cg_video_layer(),
                cg_layer=self._second_cg_stack_layer(),
            )
            if second_response.is_error:
                self._log(f"TAKE second CG '{self.second_cg}' : ERREUR - {second_response.message}")
                ui.notify(f"Erreur lors du take du second CG : {second_response.message}", type="negative")

            if self._second_cg_video_layer() != self.layer:
                await self.caspar.clear("prw", layer=self._second_cg_video_layer())

        self._state = "programme"
        key = (self.layer, self.cg_layer)
        SceneButton._active_pgm[key] = self
        if SceneButton._active_preview.get(key) is self:
            del SceneButton._active_preview[key]
        self._refresh_appearance()

    async def _stop(self) -> None:
        response = await self.caspar.stop("pgm", layer=self.layer, cg_layer=self.cg_layer)

        if response.is_error:
            self._log(f"STOP : ERREUR - {response.message}")
            ui.notify(f"Erreur lors du stop : {response.message}", type="negative")
            return

        self._log(f"STOP (programme, layer={self.layer}, cg_layer={self.cg_layer}) OK")

        if self.second_cg:
            second_response = await self.caspar.stop(
                "pgm", layer=self._second_cg_video_layer(), cg_layer=self._second_cg_stack_layer()
            )
            if second_response.is_error:
                self._log(f"STOP second CG '{self.second_cg}' : ERREUR - {second_response.message}")
                ui.notify(f"Erreur lors du stop du second CG : {second_response.message}", type="negative")

        self._state = "idle"
        self._second_cg_payload = None
        if SceneButton._active_pgm.get((self.layer, self.cg_layer)) is self:
            del SceneButton._active_pgm[(self.layer, self.cg_layer)]
        self._refresh_appearance()

    #renvoie les donnees actuelles au graphique deja affiche (et au second
    #CG, payload memorise a nouveau si en preview pour un futur Take)
    async def _update_data(self) -> None:
        channel = "prw" if self._state == "preview" else "pgm"
        payload = self._build_payload()

        response = await self.caspar.update_template(
            channel, payload, layer=self.layer, cg_layer=self.cg_layer
        )

        if response.is_error:
            self._log(f"UPDATE {channel.upper()} : ERREUR - {response.message}")
            ui.notify(f"Erreur lors de la mise a jour : {response.message}", type="negative")
        else:
            self._log(f"UPDATE {channel.upper()} OK - donnees : {payload}")

        if self.second_cg:
            second_response = await self.caspar.update_template(
                channel,
                payload,
                layer=self._second_cg_video_layer(),
                cg_layer=self._second_cg_stack_layer(),
            )
            if second_response.is_error:
                self._log(f"UPDATE {channel.upper()} second CG : ERREUR - {second_response.message}")
                ui.notify(f"Erreur lors de la mise a jour du second CG : {second_response.message}", type="negative")
            if channel == "prw":
                self._second_cg_payload = payload
