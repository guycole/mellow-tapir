# mellow-tapir

Mellow-Tapir is an experimental MCP server that helps radio hobbyists explore likely services, channels, and signal types across the radio spectrum from 108 MHz to 1 GHz; it is not a frequency-coordination or regulatory-authority tool.

## Allocation references

The [`dox/allocation`](dox/allocation) directory is a versioned archive of authoritative United States radio-frequency allocation and service references. The collection prioritizes spectrum at 30 MHz and above and is intended to support source-preserving extraction into a normalized database rather than replace the original publications.

The archive currently includes:

- **NTIA Redbook:** the complete *Manual of Regulations and Procedures for Federal Radio Frequency Management*, Chapter 4 on allocations and frequency plans, and NTIA's machine-readable allocation table and schema. These are the primary references for federal allocations, allotments, channel plans, and spectrum-management requirements.
- **NTIA allocation chart:** a visual overview of United States spectrum allocations, useful for orientation and coverage checks but not as a substitute for the underlying allocation tables.
- **FCC allocation references:** the FCC Online Table of Frequency Allocations and its Allocation History File, covering non-federal allocations, FCC rule-part mappings, footnotes, and allocation changes.
- **FCC Universal Licensing System documentation:** the ULS public-access-file guide and data dictionaries in PDF and spreadsheet form. These define fields used to interpret licensing records, including frequency and emission data.
- **Title 47 of the Code of Federal Regulations:** all five volumes of the 2025 annual edition in both PDF and XML. These preserve the governing service rules and provide machine-readable material for extracting frequencies, channel spacing, emission limits, and related requirements.

The [`manifest.json`](dox/allocation/manifest.json) file is the index to the archive. Each entry records the publishing agency, title and version, effective or publication date when available, original URL, retrieval date, local filename, media type, file size, SHA-256 checksum, and intended use.

Source files are preserved in their original formats. New revisions should be added under a new version directory and appended to the manifest; existing versions should not be overwritten. Derived records should retain links to their source artifact and, where possible, the relevant page, section, table, or rule citation so database results remain traceable to the authoritative material.

## SQLite classifier data pipeline

The MCP server uses a read-only SQLite file built from the editable catalog under [`src/tapir_schema`](src/tapir_schema).

Data sources:

- [`src/tapir_schema/seed.json`](src/tapir_schema/seed.json): authoritative editable band, emission, and channel catalog.
- [`src/tapir_schema/schema.sql`](src/tapir_schema/schema.sql): reference SQL schema used for provenance and alignment with the source data model.

Build location:

- [`src/tapir_mcp_server/data/tapir.sqlite`](src/tapir_mcp_server/data/tapir.sqlite)

Build command:

```bash
cd /Users/gsc/github/mellow-tapir/src/tapir_mcp_server
./venv/bin/python -m mcp_server.build_db \
	--db-path data/tapir.sqlite \
	--seed-path ../tapir_schema/seed.json \
	--schema-path ../tapir_schema/schema.sql
```

When source catalog data changes, rebuild the SQLite file with the command above and restart the MCP server.
