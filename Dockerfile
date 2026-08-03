FROM python:3.11-slim
# Ingestion de l'exécutable uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copie et installation des dépendances
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# Copie du code source
COPY . .

# Lancement de FastAPI
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
