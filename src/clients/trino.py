from collections.abc import Generator
from contextlib import contextmanager
from functools import cached_property
from types import TracebackType

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

from typing import (
    Annotated,
    Any,
    Literal
)


class TrinoModel(BaseModel):
    """
    Typed wrapper for creating and reusing a Trino DB-API connection.

    Args:
        database (str): Default SQL schema name within the selected catalog
            (for example, `hive.default` -> `default`). Defaults to 'default'.
        http_scheme (Literal['http', 'https']): HTTP transport scheme for the
            Trino gateway connection. Defaults to 'https'.
        host (str): Trino coordinator or gateway host.
        port (int): Trino coordinator or gateway port.
        catalog (str): Default catalog name. Defaults to 'hive'.
        username (str): Login username.
        password (str): Login password.
        request_timeout (tuple[int, int]): Connect/read timeout tuple.
            Defaults to (60, 300).

    Attributes:
        auth (BasicAuthentication): Cached basic authentication object.
        conn (Connection): Cached DB-API connection.

    Note:
        - The connection is created lazily on first access to `conn` or
          `cursor()`, then reused for the same model instance.
        - `cursor()` is a context manager; use `with api.cursor() as cursor:`.
        - `cursor()` closes only the cursor.
        - `with TrinoModel(...) as api:` closes the connection on exit.
        - You can call `close()` explicitly to close the connection.

    Example:
        >>> with TrinoModel(
        ...     host='trino.example.com',
        ...     port=443,
        ...     username='user',
        ...     password='pw',
        ... ) as api:
        ...     with api.cursor() as cursor:
        ...         cursor.execute('SELECT 1')
        ...         print(cursor.fetchall())
    """

    model_config = ConfigDict(
        extra='forbid',
    )

    database: str = 'default'

    http_scheme: Literal['http', 'https'] = 'https'

    host: str

    port: int

    catalog: str = 'hive'

    username: str

    password: Annotated[
        str,
        Field(repr=False)
    ]

    request_timeout: tuple[
        Annotated[int, Field(gt=0)],
        Annotated[int, Field(gt=0)]
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
    def cursor(self, **kwargs: Any) -> Generator[Cursor, None, None]:
        cursor: Cursor = self.conn.cursor(**kwargs)
        try:
            yield cursor
        finally:
            cursor.close()

    def close(self) -> None:
        conn: Connection | None = self.__dict__.pop('conn', None)
        if conn is not None:
            conn.close()

    def __enter__(self) -> 'TrinoModel':
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None
    ) -> None:
        self.close()
