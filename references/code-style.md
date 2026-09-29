# Code Style

This document defines style rules that apply to the whole repository:
`src/clients/**` and markdown documentation.

Design rules specific to the httpx API client modules - endpoint-derived naming,
model layout, retry policy - live in
[api-client-conventions.md](api-client-conventions.md).

## 1. String Literals

- Use `'` for string literals unless there is a specific reason not to, for
  example a literal that itself contains a single quote.
- Docstrings keep `"""`.

```python
http_scheme: Literal['http', 'https'] = 'https'
raise ValueError(f"'password' is required when auth='{self.auth}'")
```

## 2. Imports

- Import order, one blank line between groups:
  1. Python standard library (including `collections.abc`, excluding `typing`)
  2. External libraries
  3. Project libraries (`clients.*`)
  4. `typing`
- In `from x import ...`, if there are 2 or more imported targets, use
  multi-line parentheses, one name per line.
- For project imports, keep order from lower dependency depth modules to higher
  depth modules.
  - Example: `clients.utility` -> `clients.base` -> `clients.<service>.models.*`
- Use absolute imports (`from clients...`) by default.

```python
from functools import cached_property
from types import TracebackType

from httpx import Client
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from clients.utility import RequestModel
from clients.base import BaseClientModel

from typing import (
    Annotated,
    Literal,
)
```

## 3. Pydantic Declarations

The baseline is **the approach recommended by the official pydantic v2
documentation**.

### 3.1 Constraints and defaults go in different places

- Put constraints (`ge`, `le`, `min_length`, `pattern`, `description`, and so
  on) inside `Annotated[T, Field(...)]`.
- **Do not put `default`, `default_factory`, or `alias` in the `Field()` inside
  `Annotated`.** Per the pydantic documentation, static type checkers do not
  read those three arguments from a `Field()` nested in `Annotated`, so they
  belong in a `Field()` at the assignment position. This applies to request and
  response models alike.
- For a plain default with no constraint and no alias, `= value` is
  functionally identical to `Field(default=...)` and shorter; the pydantic
  documentation uses this form in its own examples.
- Do not write an empty `Field()` just to use `Annotated`: `port: int` rather
  than `port: Annotated[int, Field()]`.

```python
# No constraint, no alias - a plain assignment is enough
age: int = 20

# Constraint only - Field() inside Annotated, default via `=`
retries: Annotated[int, Field(ge=0)] = 0

# Constraint plus alias/default - constraint in Annotated, default/alias outside
store_id: Annotated[int, Field(ge=0)] = Field(default=5, alias='storeId')

# Alias only, no constraint - Field() directly, no Annotated
store_id: int = Field(alias='storeId')
```

- Use `Field(alias=...)` only when external API keys differ from the Python
  field name.
- Do not use `Field(...)` (ellipsis) to emphasise that a field is required. The
  pydantic documentation discourages it because it reads as though the field
  had a default. An annotation alone is already required: `name: str`.
- Do not declare a default twice, as in `Field(default=None)` together with
  `= None`.
- `X | None` does not make a field optional. A field is optional **only when it
  has a default**: `comment: str | None` is required (it accepts `None`, but it
  must be passed), while `comment: str | None = None` is optional.

### 3.2 `default_factory` and mutable defaults

- `default_factory` takes a callable. It may optionally accept one argument,
  a dict of the already-validated preceding fields:
  `Field(default_factory=lambda data: data['email'])`
- Mutable defaults (`= []`, `= {}`) are safe. Unlike dataclasses, pydantic
  deep-copies the default for every instance, so it is never shared.
- `default_factory` is not required for those; use it when the default must be
  computed fresh each time or is expensive to build.

### 3.3 Other rules

- Use multi-line style for field declarations by default for readability, while
  allowing one-line declarations for request/response models.
- Whether a field is actually required or optional (including how tolerant a
  response model should be of missing fields) depends on the API spec; follow
  [api-client-conventions.md](api-client-conventions.md) for the
  client-module-specific criteria.
- Hide secrets from `repr()` with `Field(repr=False)`, so tokens, passwords, and
  keys stay out of logs and exception tracebacks.

## 4. Type Hints

- Annotate all function parameters and return types.
- Use builtin generics: `list[...]`, `dict[...]`, `tuple[...]`, `set[...]`,
  `type[...]`. Not `typing.List` / `Dict` / `Tuple` / `Set` / `Type`
  (deprecated, PEP 585).
