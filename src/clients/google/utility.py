from pydata_google_auth import get_user_credentials
from pydata_google_auth.cache import NOOP

from clients.google.main import GoogleCredentialsModel

from typing import (
    List,
    Optional
)


DEFAULT_SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]


def create_credentials(
    scopes: Optional[List[str]] = None,
    credentials_cache = NOOP,
    use_local_webserver: bool = True,
    **kwargs
) -> GoogleCredentialsModel:
    """Run the Google OAuth user consent flow and return the credentials.

    Opens a browser for sign-in and blocks until consent is granted. Caching is
    off by default, so every call re-runs the flow; persist the returned model
    (or pass a `credentials_cache`) to avoid signing in repeatedly.

    Args:
        scopes: Requested scopes. Defaults to full Drive and Sheets access.
        credentials_cache: `pydata_google_auth` cache backing the flow.
            Defaults to `NOOP` — nothing is read or written to disk.
        use_local_webserver: Whether to complete the flow through a local
            webserver redirect. Defaults to True; set False to fall back to the
            copy-paste console flow on a machine with no browser.
        **kwargs: Passed through to `pydata_google_auth.get_user_credentials`.

    Returns:
        GoogleCredentialsModel: The credentials, ready to construct a
            `GdriveModel` / `GspreadModel` from.

    Example:
        >>> creds = create_credentials()
        >>> model = GspreadModel(**creds.model_dump())
    """
    creds = get_user_credentials(
        scopes=scopes or DEFAULT_SCOPES,
        credentials_cache=credentials_cache,
        use_local_webserver=use_local_webserver,
        **kwargs
    )

    return GoogleCredentialsModel(
        token=creds.token,
        refresh_token=creds.refresh_token,
        token_uri=creds.token_uri,
        client_id=creds.client_id,
        client_secret=creds.client_secret,
    )