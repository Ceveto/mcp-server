"""HTTP clients for Ceveto API — Ed25519 signing and OAuth Bearer."""

from __future__ import annotations

import json
import time
from urllib.parse import urlencode

import httpx
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


class CevetoAPIClient:
    """Async HTTP client that signs requests with Ed25519."""

    def __init__(self, base_url: str, username: str, private_key_hex: str) -> None:
        self.base_url = base_url.rstrip('/')
        self.username = username
        self._private_key = Ed25519PrivateKey.from_private_bytes(
            bytes.fromhex(private_key_hex)
        )
        self._default_account: str | None = None

    def set_default_account(self, account: str | None) -> None:
        self._default_account = account

    def _sign_request(
        self,
        method: str,
        path: str,
        body: str = '',
        account: str | None = None,
    ) -> dict[str, str]:
        timestamp = str(int(time.time()))
        message = f'{timestamp}{method}{path}{body}'.encode()
        signature = self._private_key.sign(message).hex()
        headers: dict[str, str] = {
            'X-API-Key': self.username,
            'X-API-Timestamp': timestamp,
            'X-API-Signature': signature,
        }
        acct = account or self._default_account
        if acct:
            headers['X-Account'] = acct
        return headers

    async def get(
        self,
        path: str,
        params: dict | None = None,
        account: str | None = None,
    ) -> dict:
        full_path = path
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                full_path = f'{path}?{urlencode(clean)}'
        headers = self._sign_request('GET', full_path, account=account)
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(f'{self.base_url}{full_path}', headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def post(self, path: str, data: dict, account: str | None = None) -> dict:
        body = json.dumps(data)
        headers = self._sign_request('POST', path, body, account=account)
        headers['Content-Type'] = 'application/json'
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.post(
                f'{self.base_url}{path}', content=body, headers=headers
            )
            resp.raise_for_status()
            return resp.json()

    async def put(self, path: str, data: dict, account: str | None = None) -> dict:
        body = json.dumps(data)
        headers = self._sign_request('PUT', path, body, account=account)
        headers['Content-Type'] = 'application/json'
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.put(
                f'{self.base_url}{path}', content=body, headers=headers
            )
            resp.raise_for_status()
            return resp.json()

    async def patch(self, path: str, data: dict, account: str | None = None) -> dict:
        body = json.dumps(data)
        headers = self._sign_request('PATCH', path, body, account=account)
        headers['Content-Type'] = 'application/json'
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.patch(
                f'{self.base_url}{path}', content=body, headers=headers
            )
            resp.raise_for_status()
            return resp.json()

    async def delete(self, path: str, account: str | None = None) -> dict:
        headers = self._sign_request('DELETE', path, account=account)
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.delete(f'{self.base_url}{path}', headers=headers)
            resp.raise_for_status()
            return resp.json()


class CevetoOAuthClient:
    """Async HTTP client using OAuth Bearer tokens."""

    def __init__(self, base_url: str, access_token: str) -> None:
        self.base_url = base_url.rstrip('/')
        self.access_token = access_token
        self._default_account: str | None = None

    def set_default_account(self, account: str | None) -> None:
        self._default_account = account

    def _headers(self, account: str | None = None) -> dict[str, str]:
        headers: dict[str, str] = {
            'Authorization': f'Bearer {self.access_token}',
        }
        acct = account or self._default_account
        if acct:
            headers['X-Account'] = acct
        return headers

    async def get(
        self, path: str, params: dict | None = None, account: str | None = None
    ) -> dict:
        full_path = path
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            if clean:
                full_path = f'{path}?{urlencode(clean)}'
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.get(
                f'{self.base_url}{full_path}', headers=self._headers(account)
            )
            resp.raise_for_status()
            return resp.json()

    async def post(self, path: str, data: dict, account: str | None = None) -> dict:
        body = json.dumps(data)
        headers = self._headers(account)
        headers['Content-Type'] = 'application/json'
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.post(
                f'{self.base_url}{path}', content=body, headers=headers
            )
            resp.raise_for_status()
            return resp.json()

    async def put(self, path: str, data: dict, account: str | None = None) -> dict:
        body = json.dumps(data)
        headers = self._headers(account)
        headers['Content-Type'] = 'application/json'
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.put(
                f'{self.base_url}{path}', content=body, headers=headers
            )
            resp.raise_for_status()
            return resp.json()

    async def patch(self, path: str, data: dict, account: str | None = None) -> dict:
        body = json.dumps(data)
        headers = self._headers(account)
        headers['Content-Type'] = 'application/json'
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.patch(
                f'{self.base_url}{path}', content=body, headers=headers
            )
            resp.raise_for_status()
            return resp.json()

    async def delete(self, path: str, account: str | None = None) -> dict:
        async with httpx.AsyncClient(verify=False) as client:
            resp = await client.delete(
                f'{self.base_url}{path}', headers=self._headers(account)
            )
            resp.raise_for_status()
            return resp.json()
