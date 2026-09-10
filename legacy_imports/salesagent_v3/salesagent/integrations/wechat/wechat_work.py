"""Enterprise WeChat API client for message sending and receiving.

This module provides integration with WeChat Work (企业微信) API for:
- Sending messages to customers
- Receiving messages via webhook
- Access token management
- Message encryption/decryption
"""
from __future__ import annotations

import hashlib
import time
from typing import Any

import httpx
import structlog
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

from salesagent.core.settings import settings

log = structlog.get_logger()


class WeChatWorkClient:
    """Enterprise WeChat API client."""

    def __init__(
        self,
        corp_id: str | None = None,
        corp_secret: str | None = None,
        agent_id: int | None = None,
    ):
        self.corp_id = corp_id or settings.wechat_corp_id
        self.corp_secret = corp_secret or settings.wechat_corp_secret
        self.agent_id = agent_id or settings.wechat_agent_id
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    async def get_access_token(self) -> str:
        """Get access token (cached for 2 hours).

        Returns:
            Access token string

        Raises:
            httpx.HTTPError: If API request fails
        """
        # Return cached token if still valid
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        # Fetch new token
        url = "https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        params = {
            "corpid": self.corp_id,
            "corpsecret": self.corp_secret,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            if data.get("errcode") != 0:
                log.error(
                    "Failed to get WeChat access token",
                    errcode=data.get("errcode"),
                    errmsg=data.get("errmsg"),
                )
                raise ValueError(f"WeChat API error: {data.get('errmsg')}")

            self._access_token = data["access_token"]
            # Token expires in 7200 seconds, refresh 5 minutes early
            self._token_expires_at = time.time() + data.get("expires_in", 7200) - 300

            log.info("WeChat access token refreshed", expires_in=data.get("expires_in"))
            return self._access_token

    async def send_text_message(
        self,
        user_id: str,
        content: str,
        safe: int = 0,
    ) -> dict[str, Any]:
        """Send text message to user.

        Args:
            user_id: WeChat user ID (e.g., "zhangsan")
            content: Message content
            safe: 0=normal, 1=encrypted (default: 0)

        Returns:
            API response dict

        Raises:
            httpx.HTTPError: If API request fails
        """
        token = await self.get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"

        payload = {
            "touser": user_id,
            "msgtype": "text",
            "agentid": self.agent_id,
            "text": {"content": content},
            "safe": safe,
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            if data.get("errcode") != 0:
                log.error(
                    "Failed to send WeChat message",
                    user_id=user_id,
                    errcode=data.get("errcode"),
                    errmsg=data.get("errmsg"),
                )
                raise ValueError(f"WeChat API error: {data.get('errmsg')}")

            log.info("WeChat message sent", user_id=user_id, msgid=data.get("msgid"))
            return data

    async def send_markdown_message(
        self,
        user_id: str,
        content: str,
    ) -> dict[str, Any]:
        """Send markdown message to user.

        Args:
            user_id: WeChat user ID
            content: Markdown content

        Returns:
            API response dict
        """
        token = await self.get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token={token}"

        payload = {
            "touser": user_id,
            "msgtype": "markdown",
            "agentid": self.agent_id,
            "markdown": {"content": content},
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            if data.get("errcode") != 0:
                log.error(
                    "Failed to send WeChat markdown",
                    user_id=user_id,
                    errcode=data.get("errcode"),
                    errmsg=data.get("errmsg"),
                )
                raise ValueError(f"WeChat API error: {data.get('errmsg')}")

            log.info("WeChat markdown sent", user_id=user_id, msgid=data.get("msgid"))
            return data

    async def get_user_info(self, user_id: str) -> dict[str, Any]:
        """Get user information.

        Args:
            user_id: WeChat user ID

        Returns:
            User info dict with name, mobile, email, etc.
        """
        token = await self.get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/user/get?access_token={token}&userid={user_id}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

            if data.get("errcode") != 0:
                log.error(
                    "Failed to get WeChat user info",
                    user_id=user_id,
                    errcode=data.get("errcode"),
                    errmsg=data.get("errmsg"),
                )
                raise ValueError(f"WeChat API error: {data.get('errmsg')}")

            return data

    def verify_signature(
        self,
        signature: str,
        timestamp: str,
        nonce: str,
    ) -> bool:
        """Verify webhook signature.

        Args:
            signature: Signature from WeChat
            timestamp: Timestamp from WeChat
            nonce: Nonce from WeChat

        Returns:
            True if signature is valid
        """
        token = settings.wechat_webhook_token
        tmp_list = [token, timestamp, nonce]
        tmp_list.sort()
        tmp_str = "".join(tmp_list)
        tmp_hash = hashlib.sha1(tmp_str.encode()).hexdigest()
        return tmp_hash == signature

    def decrypt_message(self, encrypted_msg: str) -> str:
        """Decrypt encrypted message from WeChat.

        Args:
            encrypted_msg: Base64 encoded encrypted message

        Returns:
            Decrypted message content
        """
        import base64

        key = base64.b64decode(settings.wechat_encoding_aes_key + "=")
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(key[:16]),
            backend=default_backend(),
        )
        decryptor = cipher.decryptor()

        encrypted_bytes = base64.b64decode(encrypted_msg)
        decrypted = decryptor.update(encrypted_bytes) + decryptor.finalize()

        # Remove padding
        pad = decrypted[-1]
        decrypted = decrypted[:-pad]

        # Extract message (skip first 16 bytes random, next 4 bytes msg length)
        msg_len = int.from_bytes(decrypted[16:20], byteorder="big")
        msg = decrypted[20 : 20 + msg_len].decode("utf-8")

        return msg


# Global client instance
_wechat_client: WeChatWorkClient | None = None


def get_wechat_client() -> WeChatWorkClient:
    """Get global WeChat client instance."""
    global _wechat_client
    if _wechat_client is None:
        _wechat_client = WeChatWorkClient()
    return _wechat_client
