from pydata_google_auth import get_user_credentials
from pydata_google_auth.cache import NOOP

from clients.google.main import GoogleCredentialsModel


DEFAULT_SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets',
]

# Apps Script API. The default OAuth client that create_credentials()
# falls back to when neither client_id nor client_secret is passed does
# not have this API enabled, so a token requesting these scopes without
# a custom client authenticates fine but then fails on the first call
# with SERVICE_DISABLED.
SCRIPT_SCOPES = [
    'https://www.googleapis.com/auth/script.projects',
    'https://www.googleapis.com/auth/script.deployments',
    'https://www.googleapis.com/auth/script.webapp.deploy',
]


def create_credentials(
    scopes: list[str] | None = None,
    client_id: str | None = None,
    client_secret: str | None = None,
) -> GoogleCredentialsModel:
    """
    Run an interactive Google OAuth2 flow on the local machine and return a
    `GoogleCredentialsModel` populated with the issued tokens.

    Intended as a **one-off local bootstrap helper**: run this once on a
    developer machine, capture the returned `GoogleCredentialsModel`, and
    persist it (e.g. JSON via `model.model_dump_json()` in a secret vault or
    a file) so runtime code can rehydrate the model without
    triggering the browser-based consent flow again. Backed by
    `pydata_google_auth.get_user_credentials` with `credentials_cache=NOOP`,
    so nothing is written to disk by this function — caching is the
    caller's responsibility.

    Leaving client_id/client_secret unset authorizes with
    pydata_google_auth's own built-in OAuth client. Google checks whether an
    API is enabled against the Cloud project that owns the OAuth *client*,
    not the project that owns the resource being called, so a token issued
    with that built-in client can fail on any API that project has not
    enabled — Drive and Sheets happen to be on, but this is not guaranteed
    for an API you add later, and nobody here can enable one on pydata's
    project. Pass your own project's OAuth client (Cloud console > APIs &
    Services > Credentials > an "installed"/Desktop client) whenever the
    call needs an API not already confirmed enabled there.

    Args:
        scopes (list[str] | None): OAuth2 scopes to request. Defaults to
            None, which falls back to `DEFAULT_SCOPES` (Drive + Sheets).
        client_id (str | None): OAuth2 client id to authorize with.
            Defaults to None, which falls back to pydata_google_auth's
            built-in client.
        client_secret (str | None): OAuth2 client secret matching
            `client_id`. Defaults to None, alongside `client_id`.

    Returns:
        GoogleCredentialsModel: Credential model carrying the freshly issued
        access token, refresh token, and OAuth2 client metadata. Cache and
        reuse this rather than calling the helper on every run.

    Example:
        >>> # one-time bootstrap on a local machine
        >>> creds = create_credentials()
        >>> Path('google_creds.json').write_text(creds.model_dump_json())
        >>>
        >>> # later, in runtime code
        >>> creds = GoogleCredentialsModel.model_validate_json(
        ...     Path('google_creds.json').read_text()
        ... )
        >>> api = GdriveModel(**creds.model_dump())

        >>> # with a project-owned OAuth client, for an API pydata's
        >>> # project does not have enabled
        >>> creds = create_credentials(
        ...     scopes=['https://www.googleapis.com/auth/script.projects'],
        ...     client_id='...apps.googleusercontent.com',
        ...     client_secret='...',
        ... )
    """
    if (client_id is not None or client_secret is not None) and (
        not client_id or not client_secret
    ):
        raise ValueError(
            'client_id and client_secret must be provided together '
            'and non-empty'
        )

    creds = get_user_credentials(
        scopes=scopes or DEFAULT_SCOPES,
        client_id=client_id,
        client_secret=client_secret,
        credentials_cache=NOOP,
        use_local_webserver=True,
    )

    return GoogleCredentialsModel(
        token=creds.token,
        refresh_token=creds.refresh_token,
        token_uri=creds.token_uri,
        client_id=creds.client_id,
        client_secret=creds.client_secret,
    )