- Use `X | None` and `X | Y` union syntax. Not `Optional[X]` / `Union[X, Y]`
  (PEP 604). The runtime baseline is Python 3.11 (see `requirements.txt`), so
  this syntax works as is; `from __future__ import annotations` is not needed,
  so do not add it.
- Import from `typing` only names without a builtin or `collections.abc`
  equivalent: `Any`, `Literal`, `Annotated`, `ClassVar`, `Protocol`,
  `TYPE_CHECKING`, `TypeVar`, `cast`, and so on.
- Import abstract container types (`Callable`, `Iterator`, `Iterable`,
  `Generator`, `Sequence`, `Mapping`, and so on) from `collections.abc`, not
  `typing`. In the import grouping they belong to the standard library group in
  [section 2](#2-imports).
- A forward reference that is part of a union is quoted as a whole:
  `'DriveResource | None'`, not `'DriveResource' | None`, which raises
  `TypeError` when the class body is evaluated.

```python
# Good
def f(name: str, count: int) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    matched_id: int | None = None

# Avoid
def f(name: str, count: int) -> Dict[str, Any]:   # typing alias
    items: List[Dict[str, Any]] = []
    matched_id: Optional[int] = None              # Optional
```

## 5. Docstrings

Google-style docstrings on every public model class, with these sections in
order (omit a section only when it does not apply):

- **Summary** - one line, then an optional short paragraph.
- **Args** - constructor/model fields. A field with a default says
  `Defaults to ...` (`Defaults to None` for a `None` default); a required field
  gets no default note.
- **Attributes** - cached/derived attributes (e.g. `conn`, `client`).
- **Raises** - exceptions the caller is expected to handle, with what triggers
  them.
- **Example** - a runnable `>>>` snippet showing typical usage.

Do **not** add a boilerplate `See` section pointing at `AGENTS.md` /
`code-style.md` to every model - that reference is implied. Add a `See` section
only when a specific model genuinely needs to point the reader at a particular
reference doc.

```python
class ExampleModel(BaseModel):
    """One-line summary of the model.

    Optional short paragraph with extra context.

    Args:
        host: Server hostname.
        port: Server port. Defaults to 8080.

    Attributes:
        conn: Cached connection, created on first access.

    Example:
        >>> with ExampleModel(host='localhost') as model:
        ...     model.conn.query('SELECT 1')
    """
```

### 5.1 Method docstrings

Public methods get a concise docstring covering:

- **Summary** - one line stating what the call does (e.g. HTTP verb + endpoint).
- **Retry behaviour** - when the call is wrapped in `@retry`, state the retry
  count, wait, and which errors trigger it (e.g. "up to 3 attempts, 1s wait, on
  5xx/429 or timeout/transport errors").
- **Args** - each parameter and the key fields it carries.
- **Returns** - the return type and, briefly, what it holds.
- **Raises** - application-level errors the method raises itself; do not list
  every transport error.
- **See** - the official API doc when the method wraps a documented external
  endpoint.

Keep it tight; do not restate the full field list already documented on the
model class. For an `async` variant with an identical signature, summarise and
point at its sync counterpart instead of repeating Args/Returns/retry.

```python
def run_request_query_v1(self, parameter):
    """Run an instant query via `GET /api/v1/query`.

    Retries up to 3 attempts on HTTP 5xx/429 responses and httpx
    timeout/transport errors, waiting 1s between attempts or, on a 429,
    the server's `Retry-After` (capped at 60s); any other error, and the
    final failed attempt, is raised.

    Args:
        parameter: Instant-query parameters - `query` (PromQL, required)
            plus optional `time` and `timeout`.

    Returns:
        PrometheusQueryV1ResponseModel: Parsed response (`status` + `data`).

    See:
        https://prometheus.io/docs/prometheus/latest/querying/api/#instant-queries
    """
```

## 6. Model Patterns

- Configure models with `model_config = ConfigDict(extra='forbid')` by default;
  relax it only where a model has a reason to accept unknown keys.
- Declare fields per [section 3](#3-pydantic-declarations).
- Lazily create expensive resources with `@cached_property`; for async
  factories, cache into `self.__dict__` manually (see `clickhouse.py`).
- Provide `close()` / `aclose()` plus `__enter__`/`__exit__` and, where async
  is supported, `__aenter__`/`__aexit__`.
