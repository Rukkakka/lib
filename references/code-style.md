# Code Style

Conventions for this library. Keep every module consistent with these rules.

## Imports

Order import groups as follows, separated by a blank line, with `typing`
always last:

1. **Standard library / built-ins** (e.g. `contextlib`, `functools`, `types`)
2. **Third-party / external** (e.g. `pydantic`, `httpx`, driver packages)
3. **`typing`** (`Annotated`, `Optional`, `Type`, ...)

```python
from functools import cached_property

from types import TracebackType

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from clickhouse_connect import get_client

from typing import (
    Annotated,
    Optional,
    Type,
)
```

Notes:

- Group multiple names from one package with parentheses, one name per line.
- Keep `typing` as its own final group even though it is standard library.

## Quotes

Use single quotes `'...'` for all string literals.

```python
http_scheme: Literal['http', 'https'] = 'https'
```

Use double quotes only when the string itself contains a single quote, to
avoid escaping:

```python
raise ValueError(f"'password' is required when auth= '{self.auth}'")
```

## Docstrings

Google-style docstrings on every public model class, with these sections in
order (omit a section only when it does not apply):

- **Summary** — one line, then an optional short paragraph.
- **Args** — constructor/model fields, with defaults noted.
- **Attributes** — cached/derived attributes (e.g. `conn`, `client`).
- **Raises** — exceptions the caller is expected to handle, with what triggers
  them.
- **Example** — a runnable `>>>` snippet showing typical usage.

Do **not** add a boilerplate `See` section pointing at `AGENTS.md` /
`code-style.md` to every model — that reference is implied. Add a `See` section
only when a specific model genuinely needs to point the reader at a particular
reference doc.

```python
class ExampleModel(BaseModel):
    """One-line summary of the model.

    Optional short paragraph with extra context.

    Args:
        host: Server hostname.
        port: Server port.

    Attributes:
        conn: Cached connection, created on first access.

    Example:
        >>> with ExampleModel(host='localhost', port=8080) as model:
        ...     model.conn.query('SELECT 1')
    """
```

### Method docstrings

Public methods get a concise docstring covering:

- **Summary** — one line stating what the call does (e.g. HTTP verb + endpoint).
- **Retry behaviour** — when the call is wrapped in `@retry`, state the retry
  count, wait, and which errors trigger it (e.g. "up to 3 attempts, 1s wait, on
  5xx/429 or timeout/transport errors").
- **Args** — each parameter and the key fields it carries.
- **Returns** — the return type and, briefly, what it holds.
- **Raises** — application-level errors the method raises itself; do not list
  every transport error.
- **See** — the official API doc when the method wraps a documented external
  endpoint.

Keep it tight; do not restate the full field list already documented on the
model class. For an `async` variant with an identical signature, summarise and
point at its sync counterpart instead of repeating Args/Returns/retry.

```python
def run_request_query_v1(self, parameter):
    """Run an instant query via `GET /api/v1/query`.

    Retries up to 3 attempts (1s fixed wait) on HTTP 5xx/429 responses and
    httpx timeout/transport errors; any other error, and the final failed
    attempt, is raised.

    Args:
        parameter: Instant-query parameters — `query` (PromQL, required)
            plus optional `time` and `timeout`.

    Returns:
        PrometheusQueryV1ResponseModel: Parsed response (`status` + `data`).

    See:
        https://prometheus.io/docs/prometheus/latest/querying/api/#instant-queries
    """
```

## Model patterns

- Configure models with `model_config = ConfigDict(extra='forbid')`.
- Declare fields as `Annotated[<type>, Field(...)]`.
- Lazily create expensive resources with `@cached_property`; for async
  factories, cache into `self.__dict__` manually (see `clickhouse.py`).
- Provide `close()` / `aclose()` plus `__enter__`/`__exit__` and, where async
  is supported, `__aenter__`/`__aexit__`.
