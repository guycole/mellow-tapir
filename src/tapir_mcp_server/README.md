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

## Sample local MCP session (with Ollama)

This sample session verifies end-to-end behavior:

1. Build or refresh the SQLite catalog.
2. Start Ollama and pull `gpt-oss:20b`.
3. Start the MCP server over HTTP.
4. Connect with a client and call tools.

Terminal 1: start Ollama

```bash
ollama serve
```

Terminal 2: pull model and optional sanity prompt

```bash
ollama pull gpt-oss:20b
ollama run gpt-oss:20b "Reply with: Ollama ready"
```

Terminal 3: start Tapir MCP server

```bash
cd /Users/gsc/github/mellow-tapir/src/tapir_mcp_server
./venv/bin/python -m mcp_server.build_db \
  --db-path data/tapir.sqlite \
  --seed-path ../tapir_schema/seed.json \
  --schema-path ../tapir_schema/schema.sql

TAPIR_DB_PATH=data/tapir.sqlite \
TAPIR_SEED_PATH=../tapir_schema/seed.json \
TAPIR_SCHEMA_PATH=../tapir_schema/schema.sql \
REFERENCE_LLM_MODEL=gpt-oss:20b \
OLLAMA_BASE_URL=http://127.0.0.1:11434 \
./venv/bin/python -m mcp_server --transport http --host 127.0.0.1 --port 8000 --path /mcp
```

Terminal 4: sample client requests

```bash
cd /Users/gsc/github/mellow-tapir
/Users/gsc/github/mellow-tapir/src/tapir_mcp_server/venv/bin/python - <<'PY'
import anyio
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main() -> None:
    async with streamable_http_client("http://127.0.0.1:8000/mcp") as (
        read_stream,
        write_stream,
    ):
        session = ClientSession(read_stream, write_stream)
        async with session:
            await session.initialize()

            classify = await session.call_tool(
                "classify_frequency", {"frequency": "121.5"}
            )
            print("classify_frequency:")
            print(classify.content[0].text)

            llm = await session.call_tool(
                "ask_reference_model",
                {
                    "prompt": "Explain 121.5 MHz in one sentence.",
                    "temperature": 0.1,
                },
            )
            print("ask_reference_model:")
            print(llm.content[0].text)


anyio.run(main)
PY
```

Expected outcome:

- `classify_frequency` returns aviation emergency channel data around `121.5 MHz`.
- `ask_reference_model` returns a completion from local Ollama model `gpt-oss:20b`.

## Available tools

- `classify_frequency`
  - Purpose: classify a single frequency into matching bands and exact known channels.
  - Input: `frequency` as numeric Hz, MHz string (`121.5`), or explicit unit (`121.5MHz`).
  - Output: frequency metadata, channel matches, and band matches with emissions.
- `query_channels`
  - Purpose: list known channels in a frequency range.
  - Input: `lower_hz`, `upper_hz`, optional `limit`.
  - Output: ordered channel rows with labels, services, and emissions.
- `search_services`
  - Purpose: text search across service names and use names.
  - Input: `service_query`, optional `limit`.
  - Output: matching service/use combinations with range summaries.
- `execute_readonly_sql`
  - Purpose: ad hoc read-only analysis over the SQLite catalog.
  - Input: SQL `SELECT` or `WITH` query and optional `limit`.
  - Output: column list, row list, and row count.
  - Guardrails: write operations are rejected.
- `ask_reference_model`
  - Purpose: query local reference LLM through Ollama.
  - Input: `prompt`, optional `system_prompt`, optional `temperature`.
  - Output: model response text and completion metadata.
  - Default model: `gpt-oss:20b` (override with `REFERENCE_LLM_MODEL`).

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
