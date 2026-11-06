# Exemple COMPLET de source de donnees WebSocket (JSON), a copier dans le
# projet (ex: data_source_ws.py) quand le projet en a besoin, puis :
#   - requirements.txt : ajouter  websockets==15.0.1
#   - project.py       : from data_source_ws import WebSocketDataSource
#                        DATA_SOURCE_CLASS = WebSocketDataSource
#
# Derive de la connexion du Biath Control Center (reconnexion automatique,
# ping natif mesure, JSON parfois double-encode). A ADAPTER : _handle_message
# (quel message est "complet", d'ou vient event_title, quels attributs
# metier exposer aux boutons).

import asyncio
import json

import websockets

from data_source import DataSource


class WebSocketDataSource(DataSource):
    status_title = "WS DATA"

    def __init__(self, ip: str, port: int, path: str = "/"):
        super().__init__(ip, port)
        self.path = path
        self.timeout = 5.0
        self.reconnect_delay = 5.0
        self._ping_interval = 5.0

        self.ws: websockets.ClientConnection | None = None
        self._lock = asyncio.Lock()
        self._receive_task: asyncio.Task | None = None
        self._ping_task: asyncio.Task | None = None

    @property
    def url(self) -> str:
        return f"ws://{self.ip}:{self.port}{self.path}"

    #la boucle de reception/reconnexion demarre meme si la 1ere tentative
    #echoue (serveur pas encore lance) - meme contrat que CasparCG.connect
    async def connect(self) -> str | None:
        error = await self._open()

        if self._receive_task is None or self._receive_task.done():
            self._receive_task = asyncio.create_task(self._receive_loop())
        if self._ping_task is None or self._ping_task.done():
            self._ping_task = asyncio.create_task(self._ping_loop())

        return error

    async def _open(self) -> str | None:
        async with self._lock:
            if self.ws is not None:
                try:
                    await self.ws.close()
                except OSError:
                    pass
                self.ws = None
            try:
                self.ws = await asyncio.wait_for(websockets.connect(self.url), timeout=self.timeout)
            except (OSError, asyncio.TimeoutError, websockets.exceptions.WebSocketException) as exc:
                self.connected = False
                return str(exc)
            self.connected = True
            return None

    async def _receive_loop(self) -> None:
        while True:
            if self.connected and self.ws is not None:
                try:
                    async for raw_message in self.ws:
                        self._handle_message(raw_message)
                except websockets.exceptions.WebSocketException:
                    pass
                self.connected = False
            else:
                await asyncio.sleep(self.reconnect_delay)
                await self._open()

    #ping/pong NATIF WebSocket (frame de controle) - mesure last_ping_ms
    async def _ping_loop(self) -> None:
        while True:
            await asyncio.sleep(self._ping_interval)
            if not self.connected or self.ws is None:
                continue
            try:
                start = asyncio.get_event_loop().time()
                pong_waiter = await self.ws.ping()
                await asyncio.wait_for(pong_waiter, timeout=self.timeout)
                self.last_ping_ms = (asyncio.get_event_loop().time() - start) * 1000
            except (OSError, asyncio.TimeoutError, websockets.exceptions.WebSocketException):
                self.last_ping_ms = None

    #A ADAPTER au format reel des messages du logiciel de donnees
    def _handle_message(self, raw_message: str | bytes) -> None:
        try:
            message = json.loads(raw_message)
            #certains serveurs encodent le JSON deux fois
            if isinstance(message, str):
                message = json.loads(message)
        except (json.JSONDecodeError, TypeError):
            return

        if not isinstance(message, dict):
            return

        self.latest_data = message
        self.event_title = str(message.get("title", "") or "")
        self._notify()

    async def disconnect(self) -> None:
        for task in (self._receive_task, self._ping_task):
            if task is not None:
                task.cancel()
        self._receive_task = None
        self._ping_task = None

        async with self._lock:
            if self.ws is not None:
                try:
                    await self.ws.close()
                except OSError:
                    pass
            self.ws = None
            self.connected = False
