# API Client Conventions

Conventions for HTTP API client modules that subclass `BaseClientModel`
(e.g. `grafana/`, `prometheus/`, `gokr_opendata/`). For formatting rules see
[code-style.md](code-style.md); for the connection lifecycle and the
composed-client (`gokr_opendata/` → `kma/`) structure see
[architecture.md](architecture.md).

## Endpoint-derived naming

Every callable endpoint has an **action id** built from its path: take the
segments after `/api/` in order, join them with `_`, and move a version
segment (`vN`) to the end. For an API not rooted at `/api/`, use the
snake_case form of the last path segment.

| Endpoint                                    | Action id           |
| ------------------------------------------- | ------------------- |
| `/api/v1/query`                             | `query_v1`          |
| `/api/v1/query_range`                       | `query_range_v1`    |
| `/api/ds/query`                             | `ds_query`          |
| `/1360000/MidFcstInfoService/getMidLandFcst`| `get_mid_land_fcst` |

All symbols for that endpoint are named from the action id. `{Action}` is the
PascalCase form (`query_v1` → `QueryV1`, `ds_query` → `DsQuery`). The model
prefix is the service name (`Prometheus`, `Grafana`, ...):

| Symbol             | Pattern                                   | Example (`ds_query`, Grafana)             |
| ------------------ | ----------------------------------------- | ----------------------------------------- |
| Endpoint ClassVar  | `{action}_endpoint`                       | `ds_query_endpoint`                       |
| Sync method        | `run_request_{action}`                    | `run_request_ds_query`                    |
| Async method       | `arun_request_{action}`                   | `arun_request_ds_query`                   |
| Request params     | `<Service>{Action}RequestParameterModel`  | `GrafanaDsQueryRequestParameterModel`     |
| Request payload    | `<Service>{Action}RequestPayloadModel`    | `GrafanaDsQueryRequestPayloadModel`       |
| Response model     | `<Service>{Action}ResponseModel`          | `GrafanaDsQueryResponseModel`             |

Request payload models are only needed for endpoints with a request body
(e.g. Grafana's `POST /api/ds/query`); GET-only endpoints like Prometheus's
queries use just a parameter model.

The endpoint ClassVar drops a leading HTTP-verb word from the action id, since
the constant names a path rather than a call: `get_mid_land_fcst` gives
`mid_land_fcst_endpoint` but still `run_request_get_mid_land_fcst` and
`KMAGetMidLandFcstRequestParameterModel`.

## Module layout

Each client package is laid out as:

```
<service>/
├── __init__.py     # re-export the public models + client
├── main.py         # <Service>ClientModel(BaseClientModel) + request methods
└── models/
    ├── __init__.py
    ├── request.py  # top-level request parameter/payload models only
    ├── response.py # top-level response models only
    └── dto.py      # everything else (see below)
```

- **request.py / response.py** hold only the **top-level** per-endpoint models —
  the ones a request method takes as a parameter/payload or validates its
  result into (`<Service>{Action}RequestParameterModel`,
  `<Service>{Action}RequestPayloadModel` / `<Service>{Action}ResponseModel`).
- **dto.py** holds everything else: shared headers, generic containers
  (`DataModel[T]`), nested/building-block models, and common bases
  (`ResultModel`). If a model is not the outermost model for an endpoint, it
  belongs in `dto.py`.

A client that fans out to sub-clients nests the same layout one level down, and
adds a `base.py` for the settings/httpx client the sub-clients share:

```
gokr_opendata/
├── __init__.py
├── base.py         # BaseGoKrOpenDataClientModel(BaseClientModel) + shared error
├── main.py         # GoKrOpenDataModel: one cached_property per sub-client
└── kma/
    ├── __init__.py
    ├── main.py     # KMAClientModel: plain class taking (client, async_client)
    └── models/     # request.py / response.py / dto.py, as above
```

## Retry

Wrap every request method in tenacity `@retry` with the shared predicates from
`clients.utility`:

```python
@retry(
    retry=retry_if_exception(should_retry_idempotent),
    stop=stop_after_attempt(3),
    wait=wait_fixed(1),
    reraise=True,
    before_sleep=log_retry_before_sleep,
)
```

Use `should_retry_idempotent` for reads (retries 5xx/429 plus timeout and
transport errors) and `should_retry_non_idempotent` for calls that mutate state
(5xx/429 only — a transport error may mean the request landed). `reraise=True`
surfaces the underlying error rather than tenacity's `RetryError`. State the
retry behaviour in the method docstring, per
[code-style.md](code-style.md#method-docstrings).

## Application-level errors

Some APIs report failure in the body of a `200 OK` — 공공데이터포털 carries it in
`resultCode`. Request methods do **not** inspect it: they call
`raise_for_status()` and then validate the body into the response model, so a
non-success `resultCode` returns normally rather than raising.

This is a deliberate trade-off, and callers must know it. Because `body` is
`Optional` (NODATA legitimately sends a header-only response), a failed
`resultCode` validates cleanly and is indistinguishable from an empty result —
both give `response.body is None`. A caller that needs to tell them apart reads
`response.header.result_code` itself.

The library defines no exception for this and raises nothing on a failed
`resultCode`; request-method docstrings therefore carry no `Raises:` section.

## Default values

Where a field has a default, its placement depends on the model's base:

- **`RequestModel` subclasses** — put the default **outside** `Field`, so it
  shows up in the constructor's type hint for callers:

  ```python
  timeout: Annotated[Optional[str], Field()] = None
  ```

- **`ResponseModel` subclasses** — put the default **inside** `Field`:

  ```python
  nullable: Annotated[Optional[bool], Field(default=None)]
  ```

The reason is caller ergonomics: request models are constructed by users, so the
default belongs in the signature; response models are parsed from server
payloads and are not hand-constructed.

## Writing DTOs

- DTOs inherit `ResponseModel` (`extra='allow'`, tolerant of unknown fields
  from the server), except request-side helpers like headers which inherit
  `RequestModel` (`extra='forbid'`).
- Factor shared fields into a common base and subclass it (e.g. `ResultModel`
  holds `metric`; `QueryResultModel` / `QueryRangeResultModel` add `value` /
  `values`).
- Use a generic container for shapes that differ only by element type:

  ```python
  T = TypeVar('T', bound=ResponseModel)

  class DataModel(ResponseModel, Generic[T]):
      result_type: Annotated[str, Field(alias='resultType')]
      result: Annotated[List[T], Field()]
  ```

  then specialize per endpoint: `DataModel[QueryResultModel]`.
- Map wire names with `Field(alias=...)` and serialize with
  `@field_serializer` (see the datetime → unix-seconds serializers in
  `prometheus/models/request.py`).
