# services/checkout/Dockerfile
# Conforme a secao "Build e Deployment" da constituicao: cada microsservico do
# monorepo tem seu proprio Dockerfile, dentro da sua propria pasta.
#
# O contexto de build deve ser a RAIZ do workspace uv (monorepo), para que
# "uv sync --package checkout" resolva tambem a dependencia local libs/contracts:
#   docker build -f services/checkout/Dockerfile -t checkout:local .

FROM python:3.12-slim AS base

# Binario do uv, copiado direto da imagem oficial (nada de pip aqui).
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

WORKDIR /app

# Copia o workspace inteiro (root pyproject.toml + uv.lock, quando existir, e
# os membros usados por este servico). Nao usa .dockerignore agressivo demais
# porque o uv precisa enxergar todos os membros do workspace para resolver.
COPY pyproject.toml uv.lock* /app/
COPY libs/contracts /app/libs/contracts
COPY services/checkout /app/services/checkout

ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# --frozen exige uv.lock commitado (rode "uv lock" na raiz do workspace antes
# do primeiro build reprodutivel). Sem uv.lock ainda, o build resolve on the fly.
RUN uv sync --package checkout --no-dev

WORKDIR /app/services/checkout

EXPOSE 8000

HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Aplica as migracoes pendentes e so entao sobe o servidor - necessario para
# "docker compose up" funcionar sem passo manual (ver README para o fluxo
# hibrido, onde a migracao e rodada a parte).
CMD ["sh", "-c", "uv run --no-sync alembic upgrade head && uv run --no-sync uvicorn src.main:app --host 0.0.0.0 --port 8000"]
