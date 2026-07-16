# Architecture

How the client-wrapper models are structured and how they manage connection
lifecycles. For formatting rules see [code-style.md](code-style.md).

## The model pattern

Each module defines a single pydantic `BaseModel` subclass that plays two roles
at once: a **validated settings object** and a **connection factory**.

1. **Settings** — connection parameters are declared as
   `Annotated[<type>, Field(...)]` fields. `model_config =
   ConfigDict(extra='forbid')` rejects unknown keyword arguments so typos fail
   loudly at construction time.
2. **Factory** — the underlying client/connection is exposed as a lazily
   evaluated, cached property, built from the validated fields.
3. **Lifecycle** — `close()` (and `aclose()` where async is supported) drop the
   cached client and release resources; context-manager dunders wrap them.

## Lazy caching

Sync resources use `@cached_property`, which stores the result in
`self.__dict__` under the property name on first access:

```python
@cached_property
def conn(self) -> Connection:
    return connect(...)
```

`cached_property` **cannot** be used for `async def` factories: awaiting the
property the second time would reuse an already-consumed coroutine. Async
factories therefore cache into `self.__dict__` manually:

```python
async def async_client(self) -> AsyncClient:
    if 'async_client' not in self.__dict__:
        self.__dict__['async_client'] = await get_async_client(...)
    return self.__dict__['async_client']
```

This mirrors what `cached_property` stores, so cleanup can treat both the same
way. Note there is no locking, so two coroutines racing on the first access may
each open a connection; the library assumes single-flow usage.

## Cleanup

`close()`/`aclose()` pop the cached client out of `self.__dict__` and close it,
guarding against the never-accessed case:

```python
def close(self) -> None:
    conn = self.__dict__.pop('conn', None)
    if conn is not None:
        conn.close()
```

Popping (not just closing) means a subsequent access rebuilds a fresh client,
so a model instance is reusable after `close()`.

Context managers simply delegate:

- `__enter__` / `__aenter__` return `self`
- `__exit__` / `__aexit__` call `close()` / `aclose()`

## Per-module notes

- **clickhouse.py** — the only model with both sync (`client`) and async
  (`async_client`) factories, and correspondingly both sync and async context
  managers.
- **hive.py** — a `@model_validator(mode='after')` enforces that `password` is
  set when `auth` is `'LDAP'` or `'CUSTOM'`. Exposes a `cursor()`
  contextmanager that closes the cursor in a `finally`.
- **trino.py** — caches a `BasicAuthentication` (`auth`) alongside the
  connection. Also exposes a `cursor()` contextmanager. The module is named
  `trino.py`, which can shadow the installed `trino` package when the project
  root is on `sys.path`; keep this in mind if imports fail.
- **slack.py** — defines `HttpxWebClient`, a `slack_sdk.WebClient` subclass that
  routes HTTP through `httpx` instead of urllib by overriding
  `_perform_urllib_http_request_internal` and `_upload_file`. `SlackModel`
  wraps it with connection- and rate-limit retry handlers. The overrides must
  return dicts with the exact keys `slack_sdk` expects (`status`, `headers`,
  `body`).
- **base.py** — `BaseClientModel(BaseModel, ABC)` is the shared contract for the
  httpx clients: common fields (`url_schema`, `verify`, `proxy`, `timeout`),
  abstract `_client` / `_async_client` properties, and the full
  close/aclose/context-manager surface. `GrafanaClientModel`,
  `PrometheusClientModel`, and `BaseGoKrOpenDataClientModel` inherit it; the
  four DB/service models above do not.
