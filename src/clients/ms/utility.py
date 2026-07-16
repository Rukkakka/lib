import asyncio
import time

from collections import defaultdict

import httpx

from azure.core.credentials import AccessToken

from typing import (
    Optional,
    Any,
    Callable,
    List,
    Tuple,
    Dict
)


def create_refresh_token(
    tenant_id: str,
    client_id: str,
    scopes: Optional[List[str]] = None,
    verify: bool = True,
    proxy: Optional[str] = None,
    poll_interval: float = 5.0,
    timeout: float = 900.0
) -> str:
    """Run the OAuth device code flow and return a refresh token.

    Prints the sign-in message to stdout, then polls the token endpoint until
    the user completes sign-in. Blocks the calling thread for up to `timeout`
    seconds. `offline_access` is added to `scopes` when missing, since without
    it Azure AD issues no refresh token.

    Args:
        tenant_id: Directory (tenant) id.
        client_id: Application (client) id of a public client with the device
            code flow enabled.
        scopes: Requested scopes. Defaults to Microsoft Graph `.default` plus
            `offline_access`.
        verify: Whether to verify TLS certificates. Defaults to True.
        proxy: Proxy URL for both requests, e.g. `http://proxy:8080`. Defaults
            to no proxy.
        poll_interval: Fallback seconds between polls when the device code
            response omits its own interval. Defaults to 5.0.
        timeout: Seconds to wait for sign-in before giving up. Defaults to 900.0.

    Returns:
        str: The refresh token, to be passed to `MSDelegateRefreshTokenClientModel`.

    Raises:
        TimeoutError: The device code expired or `timeout` elapsed.
        RuntimeError: The token endpoint returned an unexpected error.

    Example:
        >>> token = create_refresh_token(tenant_id='...', client_id='...')
        >>> model = MSDelegateRefreshTokenClientModel(
        ...     tenant_id='...', client_id='...', refresh_token=token
        ... )
    """
    if scopes is None:
        scopes = ['https://graph.microsoft.com/.default', 'offline_access']
    elif 'offline_access' not in scopes:
        scopes = [*scopes, 'offline_access']

    device_response = httpx.post(
        f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/devicecode',
        data={
            'client_id': client_id,
            'scope': ' '.join(scopes),
        },
        verify=verify,
        proxy=proxy,
        timeout=30.0
    )
    device_response.raise_for_status()
    device = device_response.json()

    print(device['message'])

    interval = float(device.get('interval', poll_interval))
    deadline = time.time() + timeout

    while time.time() < deadline:
        time.sleep(interval)

        token_response = httpx.post(
            f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token',
            data={
                'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
                'client_id': client_id,
                'device_code': device['device_code']
            },
            verify=verify,
            proxy=proxy,
            timeout=30.0
        )
        body = token_response.json()

        if 'refresh_token' in body:
            return body['refresh_token']

        error = body.get('error')
        if error == 'authorization_pending':
            continue
        if error == 'slow_down':
            interval += 5.0
            continue
        if error == 'expired_token':
            raise TimeoutError('Device code expired before user completed sign-in.')
        raise RuntimeError(f'Device code flow failed: {body}')

    raise TimeoutError(f'Device code flow timed out after {timeout}s.')


class _RefreshTokenCredential:
    """Async token credential backed by a long-lived refresh token.

    ``get_token`` is a coroutine so that the kiota Azure auth provider awaits it
    instead of blocking the event loop; the provider awaits ``close`` after every
    fetch, which is safe here because each exchange uses its own ``AsyncClient``.

    Azure AD may issue a new refresh token on every exchange. ``on_refresh`` is
    invoked with each newly issued value so the owning model can persist it.
    """

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        refresh_token: str,
        verify: bool = True,
        proxy: Optional[str] = None,
        on_refresh: Optional[Callable[[str], None]] = None
    ) -> None:
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._refresh_token = refresh_token
        self._verify = verify
        self._proxy = proxy
        self._on_refresh = on_refresh
        self._cache: Dict[Tuple[str, ...], AccessToken] = {}
        self._locks: Dict[Tuple[str, ...], asyncio.Lock] = defaultdict(asyncio.Lock)

    @property
    def refresh_token(self) -> str:
        return self._refresh_token

    def _token_request_data(self, scopes: Tuple[str, ...]) -> Dict[str, str]:
        return {
            'grant_type': 'refresh_token',
            'client_id': self._client_id,
            'refresh_token': self._refresh_token,
            'scope': ' '.join(scopes),
        }

    def _build_access_token(self, body: Dict[str, Any]) -> AccessToken:
        if body.get('refresh_token'):
            self._refresh_token = body['refresh_token']
            if self._on_refresh is not None:
                self._on_refresh(self._refresh_token)
        return AccessToken(
            body['access_token'],
            int(time.time()) + int(body['expires_in'])
        )

    def _cached_token(self, scopes: Tuple[str, ...]) -> Optional[AccessToken]:
        token = self._cache.get(scopes)
        if token is not None and token.expires_on - time.time() > 300:
            return token
        return None

    async def _exchange(self, scopes: Tuple[str, ...]) -> AccessToken:
        async with httpx.AsyncClient(
            verify=self._verify,
            proxy=self._proxy,
            timeout=30.0
        ) as client:
            response = await client.post(
                f'https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token',
                data=self._token_request_data(scopes),
            )
        response.raise_for_status()
        return self._build_access_token(response.json())

    async def get_token(self, *scopes: str, **_: Any) -> AccessToken:
        cached = self._cached_token(scopes)
        if cached is not None:
            return cached
        async with self._locks[scopes]:
            cached = self._cached_token(scopes)
            if cached is not None:
                return cached
            token = await self._exchange(scopes)
            self._cache[scopes] = token
            return token

    async def close(self) -> None:
        return None
