# lib

A small library of database and service **client wrappers**, all under
`src/clients/`. Each module exposes a pydantic model that validates connection
settings up front, lazily builds and caches the underlying client, and cleans it
up through a context manager.

The point is that connection settings are *data*: you validate them once, pass
the model around, and never hand-roll a connection or forget to close one.

## Contents

Database and service clients:

| Import                     | Model             | Wraps                               |
| -------------------------- | ----------------- | ----------------------------------- |
| `clients.clickhouse`       | `ClickHouseModel` | `clickhouse_connect` (sync + async) |
| `clients.hive`             | `HiveModel`       | `pyhive` Hive DB-API                |
| `clients.trino`            | `TrinoModel`      | `trino` DB-API                      |
| `clients.slack`            | `SlackModel`      | `slack_sdk` Web API over `httpx`    |

HTTP API clients:

| Import                    | Model / entry point                | Wraps                                       |
| ------------------------- | ---------------------------------- | ------------------------------------------- |
| `clients.grafana`         | `GrafanaClientModel`               | Grafana datasource query API                |
| `clients.prometheus`      | `PrometheusClientModel`            | Prometheus instant / range query API        |
| `clients.gokr_opendata`   | `GoKrOpenDataModel` → `kma_client` | 공공데이터포털 (data.go.kr), 기상청 중기예보 |

Credential-based clients (wrap a vendor SDK rather than `httpx`):

| Import           | Model / entry point                                                          | Wraps                    |
| ---------------- | ---------------------------------------------------------------------------- | ------------------------ |
| `clients.ms`          | `MSAppClientModel`, `MSDelegateClientModel`, `MSDelegateRefreshTokenClientModel` | Microsoft Graph          |
| `clients.google.main` | `GdriveModel`, `GspreadModel`, `GoogleModel`                                 | Google Drive  /  Sheets  |

## Usage

`src/` is the import root, so `clients` is the top-level package.

### Databases

Every DB model validates its settings on construction, opens the connection on
first use, and closes it when the `with` block exits.

```python
from clients.trino import TrinoModel

with TrinoModel(
    host='trino.acme.com',
    port=8080,
    username='user',
    password='secret',
    catalog='hive',
) as model:
    with model.cursor() as cur:
        cur.execute('SELECT 1')
        rows = cur.fetchall()
```

`HiveModel` has the same shape. `ClickHouseModel` exposes a client rather than a
cursor, and additionally supports async:

```python
from clients.clickhouse import ClickHouseModel

with ClickHouseModel(
    host='localhost', port=8123, username='default', password='',
) as model:
    result = model.client.query('SELECT 1')

async with ClickHouseModel(
    host='localhost', port=8123, username='default', password='',
) as model:
    client = await model.async_client()
    result = await client.query('SELECT 1')
```

Note `async_client` is an awaited method call, not a property — the underlying
client can only be built with `await`.

### HTTP APIs

Requests and responses are pydantic models, and calls retry automatically on
5xx/429 and timeout/transport errors (3 attempts, 1s apart).

```python
from datetime import datetime, timedelta

from clients.prometheus import (
    PrometheusClientModel,
    PrometheusQueryRangeV1RequestParameterModel,
)

with PrometheusClientModel(
    host='prometheus.acme.com',
    user_agent='my-app/1.0',
) as client:
    response = client.run_request_query_range_v1(
        PrometheusQueryRangeV1RequestParameterModel(
            query='up',
            start_date=datetime.now() - timedelta(hours=1),
            end_date=datetime.now(),
            step='1m',
        )
    )
```

Every call has an `arun_*` async twin with an identical signature:

```python
async with PrometheusClientModel(
    host='prometheus.acme.com', user_agent='my-app/1.0',
) as client:
    response = await client.arun_request_query_range_v1(parameter)
```

### 공공데이터포털 (data.go.kr)

`GoKrOpenDataModel` owns the shared HTTP clients and hands them to one client
per service, so the service key is supplied once:

```python
from datetime import datetime

from clients.gokr_opendata import GoKrOpenDataModel
from clients.gokr_opendata.kma import KMAGetMidLandFcstRequestParameterModel

with GoKrOpenDataModel(service_key='...') as model:
    response = model.kma_client.run_request_get_mid_land_fcst(
        KMAGetMidLandFcstRequestParameterModel(
            reg_id='서울, 인천, 경기도',
            tm_fc=datetime(2026, 7, 16, 6, 0),
        )
    )
```

`reg_id` (and `stn_id`) accept either the raw code or the 한글 구역명 — a name
is resolved to its code on validation, so `'서울, 인천, 경기도'` and
`'11B00000'` are equivalent. `tm_fc` is a `datetime` and is formatted to the
`YYYYMMDDHHMM` the API expects.

Pass `service_key` **decoded**. The client percent-encodes it, so an
already-encoded key is double-encoded and rejected.

### Slack

```python
from clients.slack import SlackModel

model = SlackModel(token='xoxb-...')
model.client.chat_postMessage(channel='#general', text='hello')
```

The client is a `slack_sdk` `WebClient` that sends over `httpx` instead of
urllib, with connection and rate-limit retries pre-configured, so proxy and TLS
settings are honoured.

### Google and Microsoft

These wrap vendor SDKs that own their transport, so what they model is the
**credential**. Google tokens refresh in place and are written back onto the
model, so they can be persisted after use:

```python
from clients.google.main import GspreadModel

model = GspreadModel(
    token='...',
    refresh_token='...',
    token_uri='https://oauth2.googleapis.com/token',
    client_id='...',
    client_secret='...',
)
records = model.client.open('My Sheet').sheet1.get_all_records()
```

To obtain credentials interactively the first time, use
`clients.google.utility.create_credentials()`. The Microsoft equivalent is
`clients.ms.create_refresh_token()`, which runs the device code flow; pick the
`MS*ClientModel` matching your auth flow (app, delegate, or refresh token).

## Conventions

Secrets (`password`, `token`, `client_secret`, `service_key`, ...) are declared
`Field(repr=False)`, so they do not leak into logs when a model is printed. All
models set `extra='forbid'` — an unknown or misspelled setting is an error at
construction, not a silent no-op.

If you are extending the library, read
**[AGENTS.md](AGENTS.md)** first; it links the detailed references covering
[code style](references/code-style.md),
[architecture](references/architecture.md), and the
[API client conventions](references/api-client-conventions.md) that govern
endpoint naming and model layout.