- **utility/** — the pieces the httpx clients share. `models.py` holds the two
  pydantic bases every DTO descends from: `RequestModel` (`extra='forbid'`) and
  `ResponseModel` (`extra='allow'`, so a server adding a field does not break
  parsing); both set `populate_by_name=True` so models can be constructed with
  snake_case names and dumped with `by_alias=True` to wire names. `helpers.py`
  holds `create_base_url`, the tenacity `before_sleep` logger, and the two retry
  predicates — `should_retry_idempotent` (5xx/429 **and** timeout/transport
  errors) versus `should_retry_non_idempotent` (5xx/429 only, since a request
  that may have been applied must not be replayed on a transport error).

## Composed clients

`gokr_opendata/` is the one client that fans out to sub-clients, because the
portal is many agencies' APIs behind one host and one `service_key`.

`BaseGoKrOpenDataClientModel` owns the httpx clients, baking the base URL and
the `service_key` query parameter into them. `GoKrOpenDataModel` then exposes
one lazily created sub-client per agency — currently `kma_client` — handing it
the already-configured httpx clients:

```python
@cached_property
def kma_client(self) -> KMAClientModel:
    return KMAClientModel(client=self._client, async_client=self._async_client)
```

The sub-client (`KMAClientModel`) is a plain class, not a pydantic model: it
holds no settings of its own, only endpoints and request methods. It therefore
has no lifecycle — closing belongs to the owner. `GoKrOpenDataModel.close()`
must drop the cached sub-clients before delegating to `super().close()`, since
they hold the very httpx client being closed and `BaseClientModel.close()` only
evicts it from the owning model.

Add a new agency by writing `<agency>/main.py` + `models/` under
`gokr_opendata/`, then adding a `@cached_property` for it on `GoKrOpenDataModel`
and popping it in `close()` / `aclose()`.

Note the portal's error convention: it answers `200 OK` and reports failure in
the body's `resultCode` (`'00'` success, `'03'` NODATA, `'99'` e.g. a `tm_fc`
outside the 24h retention window). The KMA methods do not check it — they
validate the body and return, so a failed `resultCode` surfaces only as
`response.body is None`, the same shape NODATA produces. Callers needing the
distinction read `response.header.result_code`. The library defines no
exception for this and raises nothing on a failed `resultCode`.

`service_key` must be stored **decoded**: httpx percent-encodes query params, so
an already-encoded key gets double-encoded and rejected.

## Credential-based clients

`ms/` and `google/` wrap vendor SDKs that create and own their own transport, so
they inherit neither `BaseClientModel` nor its close/context-manager surface.
The lazy-cached-property pattern still holds; what varies is that the cached
thing is a **credential** feeding the SDK's client.

- **ms/** — `MSBaseClientModel(BaseModel, ABC)` holds the fields common to every
  Microsoft Graph auth flow (`tenant_id`, `client_id`, `verify`, `proxy`,
  `scopes`), declares `credential` abstract, and builds the cached
  `GraphServiceClient` from whatever the subclass returns, routing it through an
  httpx `AsyncClient` so `verify`/`proxy` are honoured. One subclass per flow:
  `MSAppClientModel` (client secret, app-only), `MSDelegateClientModel`
  (username/password, delegated), `MSDelegateRefreshTokenClientModel` (a stored
  refresh token). Add a flow by subclassing and implementing `credential` only.
- **ms/utility.py** — the refresh-token flow has no `azure.identity` equivalent,
  so it is implemented here. `create_refresh_token` runs the device-code flow
  interactively (prints the sign-in message, polls the token endpoint, forcing
  `offline_access` into the scopes) and returns a refresh token to store.
  `_RefreshTokenCredential` is a hand-rolled credential satisfying the
  `azure.core` protocol: it exchanges the refresh token for an access token,
  caches it until 300s before expiry under both a `threading.Lock` and an
  `asyncio.Lock` (double-checked), and rotates `self._refresh_token` when the
  server returns a new one — that rotation is why the model caches the
  credential object rather than rebuilding it.
- **google/** — Google's libraries refresh the access token in-place, so
  `GoogleCredentialsModel` passes `SyncingCredentials` (a `Credentials`
  subclass whose `refresh` fires an `on_refresh` callback) and writes the new
  token back onto its own fields. That keeps the model a faithful, re-serializable
  record of the current credentials. `GoogleModel` builds a discovery client
  from `service_name`/`version`; `GdriveModel` pins those to `drive`/`v3` and
  adds `close()` + context-manager support; `GspreadModel` skips discovery and
  authorizes a `gspread` client directly. `utility.py`'s `create_credentials`
  bootstraps a `GoogleCredentialsModel` via an interactive OAuth flow.
