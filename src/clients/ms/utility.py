from collections.abc import (
    Callable,
    Sequence,
)
import asyncio
import threading
import time

import httpx
from azure.core.credentials import AccessToken

from clients.utility import raise_for_status

from typing import Any


def create_refresh_token(
    tenant_id: str,
    client_id: str,
    scopes: Sequence[str] = ('https://graph.microsoft.com/.default', 'offline_access'),
    verify: bool = True,
    proxy: str | None = None,
    poll_interval: float = 5.0,
    timeout: float = 900.0,
) -> str:
    """
    Run the OAuth2 device code flow interactively and return the
    refresh token.

    Intended as a **one-off local bootstrap helper**: run this once on a
    developer machine, capture the returned refresh token, and persist it
    somewhere durable (secret vault, env file, etc.).
    Runtime code then feeds the stored token into
    ``MSDelegatedRefreshTokenClientModel`` for non-interactive use, so the
    user does not have to repeat the device code flow on every run. This
    function does not cache anything itself — caching is the caller's
    responsibility.

    Prompts the user to open a verification URL and enter a one-time
    device code, then polls the token endpoint until the user completes
    the sign-in (or timeout).

    The Azure AD app registration must have ``Allow public client flows``
    enabled; otherwise ``AADSTS7000218`` is raised.

    Args:
        tenant_id (str): Azure AD tenant id.
        client_id (str): Azure AD application (client) id.
        scopes (Sequence[str]): OAuth scopes to request. Must
            include ``offline_access`` to receive a refresh token; the
            helper adds it automatically when missing. Defaults to
            ('https://graph.microsoft.com/.default', 'offline_access').
        verify (bool): TLS certificate verification flag. Defaults to True.
        proxy (str | None): Proxy URL for both the device code and the
            token requests. Defaults to None.
        poll_interval (float): Seconds between token endpoint polls.
            Server may override via ``interval`` in the device code
            response. Defaults to 5.0.
        timeout (float): Maximum seconds to wait for user completion.
            Defaults to 900.0 (15 minutes).

    Returns:
        str: The OAuth2 refresh token to persist for runtime use. Store it
        rather than calling this helper on every run.

    See:
        https://learn.microsoft.com/azure/active-directory/develop/v2-oauth2-device-code

    Example:
        >>> # one-time bootstrap on a local machine
        >>> refresh_token = create_refresh_token(
        ...     tenant_id='<tenant>',
        ...     client_id='<client>',
        ...     verify=False,
        ... )
        >>> # persist refresh_token to your secret backend, then in runtime:
        >>> client = MSDelegatedRefreshTokenClientModel(
        ...     tenant_id='<tenant>',
        ...     client_id='<client>',
        ...     refresh_token=refresh_token,
        ... )
    """
    if 'offline_access' not in scopes:
        scopes = (*scopes, 'offline_access')

    device_response = httpx.post(
        f'https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/devicecode',
        data={
            'client_id': client_id,
            'scope': ' '.join(scopes),
        },
        verify=verify,
        proxy=proxy,
        timeout=30.0,
    )
    raise_for_status(response=device_response)
    device = device_response.json()

    # Intentional stdout for local interactive device-code bootstrap.
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
                'device_code': device['device_code'],
            },
            verify=verify,
            proxy=proxy,
            timeout=30.0,
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
    """
    azure-core ``TokenCredential`` that exchanges an OAuth2 refresh
    token for an access token via the ``refresh_token`` grant.

    Microsoft rotates the refresh token on every grant; the new value
    replaces the in-memory copy and is exposed via ``refresh_token``.
    ``on_refresh`` is invoked with each newly issued value so the owning
    model can mirror it and persist it externally.

    Args:
        tenant_id (str): Azure AD tenant id.
        client_id (str): Azure AD application (client) id.
        refresh_token (str): OAuth2 refresh token previously obtained
            via an interactive flow (e.g. device code).
        verify (bool): TLS certificate verification flag. Defaults to True.
        proxy (str | None): Proxy URL for the token requests.
            Defaults to None.
        on_refresh (Callable[[str], None] | None): Called with the rotated
            refresh token after every grant that issues a new one.
            Defaults to None.
    """

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        refresh_token: str,
        verify: bool = True,
        proxy: str | None = None,
        on_refresh: Callable[[str], None] | None = None,
    ) -> None:
        self._tenant_id = tenant_id
        self._client_id = client_id
        self._refresh_token = refresh_token
        self._verify = verify
        self._proxy = proxy
        self._on_refresh = on_refresh
        self._cached: AccessToken | None = None
        self._lock = threading.Lock()
        self._async_lock = asyncio.Lock()

    @property
    def refresh_token(self) -> str:
        return self._refresh_token

    def _token_request_data(self, scopes: tuple) -> dict:
        return {
            'grant_type': 'refresh_token',
            'client_id': self._client_id,
            'refresh_token': self._refresh_token,
            'scope': ' '.join(scopes),
        }

    def _build_access_token(self, body: dict) -> AccessToken:
        if body.get('refresh_token'):
            self._refresh_token = body['refresh_token']
            if self._on_refresh is not None:
                self._on_refresh(self._refresh_token)
        return AccessToken(
            body['access_token'],
            int(time.time() + body.get('expires_in', 0)),
        )

    def _exchange(self, scopes: tuple) -> AccessToken:
        response = httpx.post(
            f'https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token',
            data=self._token_request_data(scopes),
            verify=self._verify,
            proxy=self._proxy,
            timeout=30.0,
        )
        raise_for_status(response=response)
        return self._build_access_token(response.json())

    async def _exchange_async(self, scopes: tuple) -> AccessToken:
        async with httpx.AsyncClient(
            verify=self._verify,
            proxy=self._proxy,
            timeout=30.0,
        ) as client:
            response = await client.post(
                f'https://login.microsoftonline.com/{self._tenant_id}/oauth2/v2.0/token',
                data=self._token_request_data(scopes),
            )
        raise_for_status(response=response)
        return self._build_access_token(response.json())

    def get_token(self, *scopes: str, **_: Any) -> AccessToken:
        if self._cached and self._cached.expires_on - time.time() > 300:
            return self._cached
        with self._lock:
            if self._cached and self._cached.expires_on - time.time() > 300:
                return self._cached
            self._cached = self._exchange(scopes)
            return self._cached

    async def get_token_async(self, *scopes: str, **_: Any) -> AccessToken:
        if self._cached and self._cached.expires_on - time.time() > 300:
            return self._cached
        async with self._async_lock:
            if self._cached and self._cached.expires_on - time.time() > 300:
                return self._cached
            self._cached = await self._exchange_async(scopes)
            return self._cached

    def close(self) -> None:
        return None
