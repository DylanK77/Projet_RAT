## Projet final - RAT (Python)

Ce dépôt contient un **serveur** et un **client** de RAT (Remote Administration Tool) en Python, avec communication **TCP chiffrée** (TLS), gestion **multi-agents**, interface serveur **interactive**, tests unitaires, et bonus (interface web + Docker).

## Objectif (conforme au sujet)

- **Client**: communication TCP **chiffrée et sécurisée**, compatible Windows/Linux, avec les commandes demandées.
- **Serveur**: écoute TCP, **multi-clients**, gestion de **sessions** + mode `interact`, help/gestion d’erreurs.

## Prérequis

- Python **3.10+**
- Accès webcam/micro si vous souhaitez tester `webcam_*` / `record_audio`
- Droits admin/root pour `hashdump` (sinon la commande répondra proprement avec un message d’erreur)

## Installation (Poetry)

Poetry est utilisé pour la gestion des dépendances.

Sous Windows (si `poetry` n’est pas dans le PATH), utilisez `python -m poetry`.

```bash
python -m pip install --user poetry
python -m poetry install
```

## Chiffrement TLS (obligatoire)

Le projet utilise **mTLS** (certificat client + serveur), avec CA locale.

Générer les certificats (portable Windows/Linux) :

```bash
python -m poetry run rat-gen-certs --out certs
```

Fichiers générés :

- `certs/ca.pem`
- `certs/server.pem`, `certs/server-key.pem`
- `certs/client.pem`, `certs/client-key.pem`

## Lancer le serveur

```bash
python -m poetry run rat-server --host 0.0.0.0 --port 8888 --certs certs
```

Commandes serveur :

- `help`
- `sessions`
- `interact <id>`
- `disconnect <id>`

## Lancer le client

```bash
python -m poetry run rat-client --host 127.0.0.1 --port 8888 --server-name localhost --certs certs
```

Le serveur affichera l’arrivée d’un agent, puis `sessions` permettra de lister les agents.

## Commandes agent (mode interact)

Dans `interact <id>`, vous pouvez exécuter :

- `help`
- `ipconfig`
- `search <pattern> [root]`
- `screenshot` → sauvegarde auto dans `captures/agent-<id>/`
- `webcam_snapshot` → sauvegarde auto dans `captures/agent-<id>/`
- `record_audio <seconds>` → sauvegarde auto dans `captures/agent-<id>/`
- `hashdump`
- `keylogger start|stop|dump`
- `shell <command>`
- `download <remote_path> [local_path]` → sauvegarde dans `downloads/agent-<id>/` par défaut
- `upload <local_path> <remote_path>`
- `webcam_stream start [seconds]` → sauvegarde frames dans `captures/agent-<id>/webcam_stream/`
- `webcam_stream stop`

## Logs (aucun print)

- Serveur: `data/logs/server.log`
- Client: `data/logs/client.log`

Le niveau est configurable via `RAT_LOG_LEVEL=DEBUG`.

## Qualité / pre-commit

```bash
python -m poetry run pre-commit install
python -m poetry run pre-commit run -a
```

Outils :

- Ruff (lint + format)
- Black
- Mypy

## Tests (pytest)

```bash
python -m poetry run pytest
```

## Bonus: Web UI (FastAPI)

Le serveur persiste un état minimal dans `data/state.json`.

Lancer la Web UI :

```bash
python -m poetry run rat-web --host 127.0.0.1 --port 8000 --state data/state.json
```

Endpoint :

- `GET /sessions`

## Bonus: Docker (serveur)

```bash
docker compose up --build
```

> Monter `./certs` est requis (mTLS).

## Plan de vidéo de démonstration (recommandé)

- Génération des certifs (`rat-gen-certs`)
- Lancement serveur + affichage “Listening”
- Connexion de 2 clients (2 OS si possible: Windows + Linux)
- `sessions` puis `interact`
- Démo commandes: `ipconfig`, `search`, `screenshot`, `download/upload`, `webcam_snapshot`, `webcam_stream start 5`, `record_audio 3`
- Arrêt client → le serveur gère la déconnexion
- Lancer `pytest` et `pre-commit run -a`

## Checklist “zéro malus”

- [x] Chiffrement TLS (mTLS) actif
- [x] Multi-clients + sessions + interact
- [x] Help côté serveur + client
- [x] Poetry + lockfile
- [x] pre-commit présent
- [x] Logger (aucun `print`)
- [x] Pytest (tests présents)
- [x] README complet
- [x] Compatible Windows/Linux (best-effort selon permissions/hardware)

