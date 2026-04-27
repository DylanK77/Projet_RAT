## Projet RAT (Python)

Client/serveur TCP chiffré (TLS), multi-sessions, interactif.

## Prérequis

- Python **3.10+**
- Poetry

## Installation

```bash
python -m pip install --user poetry
python -m poetry install
```

## Génération des certificats TLS

```bash
python -m poetry run rat-gen-certs --out certs
```

## Lancer le serveur

```bash
python -m poetry run rat-server --host 0.0.0.0 --port 8888 --certs certs
```

## Lancer le client

```bash
python -m poetry run rat-client --host 127.0.0.1 --port 8888 --server-name localhost --certs certs
```

## Logs

- Serveur : `data/logs/server.log`
- Client : `data/logs/client.log`
- Niveau configurable : `RAT_LOG_LEVEL=DEBUG`

## Qualité

```bash
python -m poetry run pre-commit install
python -m poetry run pre-commit run -a
```

## Tests

```bash
python -m poetry run pytest
```

## Docker (serveur uniquement)

```bash
docker compose up --build
```

> Les certificats (`./certs`) doivent être générés avant.

## Web UI (bonus)

```bash
python -m poetry run rat-web --host 127.0.0.1 --port 8000
```