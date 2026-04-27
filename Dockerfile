FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir poetry==2.3.2

COPY pyproject.toml poetry.lock README.md ./

RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-interaction --no-ansi

COPY src ./src

EXPOSE 8888

CMD ["python", "-m", "rat.server", "--host", "0.0.0.0", "--port", "8888", "--certs", "certs"]