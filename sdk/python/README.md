# Remembr Python SDK

Python client for the Remembr API.

## Install

```bash
pip install remembr
```

## Quickstart

```python
from remembr import RemembrClient

client = RemembrClient(api_key="your-api-key")
response = client.request("GET", "/health")
print(response)
```


## Running tests

```bash
cd sdk/python
PYTHONPATH=. pytest
```

To run live integration tests, set `REMEMBR_TEST_API_KEY` (and optionally `REMEMBR_TEST_BASE_URL`) before running pytest.
