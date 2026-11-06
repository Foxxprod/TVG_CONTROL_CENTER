# Source de donnees externe (optionnelle)

Par defaut `project.DATA_SOURCE_CLASS = None` : **rien** de lie aux donnees
n'apparait (ni case de statut, ni reglages IP/port, ni bouton "Donnees
recues"), et `send_ip` est refuse dans `templates.json`. On ne branche une
source que lorsqu'elle est reellement implementee.

## Contrat (`data_source.DataSource`)

| Attribut / methode | Role |
|---|---|
| `status_title` | titre de la case de statut du header (ex: `"WS DATA"`) |
| `ip`, `port` | adresse (reglable dans Parametres -> `config.json` `data_ip`/`data_port`) |
| `connected` | pilote la case de statut et l'alerte des boutons `send_ip` |
| `last_ping_ms` | affiche au survol du statut |
| `latest_data` | dernier message brut (dict), affiche dans "Donnees recues" |
| `event_title` | titre d'epreuve fourni par la source (prioritaire sur Parametres si non vide) |
| `on_message(cb)` / `remove_listener(cb)` | abonnement aux nouveaux messages |
| `_notify()` | a appeler apres chaque message complet |
| `async connect()` | ouvrir + lancer la boucle de reception/reconnexion ; `None` ou message d'erreur |
| `async disconnect()` | fermer |
| `change_connection(ip, port)` | deja fourni (disconnect + connect) |

## Brancher une source WebSocket

1. Copier `references/websocket_data_source.py` dans le projet
   (`data_source_ws.py`).
2. `requirements.txt` : ajouter `websockets==15.0.1`.
3. `project.py` :
   ```python
   from data_source_ws import WebSocketDataSource
   DATA_SOURCE_CLASS = WebSocketDataSource
   ```
4. Adapter `_handle_message` au format reel (demander un exemple de message
   a l'utilisateur AVANT d'ecrire le parsing, ne pas le deviner).

## Utiliser les donnees dans un bouton

Ajouter une option au `SceneButton` (voir `button-options.md`, section
"Ajouter une nouvelle option") qui lit `self.data` dans `_build_payload`,
et s'abonner pour un rafraichissement instantane :

```python
self.data.on_message(callback)
ui.context.client.on_delete(lambda: self.data.remove_listener(callback))
```

`self.data` peut valoir `None` : toujours tester.
