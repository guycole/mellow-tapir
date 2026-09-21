FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

LABEL io.modelcontextprotocol.server.name="io.github.guycole/mellow-tapir"

WORKDIR /app

COPY src/tapir_mcp_server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src/tapir_mcp_server/mcp_server /app/mcp_server
COPY src/tapir_schema /app/tapir_schema

RUN python -m mcp_server.build_db \
    --db-path /app/data/tapir.sqlite \
    --seed-path /app/tapir_schema/seed.json \
    --schema-path /app/tapir_schema/schema.sql \
    && chmod 444 /app/data/tapir.sqlite

RUN useradd --create-home --uid 10001 appuser
USER appuser

ENV TAPIR_DB_PATH=/app/data/tapir.sqlite
ENV TAPIR_SEED_PATH=/app/tapir_schema/seed.json
ENV TAPIR_SCHEMA_PATH=/app/tapir_schema/schema.sql
ENV REFERENCE_LLM_MODEL=gpt-oss:20b
ENV OLLAMA_BASE_URL=http://host.docker.internal:11434

EXPOSE 8080

CMD ["python", "-m", "mcp_server", "--transport", "http", "--host", "0.0.0.0", "--port", "8080", "--path", "/mcp"]
