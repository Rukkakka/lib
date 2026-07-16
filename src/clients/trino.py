from contextlib import contextmanager

from functools import cached_property

from pydantic import (
    BaseModel,
    ConfigDict,
    Field
)

from trino.auth import BasicAuthentication
from trino.dbapi import (
    connect,
    Connection,
    Cursor
)

from types import TracebackType

from typing import (
    Annotated,
    Optional,
    Iterator,
    Literal,
    Tuple,
    Type
)


class TrinoModel(BaseModel):
    """Pydantic model wrapping a Trino DB-API connection.

    Lazily creates and caches a `Connection` on first access via `conn`,
    exposes a `cursor()` context manager for per-query cursors, and supports
    both `with` and explicit `close()` for cleanup.

    Args:
        database: Default schema to connect to. Defaults to 'default'.
        http_scheme: Transport scheme, 'http' or 'https'. Defaults to 'https'.
        host: Trino coordinator hostname.
        port: Trino coordinator port.
        catalog: Catalog to query against. Defaults to 'hive'.
        username: Username used for basic authentication.
        password: Password used for basic authentication.
        request_timeout: (connect, read) timeout in seconds. Defaults to (60, 300).

    Attributes:
        auth: Cached `BasicAuthentication` built from username/password.
        conn: Cached `Connection`, created on first access.

    Example:
        >>> with TrinoModel(
        ...     host='localhost',
        ...     port=8080,
        ...     username='user',
        ...     password='secret',
        ... ) as model:
        ...     with model.cursor() as cur:
        ...         cur.execute('SELECT 1')
        ...         cur.fetchall()
    """

    model_config = ConfigDict(
        extra='forbid',
    )

    database: Annotated[
        str,
        Field()
    ] = 'default'

    http_scheme: Annotated[
        Literal['http', 'https'],
        Field()
    ] = 'https'

    host: Annotated[
        str,
        Field()
    ]

    port: Annotated[
        int,
        Field()
    ]

    catalog: Annotated[
        str,
        Field()
    ] = 'hive'

    username: Annotated[
        str,
        Field()
    ]

    password: Annotated[
        str,
        Field(repr=False)
    ]

    request_timeout: Annotated[
        Tuple[float, float],
        Field()
    ] = (60, 300)

    @cached_property
    def auth(self) -> BasicAuthentication:
        return BasicAuthentication(
            username=self.username,
            password=self.password
        )

    @cached_property
    def conn(self) -> Connection:
        return connect(
            host=self.host,
            port=self.port,
            user=self.username,
            catalog=self.catalog,
            schema=self.database,
            http_scheme=self.http_scheme,
            auth=self.auth,
            request_timeout=self.request_timeout
        )
    
    @contextmanager
    def cursor(self, **kwargs) -> Iterator[Cursor]:
        cursor: Cursor = self.conn.cursor(**kwargs)
        try:
            yield cursor
        finally:
            cursor.close()

    def close(self):
        conn: Optional[Connection] = self.__dict__.pop('conn', None)
        if conn is not None:
            conn.close()

    def __enter__(self) -> 'TrinoModel':
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()