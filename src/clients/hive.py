from contextlib import contextmanager

from functools import cached_property

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator
)

from pyhive.hive import (
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
    Dict,
    Type
)


class HiveModel(BaseModel):
    """Pydantic model wrapping a PyHive Hive connection.

    Lazily creates and caches a `Connection` on first access via `conn`,
    exposes a `cursor()` context manager for per-query cursors, and supports
    both `with` and explicit `close()` for cleanup. A password is required
    when `auth` is 'LDAP' or 'CUSTOM'.

    Args:
        database: Default database to connect to. Defaults to 'default'.
        host: Hive server hostname.
        port: Hive server port.
        username: Username used for authentication.
        password: Password used for authentication. Required for LDAP/CUSTOM.
        auth: Authentication mode, one of 'NONE', 'LDAP', 'CUSTOM', 'NOSASL'.
            Defaults to 'LDAP'.
        configuration: Optional Hive session configuration overrides.

    Attributes:
        conn: Cached `Connection`, created on first access.

    Example:
        >>> with HiveModel(
        ...     host='localhost',
        ...     port=10000,
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

    host: Annotated[
        str,
        Field()
    ]

    port: Annotated[
        int,
        Field()
    ]

    username: Annotated[
        str,
        Field()
    ]

    password: Annotated[
        Optional[str],
        Field(repr=False)
    ] = None

    auth: Annotated[
        Literal['NONE', 'LDAP', 'CUSTOM', 'NOSASL'],
        Field()
    ] = 'LDAP'

    configuration: Annotated[
        Optional[Dict],
        Field()
    ] = None

    @model_validator(mode='after')
    def check_password_for_auth(self) -> 'HiveModel':
        if self.auth in ('LDAP', 'CUSTOM') and not self.password:
            raise ValueError(
                f"'password' is required when auth= '{self.auth}'"
            )
        return self
    
    @cached_property
    def conn(self) -> Connection:
        return connect(
            host=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            database=self.database,
            auth=self.auth,
            configuration=self.configuration,
        )
    
    @contextmanager
    def cursor(self, **kwargs) -> Iterator[Cursor]:
        cursor: Cursor = self.conn.cursor(**kwargs)
        try:
            yield cursor
        finally:
            cursor.close()
    
    def close(self) -> None:
        conn: Optional[Connection] = self.__dict__.pop('conn', None)
        if conn is not None:
            conn.close()

    def __enter__(self) -> 'HiveModel':
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_val: Optional[BaseException],
        exc_tb: Optional[TracebackType],
    ) -> None:
        self.close()