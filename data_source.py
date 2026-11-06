# Source de donnees externe OPTIONNELLE (WebSocket, API HTTP, fichier...).
#
# Tant que project.DATA_SOURCE_CLASS vaut None, create_data_source() renvoie
# None et l'interface n'affiche RIEN de lie aux donnees (pas de case de
# statut dans le header, pas de reglages IP/port, pas de bouton "donnees",
# send_ip refuse dans templates.json).
#
# Pour en brancher une : sous-classer DataSource, implementer connect()/
# disconnect(), mettre a jour self.connected / self.latest_data, appeler
# self._notify() a chaque nouveau message complet, puis declarer la classe
# dans project.py (DATA_SOURCE_CLASS). Exemple complet WebSocket : voir la
# reference du skill (references/websocket_data_source.py).

import traceback
from collections.abc import Callable


class DataSource:
    #titre de la case de statut du header
    status_title = "DATA"

    def __init__(self, ip: str, port: int):
        self.ip = ip
        self.port = port

        self.connected = False
        #temps d'aller-retour mesure (ms), affiche au survol du statut
        self.last_ping_ms: float | None = None
        #dernier message complet recu, TEL QUEL (dict JSON) - affiche dans
        #la boite de dialogue "Donnees recues" du header
        self.latest_data: dict | None = None
        #titre d'epreuve fourni par la source (prioritaire sur
        #config["event_title"] s'il est non vide)
        self.event_title: str = ""

        self._listeners: list[Callable[[], None]] = []

    #abonne callback (synchrone, sans argument) aux nouveaux messages
    #complets. Penser a remove_listener() a la fermeture de la page
    #(singleton partage par tous les onglets, voir main.py).
    def on_message(self, callback: Callable[[], None]) -> None:
        self._listeners.append(callback)

    def remove_listener(self, callback: Callable[[], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    #a appeler par la sous-classe apres chaque message complet traite - un
    #listener qui leve ne doit jamais interrompre la reception
    def _notify(self) -> None:
        for listener in list(self._listeners):
            try:
                listener()
            except Exception:
                traceback.print_exc()

    #ouvre la connexion et lance la boucle de reception/reconnexion.
    #Renvoie None si OK, sinon un message d'erreur (meme contrat que
    #CasparCG.connect)
    async def connect(self) -> str | None:
        raise NotImplementedError

    async def disconnect(self) -> None:
        raise NotImplementedError

    #change l'adresse et reconnecte aussitot (boite de dialogue Parametres)
    async def change_connection(self, ip: str, port: int) -> str | None:
        await self.disconnect()
        self.ip = ip
        self.port = port
        return await self.connect()


#import de project DIFFERE : project.py importe la sous-classe, qui importe
#ce module - un import en tete de fichier serait circulaire
def create_data_source(config: dict) -> DataSource | None:
    from project import DATA_SOURCE_CLASS

    if DATA_SOURCE_CLASS is None:
        return None
    return DATA_SOURCE_CLASS(config["data_ip"], config["data_port"])
