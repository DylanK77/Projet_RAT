## Projet RAT (Python)

Remote Administration Tool – client/serveur TCP chiffré (TLS), multi-sessions.

## Prérequis

- Python **3.10+**
- Poetry

## Installation (Poetry)

Sous Windows (si `poetry` n'est pas dans le PATH), utilisez `python -m poetry`.

```bash
pip install --user poetry
poetry install
```

## Qualité / pre-commit

```bash
poetry run pre-commit install
poetry run pre-commit run -a
```

Outils :
- Ruff (lint + format)
- Black
- Mypy

## Tests

```bash
poetry run pytest
```

> La documentation métier (commandes serveur/client, TLS, Docker) sera ajoutée
> au fur et à mesure de l'implémentation.