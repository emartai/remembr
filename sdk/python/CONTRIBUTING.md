# Contributing to the Remembr Python SDK

## Prerequisites

- Python 3.11+
- `pip`

## Setup

```bash
cd sdk/python
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Running checks

```bash
ruff check remembr
python -m compileall remembr
pytest
```

## Notes

- The SDK is async-first (`RemembrClient.arequest`) with a sync wrapper (`RemembrClient.request`).
- Configure auth with `api_key=...` or `REMEMBR_API_KEY`.
