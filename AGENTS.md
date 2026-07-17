# AGENTS.md

A small library of database/service **client wrappers**, all under
`src/clients/`. Each module exposes a pydantic model that validates connection
settings, lazily builds and caches the underlying client/connection, and cleans
it up through context managers.

## Modules

Flat DB/service modules:

| Module          | Model             | Wraps                               |
| --------------- | ----------------- | ----------------------------------- |
| `clickhouse.py` | `ClickHouseModel` | `clickhouse_connect` (sync + async) |
| `hive.py`       | `HiveModel`       | `pyhive` Hive DB-API                |
| `trino.py`      | `TrinoModel`      | `trino` DB-API                      |
| `slack.py`      | `SlackModel`      | `slack_sdk` Web API over `httpx`    |

Packages:

| Package          | Model / entry point                          | Wraps                                                |
| ---------------- | -------------------------------------------- | ---------------------------------------------------- |
| `grafana/`       | `GrafanaClientModel`                         | Grafana HTTP API (`/api/ds/query`)                   |
| `prometheus/`    | `PrometheusClientModel`                      | Prometheus HTTP query API                            |
| `gokr_opendata/` | `GoKrOpenDataModel` → `kma_client`           | 공공데이터포털 (data.go.kr), 기상청 중기예보          |
| `ms/`            | `MSAppClientModel`, `MSDelegate*ClientModel` | Microsoft Graph via `msgraph` + `azure.identity`     |
| `google/`        | `GdriveModel`, `GspreadModel`, `GoogleModel` | Google Drive / Sheets (`googleapiclient`, `gspread`) |

Shared infrastructure:

| Module     | Contents                                                                    |
| ---------- | --------------------------------------------------------------------------- |
| `base.py`  | `BaseClientModel` — httpx client base (see note below)                       |
| `utility/` | `RequestModel` / `ResponseModel` bases, retry predicates, `create_base_url`  |

## Shared pattern

Every model follows the same shape:

- `model_config = ConfigDict(extra='forbid')`
- Fields declared as `Annotated[<type>, Field(...)]`
- Secrets (`password`, `token`, `client_secret`, `service_key`, ...) carry
  `Field(repr=False)`
- The client/connection is built lazily and cached (`@cached_property`, or
  manual `self.__dict__` caching for async factories)
- Cleanup via `close()` / `aclose()`, exposed through `with` / `async with`

## HTTP API clients

The httpx-based clients (`grafana/`, `prometheus/`, `gokr_opendata/`) subclass
`BaseClientModel` and add tenacity retry. They add two rules on top of the
shared pattern:

- **Endpoint-derived naming.** An endpoint's action id comes from its path and
  names every related symbol. For `/api/`-rooted APIs it is the segments after
  `/api/` joined by `_`, with a version segment (`vN`) moved to the end
  (`/api/v1/query` → `query_v1`, `/api/ds/query` → `ds_query`); elsewhere it is
  the snake_case last segment (`.../getMidLandFcst` → `get_mid_land_fcst`).
  From it come `query_v1_endpoint`, `run_request_query_v1`,
  `PrometheusQueryV1RequestParameterModel`, `PrometheusQueryV1ResponseModel`.
- **Model layout.** `request.py` / `response.py` hold only the top-level
  per-endpoint models; shared headers, generic containers (`DataModel[T]`),
  and common bases live in `dto.py`. Request-model defaults go **outside**
  `Field` (`= None`); response-model defaults go **inside** (`Field(default=None)`).

Full details in **[references/api-client-conventions.md](references/api-client-conventions.md)**.

## Credential-based clients

`ms/` and `google/` do not wrap httpx directly — they wrap vendor SDKs that own
their own transport, so they do **not** inherit `BaseClientModel`. What they
model is the **credential**: `ms/` declares an abstract `credential` property
with one subclass per auth flow (app / delegate / refresh-token), and `google/`
uses a credentials model that persists tokens back to itself on every refresh.
See [references/architecture.md](references/architecture.md).

## Conventions

Read **[references/code-style.md](references/code-style.md)** before editing —
it defines import ordering, quoting, and docstring format. For how the modules
fit together, see **[references/architecture.md](references/architecture.md)**.

## Workflow

Read **[references/deploy.md](references/deploy.md)** before committing. In
short: **open an issue before every commit**, using a template from
`.github/ISSUE_TEMPLATE/` — never a blank issue. Then **cut a branch off `main`
and commit there — never commit to `main` directly**, no matter how small the
change; name it `<type>/<slug>` and reference the issue from the commit
(`Refs #12`). A branch can carry several commits and close several issues.
Everything reaches `main` through a PR, opened with
`.github/PULL_REQUEST_TEMPLATE.md` filled in and closing its issues from the PR
body. One concern per commit; stage paths deliberately, not `git add -A`.

## Note

`base.py`'s `BaseClientModel` is the shared base for the httpx API clients
(`GrafanaClientModel`, `PrometheusClientModel`, `BaseGoKrOpenDataClientModel`).
The four DB/service models (`ClickHouseModel`, `HiveModel`, `TrinoModel`,
`SlackModel`) do **not** inherit it — they re-implement the lifecycle
independently. Treat it as the intended shared base and reconcile with it when
refactoring those models. The credential-based clients (`ms/`, `google/`) sit
outside it by design.
