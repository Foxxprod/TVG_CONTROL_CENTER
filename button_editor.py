# Boite de dialogue du MODE EDITION : creation/modification d'un bouton de
# la grille (tous les attributs de templates.json). Ne touche jamais au
# fichier elle-meme : renvoie la nouvelle definition (ou None si annule),
# c'est interface.build_body qui la persiste et reconstruit la grille.

from nicegui import ui

from buttons_config import validate_button
from project import SECTIONS

FREE_TEXT_KINDS = {"text": "Texte", "list": "Liste", "number": "Nombre"}


def _int_or_none(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


#entry : definition existante (None = nouveau bouton) ; position :
#(section, row, column) proposee pour un nouveau bouton (case du "+"
#clique). Renvoie un NOUVEAU dict, jamais l'entree d'origine modifiee.
async def open_button_editor(
    entry: dict | None,
    position: tuple[str, int, int],
    button_fields: set[str],
    has_data_source: bool,
) -> dict | None:
    source = entry or {}
    section, row, column = (
        (source["section"], source.get("row", 1), source.get("column", 1)) if entry else position
    )

    #listes editables (lignes ajoutees/retirees dans la boite)
    free_texts = [
        {
            "field": ft.get("field", ""),
            "label": ft.get("label", ""),
            "kind": "number" if ft.get("type") == "number" else ("list" if ft.get("options") is not None else "text"),
            "options": "\n".join(ft.get("options") or []),
            "min": ft.get("min"),
            "max": ft.get("max"),
            "step": ft.get("step", 1),
            "default": ft.get("default", 0),
        }
        for ft in source.get("free_texts", [])
    ]
    extra_data = [{"key": key, "value": str(value)} for key, value in source.get("extra_data", {}).items()]

    def subtitle(text: str) -> None:
        ui.label(text).classes("text-xs font-bold uppercase tracking-wide text-slate-500 mt-2")

    with ui.dialog().props("persistent") as dialog, ui.card().classes("w-[44rem] max-w-[95vw] gap-2"):
        ui.label("Modifier le bouton" if entry else "Nouveau bouton").classes("text-lg font-bold")

        with ui.scroll_area().classes("w-full h-[62vh]"):
            with ui.column().classes("w-full gap-2 pr-3"):
                subtitle("Graphique")
                with ui.row(wrap=False).classes("w-full gap-2"):
                    label_input = ui.input("Label *", value=source.get("label", "")).classes("flex-1")
                    template_input = ui.input("Template CasparCG *", value=source.get("template", "")).classes("flex-1")
                with ui.row(wrap=False).classes("w-full gap-2"):
                    layer_input = ui.number("Layer *", value=source.get("layer"), min=1, step=1, format="%d").classes("flex-1")
                    cg_layer_input = ui.number("CG layer", value=source.get("cg_layer", 1), min=1, step=1, format="%d").classes("flex-1")

                subtitle("Position")
                with ui.row(wrap=False).classes("w-full gap-2"):
                    section_select = ui.select(dict(SECTIONS), value=section, label="Section").classes("flex-1")
                    row_input = ui.number("Ligne", value=row, min=1, step=1, format="%d").classes("w-28")
                    column_input = ui.number("Colonne", value=column, min=1, step=1, format="%d").classes("w-28")

                subtitle("Multipage")
                with ui.row(wrap=False).classes("w-full items-center gap-4"):
                    multipage_switch = ui.switch("Fleches de page", value=source.get("multipage_on", False))
                    reset_page_switch = ui.switch(
                        "Page 1 a chaque play", value=source.get("reset_page_on_play", False)
                    ).bind_visibility_from(multipage_switch, "value")
                    field_page_input = ui.input(
                        "Champ page", value=source.get("field_page", "page")
                    ).classes("w-32").bind_visibility_from(multipage_switch, "value")

                subtitle("Textes libres / listes a choix")

                @ui.refreshable
                def free_texts_editor() -> None:
                    for index, ft in enumerate(free_texts):
                        with ui.column().classes("w-full border border-slate-300 rounded-xl p-2 gap-1"):
                            with ui.row(wrap=False).classes("w-full items-center gap-2"):
                                ui.input("Champ template *").bind_value(ft, "field").classes("flex-1")
                                ui.input("Libelle").bind_value(ft, "label").classes("flex-1")
                                ui.select(FREE_TEXT_KINDS, label="Type").bind_value(ft, "kind").classes("w-28")
                                ui.button(
                                    icon="delete", color=None,
                                    on_click=lambda _, i=index: (free_texts.pop(i), free_texts_editor.refresh()),
                                ).props("flat round dense").classes("text-red-500")
                            ui.textarea("Options (une par ligne)").bind_value(ft, "options").bind_visibility_from(
                                ft, "kind", value="list"
                            ).props("autogrow").classes("w-full")
                            with ui.row(wrap=False).classes("w-full gap-2").bind_visibility_from(
                                ft, "kind", value="number"
                            ):
                                for key, text in (("min", "Min"), ("max", "Max"), ("step", "Pas"), ("default", "Defaut")):
                                    ui.number(text).bind_value(ft, key).classes("flex-1")
                    ui.button(
                        "Ajouter un champ", icon="add", color=None,
                        on_click=lambda: (
                            free_texts.append(
                                {"field": "", "label": "", "kind": "text", "options": "",
                                 "min": None, "max": None, "step": 1, "default": 0}
                            ),
                            free_texts_editor.refresh(),
                        ),
                    ).props("flat dense no-caps").classes("text-sky-600")

                free_texts_editor()

                subtitle("Donnees fixes (extra_data)")

                @ui.refreshable
                def extra_data_editor() -> None:
                    for index, pair in enumerate(extra_data):
                        with ui.row(wrap=False).classes("w-full items-center gap-2"):
                            ui.input("Champ").bind_value(pair, "key").classes("flex-1")
                            ui.input("Valeur").bind_value(pair, "value").classes("flex-1")
                            ui.button(
                                icon="delete", color=None,
                                on_click=lambda _, i=index: (extra_data.pop(i), extra_data_editor.refresh()),
                            ).props("flat round dense").classes("text-red-500")
                    ui.button(
                        "Ajouter une donnee", icon="add", color=None,
                        on_click=lambda: (extra_data.append({"key": "", "value": ""}), extra_data_editor.refresh()),
                    ).props("flat dense no-caps").classes("text-sky-600")

                extra_data_editor()

                subtitle("Second graphique (optionnel)")
                with ui.row(wrap=False).classes("w-full gap-2"):
                    second_cg_input = ui.input("Template second CG", value=source.get("second_cg") or "").classes("flex-1")
                    second_cg_layer_input = ui.number(
                        "Layer second CG", value=source.get("second_cg_layer"), min=1, step=1, format="%d"
                    ).classes("w-40")

                if has_data_source:
                    subtitle("Source de donnees")
                    with ui.row(wrap=False).classes("w-full items-center gap-4"):
                        send_ip_switch = ui.switch("Envoyer l'IP de la source", value=source.get("send_ip", False))
                        field_ip_input = ui.input(
                            "Champ IP", value=source.get("field_ip", "ip")
                        ).classes("w-32").bind_visibility_from(send_ip_switch, "value")

        error_label = ui.label("").classes("text-xs text-red-500 font-mono")

        #construit la definition depuis le formulaire (seulement les champs
        #utiles - templates.json reste lisible), la valide avec les MEMES
        #regles que le chargement du fichier, et ferme si tout est correct
        def on_save() -> None:
            new: dict = {"_comment": source["_comment"]} if "_comment" in source else {}
            new.update(
                section=section_select.value,
                row=_int_or_none(row_input.value) or 1,
                column=_int_or_none(column_input.value) or 1,
                label=(label_input.value or "").strip(),
                template=(template_input.value or "").strip(),
                layer=_int_or_none(layer_input.value),
            )
            if not new["label"] or not new["template"] or new["layer"] is None:
                error_label.text = "Label, template et layer sont obligatoires."
                return

            cg_layer = _int_or_none(cg_layer_input.value) or 1
            if cg_layer != 1:
                new["cg_layer"] = cg_layer

            if multipage_switch.value:
                new["multipage_on"] = True
                if reset_page_switch.value:
                    new["reset_page_on_play"] = True
                if (field_page_input.value or "page") != "page":
                    new["field_page"] = field_page_input.value

            texts = []
            for ft in free_texts:
                field = (ft["field"] or "").strip()
                if not field:
                    error_label.text = "Chaque texte libre doit avoir un champ template."
                    return
                item = {"field": field}
                if (ft["label"] or "").strip():
                    item["label"] = ft["label"].strip()
                if ft["kind"] == "list":
                    item["options"] = [o.strip() for o in (ft["options"] or "").splitlines() if o.strip()]
                elif ft["kind"] == "number":
                    item["type"] = "number"
                    for key in ("min", "max", "step", "default"):
                        if ft[key] is not None:
                            value = float(ft[key])
                            item[key] = int(value) if value.is_integer() else value
                texts.append(item)
            if texts:
                new["free_texts"] = texts

            extras = {p["key"].strip(): p["value"] or "" for p in extra_data if (p["key"] or "").strip()}
            if extras:
                new["extra_data"] = extras

            if (second_cg_input.value or "").strip():
                new["second_cg"] = second_cg_input.value.strip()
                second_layer = _int_or_none(second_cg_layer_input.value)
                if second_layer is not None:
                    new["second_cg_layer"] = second_layer

            if has_data_source and send_ip_switch.value:
                new["send_ip"] = True
                if (field_ip_input.value or "ip") != "ip":
                    new["field_ip"] = field_ip_input.value

            error = validate_button(new, [key for key, _ in SECTIONS], button_fields, has_data_source)
            if error:
                error_label.text = error
                return

            dialog.submit(new)

        with ui.row().classes("justify-end gap-2 w-full"):
            ui.button("Annuler", on_click=lambda: dialog.submit(None))
            ui.button("Enregistrer", on_click=on_save).classes("bg-slate-800 text-white")

    result = await dialog
    dialog.delete()
    return result
