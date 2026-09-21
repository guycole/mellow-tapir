# Tapir MCP Server

This directory contains an MCP server with both stdio and streamable HTTP transports.
The server uses data from `src/tapir_schema/seed.json` and source schema text from
`src/tapir_schema/schema.sql`, then serves a read-only SQLite catalog.

## Python environment

Use the existing local virtual environment:

```bash
cd src/tapir_mcp_server
./venv/bin/python -m pip install -r requirements.txt
```

## Build the SQLite database

```bash
cd /Users/gsc/github/mellow-tapir/src/tapir_mcp_server
./venv/bin/python -m mcp_server.build_db \
  --db-path data/tapir.sqlite \
  --seed-path ../tapir_schema/seed.json \
  --schema-path ../tapir_schema/schema.sql
```

## Run in stdio mode

```bash
cd /Users/gsc/github/mellow-tapir/src/tapir_mcp_server
TAPIR_DB_PATH=data/tapir.sqlite \
TAPIR_SEED_PATH=../tapir_schema/seed.json \
TAPIR_SCHEMA_PATH=../tapir_schema/schema.sql \
./venv/bin/python -m mcp_server --transport stdio
```

## Run in HTTP mode

```bash
cd /Users/gsc/github/mellow-tapir/src/tapir_mcp_server
TAPIR_DB_PATH=data/tapir.sqlite \
TAPIR_SEED_PATH=../tapir_schema/seed.json \
TAPIR_SCHEMA_PATH=../tapir_schema/schema.sql \
REFERENCE_LLM_MODEL=gpt-oss:20b \
OLLAMA_BASE_URL=http://127.0.0.1:11434 \
./venv/bin/python -m mcp_server \
  --transport http --host 0.0.0.0 --port 8000 --path /mcp
```

## Local testing with Ollama gpt-oss:20b

Start Ollama and ensure the reference model is available:

```bash
ollama serve
```

In another terminal:

```bash
ollama pull gpt-oss:20b
ollama run gpt-oss:20b "Summarize the purpose of this MCP server in one sentence."
```

Run the MCP server with the same local Ollama endpoint:

```bash
cd /Users/gsc/github/mellow-tapir/src/tapir_mcp_server
TAPIR_DB_PATH=data/tapir.sqlite \
TAPIR_SEED_PATH=../tapir_schema/seed.json \
TAPIR_SCHEMA_PATH=../tapir_schema/schema.sql \
REFERENCE_LLM_MODEL=gpt-oss:20b \
OLLAMA_BASE_URL=http://127.0.0.1:11434 \
./venv/bin/python -m mcp_server --transport http --host 127.0.0.1 --port 8000 --path /mcp
```

When connected with an MCP client, call `ask_reference_model` with a test prompt.
If Ollama is reachable and the model is present, the tool returns a response body
and metadata including model and done status.

## Available tools

- `classify_frequency`: find matching services and channels for one frequency.
- `query_channels`: list named channels in a frequency range.
- `search_services`: search by service text and use text.
- `execute_readonly_sql`: run a SELECT or CTE query with row limit protection.
- `ask_reference_model`: optional Ollama call, defaulting to `gpt-oss:20b`.

## Available resources

- `tapir://metadata`
- `tapir://sources/seed-json`
- `tapir://sources/schema-sql`

## Docker

Build locally:

```bash
cd /Users/gsc/github/mellow-tapir
docker build -f src/tapir_mcp_server/Dockerfile -t tapir-mcp:local .
```

Run:

```bash
docker run --rm -p 8080:8080 \
  -e OLLAMA_BASE_URL=http://host.docker.internal:11434 \
  tapir-mcp:local
```

The GitHub Actions workflow in `.github/workflows/tapir-mcp-server-image.yml` publishes
images to GitHub Container Registry.

## SQLite data lineage and refresh

The SQLite database in `data/tapir.sqlite` is generated from two source files:

- `src/tapir_schema/seed.json`: canonical editable catalog of bands, emissions, and channels.
- `src/tapir_schema/schema.sql`: source PostgreSQL schema retained for provenance and parity checks.

Generation is handled by `mcp_server.build_db`, which:

- creates SQLite tables (`band`, `band_emission`, `channel`, `dataset_metadata`),
- reloads records from `seed.json`,
- stores source provenance metadata (including source paths and schema SQL text),
- produces a read-ready file used in read-only mode by the MCP server.

When updating the dataset in the future:

1. Edit `src/tapir_schema/seed.json`.
2. Optionally update `src/tapir_schema/schema.sql` if source-schema intent changed.
3. Rebuild SQLite:

```bash
cd /Users/gsc/github/mellow-tapir/src/tapir_mcp_server
./venv/bin/python -m mcp_server.build_db \
  --db-path data/tapir.sqlite \
  --seed-path ../tapir_schema/seed.json \
  --schema-path ../tapir_schema/schema.sql
```

4. Restart the MCP server so it uses the refreshed SQLite file.

The container image build also runs this same build step during `docker build`,
so image contents stay aligned with the latest checked-in `seed.json` and `schema.sql`.
